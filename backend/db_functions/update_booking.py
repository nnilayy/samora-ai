from datetime import datetime
from db import db
from pipecat.services.llm_service import FunctionCallParams


async def update_booking(
    params: FunctionCallParams,
    confirmation_number: str = None,
    guest_name: str = None,
    guest_email: str = None,
    new_check_in_date: str = None,
    new_check_out_date: str = None,
    new_room_type: str = None,
    new_num_guests: int = None,
):
    """Modify an existing reservation.

    Can update check-in date, check-out date, room type, or number of guests.
    First look up the booking, then ask what they want to change.

    Args:
        confirmation_number: The booking confirmation number.
        guest_name: Guest's name (alternative to confirmation number).
        guest_email: Guest's email (alternative to confirmation number).
        new_check_in_date: New check-in date in YYYY-MM-DD format.
        new_check_out_date: New check-out date in YYYY-MM-DD format.
        new_room_type: New room type (standard, deluxe, suite).
        new_num_guests: New number of guests.
    """
    rooms = db["rooms"]
    bookings = db["bookings"]

    # Build query to find the booking
    query = {}
    if confirmation_number:
        query["confirmation_number"] = confirmation_number.upper()
    elif guest_email:
        query["guest_email"] = guest_email.lower()
    elif guest_name:
        query["guest_name"] = {"$regex": guest_name, "$options": "i"}
    else:
        await params.result_callback(
            {
                "success": False,
                "error": "Please provide a confirmation number, name, or email to find the booking.",
            }
        )
        return

    # Find the booking
    booking = await bookings.find_one(query)

    if not booking:
        await params.result_callback(
            {
                "success": False,
                "error": "No booking found with the provided information.",
            }
        )
        return

    # Check if booking is in the past
    original_check_in = datetime.strptime(booking["check_in_date"], "%Y-%m-%d")
    if original_check_in.date() < datetime.now().date():
        await params.result_callback(
            {
                "success": False,
                "error": "Cannot modify a booking that has already started or is in the past.",
            }
        )
        return

    # Prepare update fields
    updates = {}

    # Room capacity by type
    room_capacity = {"standard": 2, "deluxe": 3, "suite": 4}
    room_prices = {"standard": 100, "deluxe": 150, "suite": 250}

    # Determine the room type to use for validation
    target_room_type = new_room_type.lower() if new_room_type else booking["room_type"]

    # Validate new room type if provided
    if new_room_type:
        new_room_type = new_room_type.lower()
        if new_room_type not in ["standard", "deluxe", "suite"]:
            await params.result_callback(
                {
                    "success": False,
                    "error": f"Invalid room type '{new_room_type}'. Choose from: standard, deluxe, or suite.",
                }
            )
            return
        updates["room_type"] = new_room_type
        updates["price_per_night"] = room_prices[new_room_type]

    # Validate new number of guests
    if new_num_guests:
        max_guests = room_capacity.get(target_room_type, 2)
        if new_num_guests > max_guests:
            await params.result_callback(
                {
                    "success": False,
                    "error": f"A {target_room_type} room can only accommodate {max_guests} guests. You requested {new_num_guests}.",
                }
            )
            return
        updates["num_guests"] = new_num_guests

    # Validate new dates
    check_in_date = new_check_in_date if new_check_in_date else booking["check_in_date"]
    check_out_date = (
        new_check_out_date if new_check_out_date else booking["check_out_date"]
    )

    if new_check_in_date or new_check_out_date:
        try:
            check_in = datetime.strptime(check_in_date, "%Y-%m-%d")
            check_out = datetime.strptime(check_out_date, "%Y-%m-%d")
        except ValueError:
            await params.result_callback(
                {
                    "success": False,
                    "error": "Invalid date format. Please use YYYY-MM-DD format.",
                }
            )
            return

        if check_in >= check_out:
            await params.result_callback(
                {
                    "success": False,
                    "error": "Check-out date must be after check-in date.",
                }
            )
            return

        if check_in.date() < datetime.now().date():
            await params.result_callback(
                {"success": False, "error": "Check-in date cannot be in the past."}
            )
            return

        if new_check_in_date:
            updates["check_in_date"] = new_check_in_date
        if new_check_out_date:
            updates["check_out_date"] = new_check_out_date

    # If no updates provided
    if not updates:
        await params.result_callback(
            {
                "success": False,
                "error": "No changes provided. Please specify what you'd like to update.",
            }
        )
        return

    # Check room availability if dates or room type changed
    if new_check_in_date or new_check_out_date or new_room_type:
        # Find rooms that are booked during the new period (excluding current booking)
        booked_rooms_cursor = bookings.find(
            {
                "confirmation_number": {"$ne": booking["confirmation_number"]},
                "room_type": target_room_type,
                "$and": [
                    {"check_in_date": {"$lt": check_out_date}},
                    {"check_out_date": {"$gt": check_in_date}},
                ],
            }
        )

        booked_room_numbers = set()
        async for b in booked_rooms_cursor:
            booked_room_numbers.add(b["room_number"])

        # Get all rooms of the target type
        all_rooms = await rooms.find({"room_type": target_room_type}).to_list(
            length=None
        )
        available_rooms = [
            r for r in all_rooms if r["room_number"] not in booked_room_numbers
        ]

        if not available_rooms:
            await params.result_callback(
                {
                    "success": False,
                    "error": f"Sorry, no {target_room_type} rooms are available for the new dates. Please try different dates.",
                }
            )
            return

        # If changing room type, assign a new room
        if new_room_type and new_room_type != booking["room_type"]:
            import random

            new_room = random.choice(available_rooms)
            updates["room_number"] = new_room["room_number"]
            updates["floor"] = new_room["floor"]

    # Recalculate total price
    final_check_in = datetime.strptime(check_in_date, "%Y-%m-%d")
    final_check_out = datetime.strptime(check_out_date, "%Y-%m-%d")
    nights = (final_check_out - final_check_in).days
    price_per_night = updates.get("price_per_night", booking["price_per_night"])
    updates["total_price"] = price_per_night * nights

    # Add timestamp
    updates["updated_at"] = datetime.utcnow()

    # Perform the update
    update_result = await bookings.update_one(
        {"_id": booking["_id"]}, {"$set": updates}
    )

    if update_result.modified_count == 1:
        # Get the updated booking
        updated_booking = await bookings.find_one({"_id": booking["_id"]})

        await params.result_callback(
            {
                "success": True,
                "message": "Booking has been successfully updated.",
                "updated_booking": {
                    "confirmation_number": updated_booking["confirmation_number"],
                    "guest_name": updated_booking["guest_name"],
                    "room_type": updated_booking["room_type"],
                    "room_number": updated_booking["room_number"],
                    "check_in_date": updated_booking["check_in_date"],
                    "check_out_date": updated_booking["check_out_date"],
                    "nights": nights,
                    "num_guests": updated_booking["num_guests"],
                    "price_per_night": updated_booking["price_per_night"],
                    "total_price": updated_booking["total_price"],
                },
                "changes_made": list(updates.keys()),
            }
        )
    else:
        await params.result_callback(
            {"success": False, "error": "Failed to update booking. Please try again."}
        )
