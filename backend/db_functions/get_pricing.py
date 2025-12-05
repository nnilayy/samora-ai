from db import db
from pipecat.services.llm_service import FunctionCallParams


async def get_pricing(params: FunctionCallParams, room_type: str = None):
    """Get room pricing information.

    Call without room_type to get all prices, or specify a type for specific pricing.
    Use when the caller asks about rates, costs, or how much rooms are.

    Args:
        room_type: The room type to get pricing for (standard, deluxe, suite). Optional - omit to get all room prices.
    """
    if room_type:
        # Get price for specific room type
        room = await db.rooms.find_one({"room_type": room_type})
        if room:
            result = {
                "room_type": room["room_type"],
                "price_per_night": room["price_per_night"],
                "capacity": room["capacity"],
            }
        else:
            result = {"error": f"Room type '{room_type}' not found"}
    else:
        # Get all room types with prices
        pipeline = [
            {
                "$group": {
                    "_id": "$room_type",
                    "price_per_night": {"$first": "$price_per_night"},
                    "capacity": {"$first": "$capacity"},
                }
            }
        ]
        rooms = await db.rooms.aggregate(pipeline).to_list(10)
        result = {
            "pricing": [
                {
                    "room_type": r["_id"],
                    "price_per_night": r["price_per_night"],
                    "capacity": r["capacity"],
                }
                for r in rooms
            ]
        }

    await params.result_callback(result)
