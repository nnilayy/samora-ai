from datetime import datetime
from db import db
from pipecat.services.llm_service import FunctionCallParams


async def cancel_booking(
    params: FunctionCallParams,
    confirmation_number: str = None,
    guest_name: str = None,
    guest_email: str = None,
):
    """Cancel an existing reservation.

    Use when a guest wants to cancel their booking. Always confirm with the guest before cancelling.
    Requires confirmation number, name, or email to find the booking.

    Args:
        confirmation_number: The booking confirmation number.
        guest_name: The guest's name (alternative to confirmation number).
        guest_email: The guest's email (alternative to confirmation number).
    """
    bookings = db["bookings"]

    # Build query based on provided parameters
    query = {}

    if confirmation_number:
        query["confirmation_number"] = confirmation_number.upper()
    elif guest_email:
        query["guest_email"] = guest_email.lower()
    elif guest_name:
        # Case-insensitive partial match
        query["guest_name"] = {"$regex": guest_name, "$options": "i"}
    else:
        await params.result_callback(
            {
                "success": False,
                "error": "Please provide a confirmation number, name, or email to find the booking.",
            }
        )
        return

    # Find the booking first
    booking = await bookings.find_one(query)

    if not booking:
        await params.result_callback(
            {
                "success": False,
                "error": "No booking found with the provided information.",
            }
        )
        return

    # Check if it's a past booking
    check_in_date = datetime.strptime(booking["check_in_date"], "%Y-%m-%d")
    if check_in_date.date() < datetime.now().date():
        await params.result_callback(
            {
                "success": False,
                "error": "Cannot cancel a booking for a past date.",
                "booking": {
                    "confirmation_number": booking["confirmation_number"],
                    "check_in_date": booking["check_in_date"],
                    "status": booking["status"],
                },
            }
        )
        return

    # Store booking details before deletion
    cancelled_booking = {
        "confirmation_number": booking["confirmation_number"],
        "guest_name": booking["guest_name"],
        "room_number": booking["room_number"],
        "room_type": booking["room_type"],
        "check_in_date": booking["check_in_date"],
        "check_out_date": booking["check_out_date"],
    }

    # Delete the booking
    delete_result = await bookings.delete_one({"_id": booking["_id"]})

    if delete_result.deleted_count == 1:
        await params.result_callback(
            {
                "success": True,
                "message": "Booking has been successfully cancelled and removed.",
                "cancelled_booking": cancelled_booking,
            }
        )
    else:
        await params.result_callback(
            {"success": False, "error": "Failed to cancel booking. Please try again."}
        )
