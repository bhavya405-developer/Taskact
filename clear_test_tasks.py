#!/usr/bin/env python3
"""
Script to clear all test tasks from TaskAct database
"""

import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime

# Database configuration
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = "test_database"

async def clear_all_tasks():
    """Clear all tasks from the database"""
    
    # Connect to MongoDB
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    try:
        # Get current task count
        task_count = await db.tasks.count_documents({})
        print(f"Found {task_count} tasks to delete...")
        
        if task_count > 0:
            # Delete all tasks
            result = await db.tasks.delete_many({})
            print(f"✅ Successfully deleted {result.deleted_count} tasks")
            
            # Also clear any task-related notifications
            notification_result = await db.notifications.delete_many({
                "task_id": {"$exists": True, "$ne": None}
            })
            print(f"✅ Deleted {notification_result.deleted_count} task-related notifications")
            
        else:
            print("No tasks found to delete")
            
    except Exception as e:
        print(f"❌ Error clearing tasks: {e}")
    finally:
        client.close()
        print("Database connection closed")

if __name__ == "__main__":
    print("=== TaskAct Test Data Cleanup ===")
    print("Clearing ALL test tasks from the database...")
    asyncio.run(clear_all_tasks())
    print("✅ Task cleanup completed!")