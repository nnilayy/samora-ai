import os
import re
from loguru import logger
from dotenv import load_dotenv
from deepgram import LiveOptions
from utils import save_chat_history
from pipecat.pipeline.pipeline import Pipeline
from prompts import SYSTEM_PROMPT, WAKE_PROMPTS
from pipecat.runner.utils import create_transport
from pipecat.pipeline.runner import PipelineRunner
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.services.groq.llm import GroqLLMService
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.services.google.llm import GoogleLLMService
from pipecat.services.openai.llm import OpenAILLMService
# from pipecat.transports.daily.transport import DailyParams
from pipecat.services.llm_service import FunctionCallParams
from pipecat.services.cerebras.llm import CerebrasLLMService
from pipecat.services.cartesia.tts import CartesiaTTSService
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.deepgram.tts import DeepgramTTSService
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.user_idle_processor import UserIdleProcessor
from pipecat.transports.websocket.fastapi import FastAPIWebsocketParams
from pipecat.services.elevenlabs.stt import ElevenLabsRealtimeSTTService
from pipecat.audio.turn.smart_turn.base_smart_turn import SmartTurnParams
from pipecat.transports.base_transport import BaseTransport, TransportParams
from pipecat.processors.frame_processor import FrameProcessor, FrameDirection
from rolling_summarizer_context_manager import RollingSummarizerContextManager
from pipecat.audio.turn.smart_turn.local_smart_turn_v3 import LocalSmartTurnAnalyzerV3
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
)
from pipecat.frames.frames import (
    Frame,
    EndFrame,
    LLMRunFrame,
    TTSSpeakFrame,
    TranscriptionFrame,
    LLMMessagesAppendFrame,
    FunctionCallResultProperties,
)
from prompts.function_schemas import (
    hold_function,
    end_call_function,
)
from db_functions import (
    book_room,
    get_pricing,
    get_amenities,
    lookup_booking,
    cancel_booking,
    update_booking,
    check_availability,
    add_special_request,
)


load_dotenv(override=True)


class HoldWakeProcessor(FrameProcessor):
    """Filters transcriptions when on hold, passes wake prompts to resume."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.is_on_hold = False
        self._wake_patterns = [
            re.compile(r"\b" + re.escape(phrase) + r"\b", re.IGNORECASE)
            for phrase in WAKE_PROMPTS
        ]

    def set_hold(self, on_hold: bool):
        """Set the hold state."""
        self.is_on_hold = on_hold
        if on_hold:
            logger.info("Hold mode ACTIVATED - waiting for wake phrase")
        else:
            logger.info("Hold mode DEACTIVATED - resuming conversation")

    def _contains_wake_phrase(self, text: str) -> bool:
        """Check if text contains any wake phrase."""
        for pattern in self._wake_patterns:
            if pattern.search(text):
                return True
        return False

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        """Process frames, filtering transcriptions when on hold."""
        await super().process_frame(frame, direction)

        # If not on hold, pass everything through
        if not self.is_on_hold:
            await self.push_frame(frame, direction)
            return

        # When on hold, check transcriptions for wake phrases
        if isinstance(frame, TranscriptionFrame):
            text = frame.text
            logger.debug(f"On hold - received transcription: '{text}'")

            if self._contains_wake_phrase(text):
                logger.info(f"Wake phrase detected: '{text}'")
                self.is_on_hold = False
                # Pass the frame through so LLM can respond
                await self.push_frame(frame, direction)
            else:
                # Silently drop the transcription
                logger.debug(f"Dropping transcription (on hold): '{text}'")
        else:
            # Pass through non-transcription frames
            await self.push_frame(frame, direction)


transport_params = {
    # "daily": lambda: DailyParams(
    #     audio_in_enabled=True,
    #     audio_out_enabled=True,
    #     vad_analyzer=SileroVADAnalyzer(params=VADParams(stop_secs=0.3)),
    #     turn_analyzer=LocalSmartTurnAnalyzerV3(params=SmartTurnParams()),
    # ),
    "webrtc": lambda: TransportParams(
        audio_in_enabled=True,
        audio_out_enabled=True,
        vad_analyzer=SileroVADAnalyzer(
            params=VADParams(stop_secs=0.8)
        ),  # Increased from 0.3 to reduce split transcriptions
        turn_analyzer=LocalSmartTurnAnalyzerV3(params=SmartTurnParams()),
    ),
    "twilio": lambda: FastAPIWebsocketParams(
        audio_in_enabled=True,
        audio_out_enabled=True,
        add_wav_header=False,
        vad_analyzer=SileroVADAnalyzer(params=VADParams(stop_secs=0.3)),
        turn_analyzer=LocalSmartTurnAnalyzerV3(params=SmartTurnParams()),
    ),
}


async def run_bot(transport: BaseTransport, runner_args, config: dict):
    logger.info("Starting Samora AI bot...")

    # ============ PROVIDER CONFIG ============
    llm_provider = config.get("llm_provider", "openai")
    stt_provider = config.get("stt_provider", "deepgram")
    tts_provider = config.get("tts_provider", "cartesia")

    logger.info(
        f"Using providers - LLM: {llm_provider}, STT: {stt_provider}, TTS: {tts_provider}"
    )

    # ============ STT ============
    if stt_provider == "deepgram":
        deepgram_key = config.get("deepgram_api_key") or os.getenv(
            "DEEPGRAM_API_KEY", ""
        )
        stt = DeepgramSTTService(
            api_key=deepgram_key,
            live_options=LiveOptions(
                model="nova-3",
                language="multi",
                interim_results=False,
                vad_events=False,
                diarize=False,
                filler_words=True,
            ),
        )
        logger.info("STT: Deepgram Nova-3")
    else:  # elevenlabs (default)
        elevenlabs_key = config.get("elevenlabs_api_key") or os.getenv(
            "ELEVENLABS_API_KEY", ""
        )
        stt = ElevenLabsRealtimeSTTService(
            api_key=elevenlabs_key,
            model="scribe_v2_realtime",
        )
        logger.info("STT: ElevenLabs Scribe v2")

    # ============ LLM ============
    if llm_provider == "openai":
        openai_key = config.get("openai_api_key") or os.getenv("OPENAI_API_KEY", "")
        llm = OpenAILLMService(
            api_key=openai_key,
            model="gpt-4o-mini",
        )
        logger.info("LLM: OpenAI GPT-4o-mini")
    elif llm_provider == "cerebras":
        cerebras_key = config.get("cerebras_api_key") or os.getenv(
            "CEREBRAS_API_KEY", ""
        )
        llm = CerebrasLLMService(
            api_key=cerebras_key,
            model="llama-3.3-70b",
        )
        logger.info("LLM: Cerebras Llama-3.3-70B")
    elif llm_provider == "groq":
        groq_key = config.get("groq_api_key") or os.getenv("GROQ_API_KEY", "")
        llm = GroqLLMService(
            api_key=groq_key,
            model="llama-3.3-70b-versatile",
        )
        logger.info("LLM: Groq Llama-3.3-70B")
    else:  # google (default)
        google_key = config.get("google_api_key") or os.getenv("GOOGLE_API_KEY", "")
        llm = GoogleLLMService(
            api_key=google_key,
            model="gemini-2.5-flash",
        )
        logger.info("LLM: Google Gemini 2.5 Flash")

    # ============ TTS ============
    if tts_provider == "deepgram":
        deepgram_key = config.get("deepgram_api_key") or os.getenv(
            "DEEPGRAM_API_KEY", ""
        )
        tts = DeepgramTTSService(
            api_key=deepgram_key,
            voice="aura-2-theia-en",  # Australian, feminine, expressive, polite, sincere
        )
        logger.info("TTS: Deepgram Aura-2 Theia")
    else:  # cartesia (default)
        cartesia_key = config.get("cartesia_api_key") or os.getenv(
            "CARTESIA_API_KEY", ""
        )
        tts = CartesiaTTSService(
            api_key=cartesia_key,
            voice_id="248be419-c632-4f23-adf1-5324ed7dbf1d",
        )
        logger.info("TTS: Cartesia")

    # Track LLM response state to prevent idle interrupts during generation
    # Note: This uses event handlers which may not fire for all LLM providers
    _llm_responding_tracker = {"is_responding": False}

    @llm.event_handler("on_llm_started")
    async def on_llm_started(llm_service):
        _llm_responding_tracker["is_responding"] = True

    @llm.event_handler("on_llm_stopped")
    async def on_llm_stopped(llm_service):
        _llm_responding_tracker["is_responding"] = False

    # ============ PROCESSORS ============
    hold_wake_processor = HoldWakeProcessor()

    async def handle_user_idle(processor: UserIdleProcessor, retry_count: int) -> bool:
        """Handle user idle - prompts user up to 3 times then ends call."""
        if _llm_responding_tracker["is_responding"]:
            return True

        if hold_wake_processor.is_on_hold:
            return True

        if retry_count == 1:
            logger.info(f"User idle (attempt {retry_count}/3)")
            message = {
                "role": "system",
                "content": "The user has been quiet for a moment. Gently and briefly ask if they're still there. Keep it natural and warm, like 'Hey, just checking - are you still with me?'",
            }
            await processor.push_frame(LLMMessagesAppendFrame([message], run_llm=True))
            return True
        elif retry_count == 2:
            logger.info(f"User idle (attempt {retry_count}/3)")
            message = {
                "role": "system",
                "content": "The user is still quiet. Politely ask if they'd like to continue or if they need more time. Be warm but brief.",
            }
            await processor.push_frame(LLMMessagesAppendFrame([message], run_llm=True))
            return True
        else:
            logger.info(f"User idle (attempt {retry_count}/3) - ending call")
            await processor.push_frame(
                TTSSpeakFrame(
                    "It looks like you might be busy right now. Feel free to call back anytime - we're always here to help. Take care!"
                )
            )
            await task.queue_frame(EndFrame())
            return False

    user_idle_processor = UserIdleProcessor(
        callback=handle_user_idle,
        timeout=10.0,
    )

    async def put_on_hold(params: FunctionCallParams):
        logger.info("Putting conversation on HOLD")
        hold_wake_processor.set_hold(True)
        await params.llm.push_frame(
            TTSSpeakFrame(
                "No problem! I'll wait right here. Just say I'm back when you're ready to continue."
            )
        )
        properties = FunctionCallResultProperties(run_llm=False)
        await params.result_callback({"status": "on_hold"}, properties=properties)

    async def end_call(params: FunctionCallParams):
        logger.info("Ending call gracefully")
        await task.queue_frames(
            [
                TTSSpeakFrame(
                    "It was great talking with you! Feel free to reach out anytime. Take care!"
                ),
                EndFrame(),
            ]
        )
        properties = FunctionCallResultProperties(run_llm=False)
        await params.result_callback({"status": "call_ended"}, properties=properties)

    llm.register_function("put_on_hold", put_on_hold)
    llm.register_function("end_call", end_call)

    # ============ REGISTER DB FUNCTIONS (Direct Functions) ============
    llm.register_direct_function(get_pricing)
    llm.register_direct_function(get_amenities)
    llm.register_direct_function(lookup_booking)
    llm.register_direct_function(add_special_request)
    llm.register_direct_function(cancel_booking)
    llm.register_direct_function(check_availability)
    llm.register_direct_function(book_room)
    llm.register_direct_function(update_booking)

    # ============ CONTEXT & PIPELINE ============
    tools = ToolsSchema(
        standard_tools=[
            hold_function,
            end_call_function,
            get_pricing,
            get_amenities,
            lookup_booking,
            add_special_request,
            cancel_booking,
            check_availability,
            book_room,
            update_booking,
        ]
    )

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    context = LLMContext(messages, tools=tools)
    context_aggregator = LLMContextAggregatorPair(context)

    context_threshold = config.get("context_threshold", 100)
    context_keep_recent = config.get("context_keep_recent", 20)

    context_manager = RollingSummarizerContextManager(
        context=context,
        llm_service=llm,
        threshold=context_threshold,
        keep_recent=context_keep_recent,
    )

    # user_idle_processor placed after LLM to auto-pause during function calls
    pipeline = Pipeline(
        [
            transport.input(),
            stt,
            hold_wake_processor,
            context_aggregator.user(),
            llm,
            context_manager,
            user_idle_processor,
            tts,
            transport.output(),
            context_aggregator.assistant(),
        ]
    )

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            allow_interruptions=True,
            enable_metrics=True,
            enable_usage_metrics=True,
        ),
        idle_timeout_secs=runner_args.pipeline_idle_timeout_secs,
    )

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        logger.info("Client connected")
        await task.queue_frames([LLMRunFrame()])

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info("Client disconnected")
        await task.cancel()

    runner = PipelineRunner(
        handle_sigint=runner_args.handle_sigint
        if hasattr(runner_args, "handle_sigint")
        else False
    )
    await runner.run(task)

    # Save chat history after pipeline finishes
    save_chat_history(context.messages)


async def bot(runner_args):
    """Main bot entry point for Pipecat Cloud."""
    # Extract config from runner_args.body (sent from frontend)
    body = getattr(runner_args, "body", None) or {}

    config = {
        # Provider selections (defaults if not specified)
        "llm_provider": body.get("llm_provider", "openai"),
        "stt_provider": body.get("stt_provider", "deepgram"),
        "tts_provider": body.get("tts_provider", "cartesia"),
        # API keys (optional overrides)
        "openai_api_key": body.get("openai_api_key"),
        "google_api_key": body.get("google_api_key"),
        "cerebras_api_key": body.get("cerebras_api_key"),
        "groq_api_key": body.get("groq_api_key"),
        "elevenlabs_api_key": body.get("elevenlabs_api_key"),
        "deepgram_api_key": body.get("deepgram_api_key"),
        "cartesia_api_key": body.get("cartesia_api_key"),
        # Context management settings
        "context_threshold": body.get("context_threshold", 100),
        "context_keep_recent": body.get("context_keep_recent", 20),
    }

    logger.info(
        f"Bot config received: LLM={config['llm_provider']}, STT={config['stt_provider']}, TTS={config['tts_provider']}"
    )

    transport = await create_transport(runner_args, transport_params)
    await run_bot(transport, runner_args, config)


if __name__ == "__main__":
    from pipecat.runner.run import main

    main()
