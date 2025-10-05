#!/usr/bin/env python3

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path
import uuid
from datetime import datetime, timezone

# Load environment variables
ROOT_DIR = Path(__file__).parent / "backend"
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

async def create_sample_notifications():
    """Create sample notifications for testing"""
    
    # Get user IDs
    users = await db.users.find().to_list(length=None)
    user_map = {user['email']: user['id'] for user in users}
    
    # Sample notifications
    notifications = [
        {
            "id": str(uuid.uuid4()),
            "user_id": user_map.get("michael@firm.com"),
            "title": "New Task Assigned",
            "message": "You have been assigned a new task: Draft merger agreement",
            "task_id": None,
            "read": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "user_id": user_map.get("emma@firm.com"),
            "title": "Task Updated",
            "message": "Task 'Prepare for client meeting' has been updated by Sarah Johnson",
            "task_id": None,
            "read": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "user_id": user_map.get("michael@firm.com"),
            "title": "Task Reminder",
            "message": "Task 'Review client contract for ABC Corp' is due tomorrow",
            "task_id": None,
            "read": True,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    ]
    
    for notif in notifications:
        if notif["user_id"]:
            await db.notifications.insert_one(notif)
            print(f"✅ Created notification for user {notif['user_id']}")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(create_sample_notifications())