#!/usr/bin/env python3

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
ROOT_DIR = Path(__file__).parent / "backend"
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    return pwd_context.hash(password)

async def add_passwords():
    """Add default passwords to existing users"""
    
    # Define default passwords for existing users
    user_passwords = {
        "sarah@firm.com": "password123",  # Partner
        "michael@firm.com": "password123",  # Associate  
        "emma@firm.com": "password123"  # Junior
    }
    
    for email, password in user_passwords.items():
        password_hash = get_password_hash(password)
        
        result = await db.users.update_one(
            {"email": email},
            {"$set": {"password_hash": password_hash}}
        )
        
        if result.modified_count > 0:
            print(f"✅ Added password for {email}")
        else:
            print(f"❌ Could not update password for {email}")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(add_passwords())