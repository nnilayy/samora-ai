from db import db
from pipecat.services.llm_service import FunctionCallParams


async def get_amenities(params: FunctionCallParams, room_type: str):
    """Get the list of amenities for a specific room type.

    Use when the caller asks what's included in a room, what features it has,
    or what amenities are available.

    Args:
        room_type: The room type to get amenities for (standard, deluxe, suite).
    """
    if not room_type:
        result = {"error": "Please specify a room type: standard, deluxe, or suite"}
    else:
        room = await db.rooms.find_one({"room_type": room_type})

        if room:
            result = {"room_type": room["room_type"], "amenities": room["amenities"]}
        else:
            result = {"error": f"Room type '{room_type}' not found"}

    await params.result_callback(result)
