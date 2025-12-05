from datetime import datetime
from db import db
from pipecat.services.llm_service import FunctionCallParams


async def add_special_request(
    params: FunctionCallParams,
    confirmation_number: str = None,
    guest_name: str = None,
    guest_email: str = None,
    request: str = None,
):
    """Add a special request to an existing booking.

    Use when a guest wants to add requests like late check-in, early check-in, extra pillows,
    extra towels, baby crib, anniversary setup, champagne, dietary requirements, or any other
    special accommodation. First look up their booking, then add the request.

    Args:
        confirmation_number: The booking confirmation number.
        guest_name: The guest's name (alternative to confirmation number).
        guest_email: The guest's email (alternative to confirmation number).
        request: The special request to add (e.g., 'late check-in', 'extra pillows', 'baby crib').
    """
    # Validate request is provided
    if not request:
        await params.result_callback(
            {
                "success": False,
                "error": "Please specify what special request you'd like to add.",
            }
        )
        return

    # Build query to find the booking
    query = {}
    lookup_method = ""

    if confirmation_number:
        query["confirmation_number"] = {"$regex": confirmation_number, "$options": "i"}
        lookup_method = f"confirmation number {confirmation_number}"
    elif guest_email:
        query["guest_email"] = {"$regex": f"^{guest_email}$", "$options": "i"}
        lookup_method = f"email {guest_email}"
    elif guest_name:
        query["guest_name"] = {"$regex": guest_name, "$options": "i"}
        lookup_method = f"name {guest_name}"
    else:
        await params.result_callback(
            {
                "success": False,
                "error": "Please provide a confirmation number, guest name, or email to find the booking.",
            }
        )
        return

    # Find the booking first
    booking = await db.bookings.find_one(query)

    if not booking:
        await params.result_callback(
            {
                "success": False,
                "error": f"No booking found with {lookup_method}. Please verify the information.",
            }
        )
        return

    # Check if request already exists
    existing_requests = booking.get("special_requests", [])
    if request.lower() in [r.lower() for r in existing_requests]:
        await params.result_callback(
            {
                "success": True,
                "message": f"'{request}' is already noted on your reservation.",
                "confirmation_number": booking["confirmation_number"],
                "guest_name": booking["guest_name"],
                "all_requests": existing_requests,
            }
        )
        return

    # Add the special request
    update_result = await db.bookings.update_one(
        {"_id": booking["_id"]},
        {
            "$push": {"special_requests": request},
            "$set": {"updated_at": datetime.utcnow()},
        },
    )

    if update_result.modified_count > 0:
        updated_requests = existing_requests + [request]
        await params.result_callback(
            {
                "success": True,
                "message": f"I've added '{request}' to your reservation.",
                "confirmation_number": booking["confirmation_number"],
                "guest_name": booking["guest_name"],
                "all_requests": updated_requests,
            }
        )
    else:
        await params.result_callback(
            {
                "success": False,
                "error": "Something went wrong while updating the booking. Please try again.",
            }
        )
