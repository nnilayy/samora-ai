#
# Function Schemas - LLM function definitions for Pipecat
#

from pipecat.adapters.schemas.function_schema import FunctionSchema

from .function_descriptions import HOLD_FUNCTION_DESCRIPTION, END_CALL_FUNCTION_DESCRIPTION


# ============ CONTROL FUNCTIONS ============

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


# ============ HOTEL BOOKING FUNCTIONS ============

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
