from db import db
from pipecat.services.llm_service import FunctionCallParams


async def lookup_booking(
    params: FunctionCallParams,
    confirmation_number: str = None,
    guest_name: str = None,
    guest_email: str = None,
    guest_phone: str = None,
):
    """Look up an existing reservation.

    Use when a guest wants to: confirm their booking details, check their reservation status,
    know more about their upcoming stay, verify room type or dates, or look up their booking.
    Ask the guest for their confirmation number, name, email, or phone number to find their booking.

    Args:
        confirmation_number: The booking confirmation number (e.g., GV-2025-001001).
        guest_name: The guest's full or partial name.
        guest_email: The guest's email address.
        guest_phone: The guest's phone number.
    """
    # Build query based on provided parameters
    query = {}

    if confirmation_number:
        # Exact match for confirmation number (case-insensitive)
        query["confirmation_number"] = {"$regex": confirmation_number, "$options": "i"}
    elif guest_email:
        # Exact match for email (case-insensitive)
        query["guest_email"] = {"$regex": f"^{guest_email}$", "$options": "i"}
    elif guest_phone:
        # Partial match for phone (in case formatting differs)
        # Remove common phone formatting characters for matching
        clean_phone = (
            guest_phone.replace("-", "")
            .replace(" ", "")
            .replace("(", "")
            .replace(")", "")
            .replace("+", "")
        )
        query["guest_phone"] = {"$regex": clean_phone}
    elif guest_name:
        # Partial match for guest name (case-insensitive)
        query["guest_name"] = {"$regex": guest_name, "$options": "i"}
    else:
        await params.result_callback(
            {
                "error": "Please provide at least one of: confirmation number, guest name, email, or phone number"
            }
        )
        return

    # Find matching bookings
    bookings_list = await db.bookings.find(query).to_list(10)

    if not bookings_list:
        await params.result_callback(
            {
                "found": False,
                "message": "No booking found with the provided information. Please double-check and try again.",
            }
        )
        return

    # Format results
    results = []
    for booking in bookings_list:
        results.append(
            {
                "confirmation_number": booking["confirmation_number"],
                "guest_name": booking["guest_name"],
                "guest_email": booking["guest_email"],
                "guest_phone": booking["guest_phone"],
                "room_number": booking["room_number"],
                "room_type": booking["room_type"],
                "floor": booking["floor"],
                "check_in_date": booking["check_in_date"],
                "check_out_date": booking["check_out_date"],
                "num_guests": booking["num_guests"],
                "price_per_night": booking["price_per_night"],
                "total_price": booking["total_price"],
                "status": booking["status"],
                "special_requests": booking.get("special_requests", []),
            }
        )

    if len(results) == 1:
        result = {"found": True, "booking": results[0]}
    else:
        result = {
            "found": True,
            "message": f"Found {len(results)} bookings matching your search",
            "bookings": results,
        }

    await params.result_callback(result)
