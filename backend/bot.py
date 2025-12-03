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
# from pipecat.services.cartesia.tts import CartesiaTTSService
from pipecat.services.elevenlabs.tts import ElevenLabsTTSService
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.elevenlabs.stt import ElevenLabsRealtimeSTTService
from pipecat.services.llm_service import FunctionCallParams
from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.services.cerebras.llm import CerebrasLLMService
from pipecat.transports.base_transport import BaseTransport, TransportParams
from pipecat.transports.websocket.fastapi import FastAPIWebsocketParams
# from pipecat.services.openai.llm import OpenAILLMService
from pipecat.services.groq.llm import GroqLLMService
# from pipecat.transports.daily.transport import DailyParams

from prompts import (
    SYSTEM_PROMPT,
    USER_IDLE_PROMPTS,
    WAKE_PROMPTS,
    HOLD_FUNCTION_DESCRIPTION,
    END_CALL_FUNCTION_DESCRIPTION,
)
from db_functions import get_pricing, get_amenities, lookup_booking, add_special_request, cancel_booking, check_availability, book_room, update_booking


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

    # ============ STT ============
    stt = ElevenLabsRealtimeSTTService(
        api_key=os.getenv("ELEVENLABS_API_KEY", ""),
        model="scribe_v2_realtime",
    )
    # stt = DeepgramSTTService(
    #     api_key=os.getenv("DEEPGRAM_API_KEY", ""),
    # )

    # ============ LLM ============
    llm = CerebrasLLMService(
        api_key=os.getenv("CEREBRAS_API_KEY", ""),
        model="gpt-oss-120b",
    )
    # llm = OpenAILLMService(
    #     api_key=os.getenv("OPENAI_API_KEY", ""),
    #     model="gpt-4o-mini",
    # )
    # llm = GroqLLMService(
    #     api_key=os.getenv("GROQ_API_KEY", ""),
    #     model="openai/gpt-oss-120b",
    # )

    # ============ TTS ============
    # tts = CartesiaTTSService(
    #     api_key=os.getenv("CARTESIA_API_KEY", ""),
    #     voice_id="11af83e2-23eb-452f-956e-7fee218ccb5c",
    # )
    tts = ElevenLabsTTSService(
        api_key=os.getenv("ELEVENLABS_API_KEY", ""),
        voice_id="cgSgspJ2msm6clMCkdW9",
    )

    # ============ PROCESSORS ============
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
    
    # Hotel booking functions
    get_pricing_function = FunctionSchema(
        name="get_pricing",
        description="Get room pricing. Call without room_type to get all prices, or specify a type for specific pricing.",
        properties={
            "room_type": {
                "type": "string",
                "enum": ["standard", "deluxe", "suite"],
                "description": "The room type to get pricing for. Optional - omit to get all room prices."
            }
        },
        required=[]
    )
    
    get_amenities_function = FunctionSchema(
        name="get_amenities",
        description="Get the list of amenities for a specific room type.",
        properties={
            "room_type": {
                "type": "string",
                "enum": ["standard", "deluxe", "suite"],
                "description": "The room type to get amenities for."
            }
        },
        required=["room_type"]
    )
    
    lookup_booking_function = FunctionSchema(
        name="lookup_booking",
        description="Look up an existing reservation. Use this when a guest wants to: confirm their booking details, check their reservation status, know more about their upcoming stay, verify room type or dates, or just casually look up their booking. Ask the guest for their confirmation number, name, email, or phone number to find their booking.",
        properties={
            "confirmation_number": {
                "type": "string",
                "description": "The booking confirmation number (e.g., GV-2025-001001)"
            },
            "guest_name": {
                "type": "string",
                "description": "The guest's full or partial name"
            },
            "guest_email": {
                "type": "string",
                "description": "The guest's email address"
            },
            "guest_phone": {
                "type": "string",
                "description": "The guest's phone number"
            }
        },
        required=[]
    )
    
    add_special_request_function = FunctionSchema(
        name="add_special_request",
        description="Add a special request to an existing booking. Use this when a guest wants to add requests like late check-in, early check-in, extra pillows, extra towels, baby crib, anniversary setup, champagne, dietary requirements, or any other special accommodation. First look up their booking, then add the request.",
        properties={
            "confirmation_number": {
                "type": "string",
                "description": "The booking confirmation number"
            },
            "guest_name": {
                "type": "string",
                "description": "The guest's name (alternative to confirmation number)"
            },
            "guest_email": {
                "type": "string",
                "description": "The guest's email (alternative to confirmation number)"
            },
            "request": {
                "type": "string",
                "description": "The special request to add (e.g., 'late check-in', 'extra pillows', 'baby crib')"
            }
        },
        required=["request"]
    )
    
    cancel_booking_function = FunctionSchema(
        name="cancel_booking",
        description="Cancel an existing reservation. Use this when a guest wants to cancel their booking. Confirm with the guest before cancelling. Requires confirmation number, name, or email to find the booking.",
        properties={
            "confirmation_number": {
                "type": "string",
                "description": "The booking confirmation number"
            },
            "guest_name": {
                "type": "string",
                "description": "The guest's name (alternative to confirmation number)"
            },
            "guest_email": {
                "type": "string",
                "description": "The guest's email (alternative to confirmation number)"
            }
        },
        required=[]
    )
    
    check_availability_function = FunctionSchema(
        name="check_availability",
        description="Check room availability for specific dates. Use this when a guest wants to know if rooms are available, before making a booking. Returns available room types with pricing.",
        properties={
            "check_in_date": {
                "type": "string",
                "description": "Check-in date in YYYY-MM-DD format (e.g., 2025-12-15)"
            },
            "check_out_date": {
                "type": "string",
                "description": "Check-out date in YYYY-MM-DD format (e.g., 2025-12-18)"
            },
            "room_type": {
                "type": "string",
                "enum": ["standard", "deluxe", "suite"],
                "description": "Optional - filter by specific room type"
            },
            "num_guests": {
                "type": "integer",
                "description": "Optional - number of guests to accommodate"
            }
        },
        required=["check_in_date", "check_out_date"]
    )
    
    book_room_function = FunctionSchema(
        name="book_room",
        description="Create a new room reservation. Use this ONLY after confirming all details with the guest: name, phone, email, room type, dates, and number of guests. Do NOT call this until you have collected all required information.",
        properties={
            "guest_name": {
                "type": "string",
                "description": "Full name of the guest"
            },
            "guest_phone": {
                "type": "string",
                "description": "Guest's phone number"
            },
            "guest_email": {
                "type": "string",
                "description": "Guest's email address"
            },
            "room_type": {
                "type": "string",
                "enum": ["standard", "deluxe", "suite"],
                "description": "Type of room to book"
            },
            "check_in_date": {
                "type": "string",
                "description": "Check-in date in YYYY-MM-DD format"
            },
            "check_out_date": {
                "type": "string",
                "description": "Check-out date in YYYY-MM-DD format"
            },
            "num_guests": {
                "type": "integer",
                "description": "Number of guests staying"
            },
            "special_requests": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional list of special requests"
            }
        },
        required=["guest_name", "guest_phone", "guest_email", "room_type", "check_in_date", "check_out_date", "num_guests"]
    )
    
    update_booking_function = FunctionSchema(
        name="update_booking",
        description="Modify an existing reservation. Can update check-in date, check-out date, room type, or number of guests. First look up the booking, then ask what they want to change.",
        properties={
            "confirmation_number": {
                "type": "string",
                "description": "The booking confirmation number"
            },
            "guest_name": {
                "type": "string",
                "description": "Guest's name (alternative to confirmation number)"
            },
            "guest_email": {
                "type": "string",
                "description": "Guest's email (alternative to confirmation number)"
            },
            "new_check_in_date": {
                "type": "string",
                "description": "New check-in date in YYYY-MM-DD format"
            },
            "new_check_out_date": {
                "type": "string",
                "description": "New check-out date in YYYY-MM-DD format"
            },
            "new_room_type": {
                "type": "string",
                "enum": ["standard", "deluxe", "suite"],
                "description": "New room type"
            },
            "new_num_guests": {
                "type": "integer",
                "description": "New number of guests"
            }
        },
        required=[]
    )
    
    tools = ToolsSchema(standard_tools=[
        hold_function, 
        end_call_function,
        get_pricing_function,
        get_amenities_function,
        lookup_booking_function,
        add_special_request_function,
        cancel_booking_function,
        check_availability_function,
        book_room_function,
        update_booking_function
    ])
    llm.register_function("put_on_hold", put_on_hold)
    llm.register_function("end_call", end_call)
    
    # Register hotel booking functions with wrapper to handle FunctionCallParams
    async def handle_get_pricing(params: FunctionCallParams):
        room_type = params.arguments.get("room_type")
        result = await get_pricing(room_type)
        await params.result_callback(result)
    
    async def handle_get_amenities(params: FunctionCallParams):
        room_type = params.arguments.get("room_type")
        result = await get_amenities(room_type)
        await params.result_callback(result)
    
    async def handle_lookup_booking(params: FunctionCallParams):
        result = await lookup_booking(
            confirmation_number=params.arguments.get("confirmation_number"),
            guest_name=params.arguments.get("guest_name"),
            guest_email=params.arguments.get("guest_email"),
            guest_phone=params.arguments.get("guest_phone")
        )
        await params.result_callback(result)
    
    async def handle_add_special_request(params: FunctionCallParams):
        result = await add_special_request(
            confirmation_number=params.arguments.get("confirmation_number"),
            guest_name=params.arguments.get("guest_name"),
            guest_email=params.arguments.get("guest_email"),
            request=params.arguments.get("request")
        )
        await params.result_callback(result)
    
    async def handle_cancel_booking(params: FunctionCallParams):
        result = await cancel_booking(
            confirmation_number=params.arguments.get("confirmation_number"),
            guest_name=params.arguments.get("guest_name"),
            guest_email=params.arguments.get("guest_email")
        )
        await params.result_callback(result)
    
    llm.register_function("get_pricing", handle_get_pricing)
    llm.register_function("get_amenities", handle_get_amenities)
    llm.register_function("lookup_booking", handle_lookup_booking)
    llm.register_function("add_special_request", handle_add_special_request)
    llm.register_function("cancel_booking", handle_cancel_booking)
    
    async def handle_check_availability(params: FunctionCallParams):
        result = await check_availability(
            check_in_date=params.arguments.get("check_in_date"),
            check_out_date=params.arguments.get("check_out_date"),
            room_type=params.arguments.get("room_type"),
            num_guests=params.arguments.get("num_guests")
        )
        await params.result_callback(result)
    
    llm.register_function("check_availability", handle_check_availability)
    
    async def handle_book_room(params: FunctionCallParams):
        result = await book_room(
            guest_name=params.arguments.get("guest_name"),
            guest_phone=params.arguments.get("guest_phone"),
            guest_email=params.arguments.get("guest_email"),
            room_type=params.arguments.get("room_type"),
            check_in_date=params.arguments.get("check_in_date"),
            check_out_date=params.arguments.get("check_out_date"),
            num_guests=params.arguments.get("num_guests", 1),
            special_requests=params.arguments.get("special_requests")
        )
        await params.result_callback(result)
    
    llm.register_function("book_room", handle_book_room)
    
    async def handle_update_booking(params: FunctionCallParams):
        result = await update_booking(
            confirmation_number=params.arguments.get("confirmation_number"),
            guest_name=params.arguments.get("guest_name"),
            guest_email=params.arguments.get("guest_email"),
            new_check_in_date=params.arguments.get("new_check_in_date"),
            new_check_out_date=params.arguments.get("new_check_out_date"),
            new_room_type=params.arguments.get("new_room_type"),
            new_num_guests=params.arguments.get("new_num_guests")
        )
        await params.result_callback(result)
    
    llm.register_function("update_booking", handle_update_booking)

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
