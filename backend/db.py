import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

# Connect to MongoDB with SSL fix for compatibility
mongodb_uri = os.getenv("MONGODB_URI")
# Add TLS options if not already present
if "?" in mongodb_uri:
    mongodb_uri += "&tls=true&tlsAllowInvalidCertificates=true"
else:
    mongodb_uri += "?tls=true&tlsAllowInvalidCertificates=true"

client = AsyncIOMotorClient(mongodb_uri)

# Get the hotel_db database
db = client["hotel_db"]
