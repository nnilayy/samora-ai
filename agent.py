#
# Samora AI Demo - Voice Pipeline with Hold/Wake Feature
#

import os
import re
import random
from dotenv import load_dotenv
from loguru import logger

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.processors.user_idle_processor import UserIdleProcessor
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.audio.turn.smart_turn.base_smart_turn import SmartTurnParams
from pipecat.audio.turn.smart_turn.local_smart_turn_v3 import LocalSmartTurnAnalyzerV3
from pipecat.frames.frames import LLMRunFrame, TTSSpeakFrame, TranscriptionFrame, Frame, FunctionCallResultProperties
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import LLMContextAggregatorPair
from pipecat.processors.frame_processor import FrameProcessor, FrameDirection
from pipecat.runner.types import RunnerArguments
from pipecat.runner.utils import create_transport
from pipecat.services.cartesia.tts import CartesiaTTSService
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.elevenlabs.stt import ElevenLabsRealtimeSTTService
from pipecat.services.llm_service import FunctionCallParams
from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.services.cerebras.llm import CerebrasLLMService
from pipecat.transports.base_transport import BaseTransport, TransportParams
from pipecat.transports.websocket.fastapi import FastAPIWebsocketParams
# from pipecat.services.openai.llm import OpenAILLMService
# from pipecat.services.groq.llm import GroqLLMService
# from pipecat.transports.daily.transport import DailyParams

from prompts import (
    SYSTEM_PROMPT,
    USER_IDLE_PROMPTS,
    WAKE_PROMPTS,
    HOLD_FUNCTION_DESCRIPTION,
    END_CALL_FUNCTION_DESCRIPTION,
)


class HoldWakeProcessor(FrameProcessor):
    """Filters transcriptions when on hold, passes wake prompts to resume."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.is_on_hold = False
        self._wake_patterns = [
            re.compile(r'\b' + re.escape(phrase) + r'\b', re.IGNORECASE)
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

load_dotenv(override=True)

# Transport configuration for different connection types
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
        vad_analyzer=SileroVADAnalyzer(params=VADParams(stop_secs=0.3)),
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


async def run_bot(transport: BaseTransport, runner_args: RunnerArguments):
    logger.info("Starting Samora AI bot...")

    stt = ElevenLabsRealtimeSTTService(
        api_key=os.getenv("ELEVENLABS_API_KEY", ""),
        model="scribe_v2_realtime",
    )
    
    # stt = DeepgramSTTService(
    #     api_key=os.getenv("DEEPGRAM_API_KEY", ""),
    # )

    tts = CartesiaTTSService(
        api_key=os.getenv("CARTESIA_API_KEY", ""),
        voice_id="11af83e2-23eb-452f-956e-7fee218ccb5c",
    )

    hold_wake_processor = HoldWakeProcessor()

    async def handle_user_idle(processor, retry_count):
        if hold_wake_processor.is_on_hold:
            logger.debug("User idle but on hold - skipping idle prompt")
            return True
        
        prompt = random.choice(USER_IDLE_PROMPTS)
        logger.info(f"User idle (retry {retry_count}) - prompting: '{prompt}'")
        await processor.push_frame(TTSSpeakFrame(prompt))
        
        if retry_count >= 3:
            logger.info("Max idle retries reached - stopping idle prompts")
            return False
        return True

    user_idle_processor = UserIdleProcessor(
        callback=handle_user_idle,
        timeout=10.0,
    )

    # llm = OpenAILLMService(
    #     api_key=os.getenv("OPENAI_API_KEY", ""),
    #     model="gpt-4o-mini",
    # )

    llm = CerebrasLLMService(
        api_key=os.getenv("CEREBRAS_API_KEY", ""),
        model="gpt-oss-120b",
    )

    # llm = GroqLLMService(
    #     api_key=os.getenv("GROQ_API_KEY", ""),
    #     model="openai/gpt-oss-120b",
    # )

    async def put_on_hold(params: FunctionCallParams):
        logger.info("Putting conversation on HOLD")
        hold_wake_processor.set_hold(True)
        await params.llm.push_frame(
            TTSSpeakFrame("No problem! I'll wait right here. Just say I'm back when you're ready to continue.")
        )
        properties = FunctionCallResultProperties(run_llm=False)
        await params.result_callback({"status": "on_hold"}, properties=properties)
    
    async def end_call(params: FunctionCallParams):
        logger.info("Ending call gracefully")
        await params.llm.push_frame(
            TTSSpeakFrame("It was great talking with you! Feel free to reach out anytime. Take care!")
        )
        properties = FunctionCallResultProperties(run_llm=False)
        await params.result_callback({"status": "call_ended"}, properties=properties)
        await task.stop_when_done()
    
    hold_function = FunctionSchema(
        name="put_on_hold",
        description=HOLD_FUNCTION_DESCRIPTION,
        properties={},
        required=[]
    )
    
    end_call_function = FunctionSchema(
        name="end_call",
        description=END_CALL_FUNCTION_DESCRIPTION,
        properties={},
        required=[]
    )
    
    tools = ToolsSchema(standard_tools=[hold_function, end_call_function])
    llm.register_function("put_on_hold", put_on_hold)
    llm.register_function("end_call", end_call)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    context = LLMContext(messages, tools=tools)
    context_aggregator = LLMContextAggregatorPair(context)

    pipeline = Pipeline([
            transport.input(),
            stt,
            user_idle_processor,
            hold_wake_processor,
            context_aggregator.user(),
            llm,
            tts,
            transport.output(),
            context_aggregator.assistant(),
        ])

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

    runner = PipelineRunner(handle_sigint=runner_args.handle_sigint)
    await runner.run(task)


async def bot(runner_args: RunnerArguments):
    """Main bot entry point for Pipecat Cloud."""
    transport = await create_transport(runner_args, transport_params)
    await run_bot(transport, runner_args)


if __name__ == "__main__":
    from pipecat.runner.run import main
    main()
