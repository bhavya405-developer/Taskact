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

async def seed_categories_and_clients():
    """Seed initial categories and clients"""
    
    # Get Sarah Johnson's ID (Partner) as creator
    sarah = await db.users.find_one({"email": "sarah@firm.com"})
    if not sarah:
        print("❌ Sarah Johnson (Partner) not found. Please create partner first.")
        return
    
    creator_id = sarah["id"]
    
    # Initial categories
    categories = [
        {
            "id": str(uuid.uuid4()),
            "name": "Legal Research",
            "description": "Research legal precedents, statutes, and case law",
            "color": "#3B82F6",
            "created_by": creator_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "active": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Contract Review",
            "description": "Review and analysis of legal contracts and agreements",
            "color": "#10B981",
            "created_by": creator_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "active": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Client Meeting",
            "description": "Meetings and consultations with clients",
            "color": "#F59E0B",
            "created_by": creator_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "active": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Court Filing",
            "description": "Prepare and file court documents and motions",
            "color": "#EF4444",
            "created_by": creator_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "active": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Document Preparation",
            "description": "Draft legal documents, briefs, and correspondence",
            "color": "#8B5CF6",
            "created_by": creator_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "active": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Due Diligence",
            "description": "Comprehensive investigation and analysis for transactions",
            "color": "#06B6D4",
            "created_by": creator_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "active": True
        }
    ]
    
    # Initial clients
    clients = [
        {
            "id": str(uuid.uuid4()),
            "name": "TechCorp Inc.",
            "company_type": "Corporation",
            "industry": "Technology",
            "contact_person": "John Smith",
            "email": "john.smith@techcorp.com",
            "phone": "+1 (555) 123-4567",
            "address": "123 Tech Street, Silicon Valley, CA 94000",
            "notes": "Major technology client focused on software development and AI",
            "created_by": creator_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "active": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Global Manufacturing Ltd.",
            "company_type": "Corporation",
            "industry": "Manufacturing",
            "contact_person": "Maria Rodriguez",
            "email": "maria@globalmanufacturing.com",
            "phone": "+1 (555) 987-6543",
            "address": "456 Industrial Blvd, Detroit, MI 48000",
            "notes": "Large manufacturing company with international operations",
            "created_by": creator_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "active": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Healthcare Solutions Group",
            "company_type": "LLC",
            "industry": "Healthcare",
            "contact_person": "Dr. James Wilson",
            "email": "j.wilson@healthcaresolutions.com",
            "phone": "+1 (555) 456-7890",
            "address": "789 Medical Center Dr, Boston, MA 02000",
            "notes": "Healthcare consulting and medical device company",
            "created_by": creator_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "active": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Renewable Energy Partners",
            "company_type": "Partnership",
            "industry": "Energy",
            "contact_person": "Sarah Green",
            "email": "sarah@renewableenergy.com",
            "phone": "+1 (555) 321-9876",
            "address": "321 Green Energy Way, Austin, TX 78000",
            "notes": "Clean energy investment and development firm",
            "created_by": creator_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "active": True
        }
    ]
    
    # Insert categories
    for category in categories:
        existing = await db.categories.find_one({"name": category["name"]})
        if not existing:
            await db.categories.insert_one(category)
            print(f"✅ Created category: {category['name']}")
        else:
            print(f"⚠️  Category already exists: {category['name']}")
    
    # Insert clients
    for client in clients:
        existing = await db.clients.find_one({"name": client["name"]})
        if not existing:
            await db.clients.insert_one(client)
            print(f"✅ Created client: {client['name']}")
        else:
            print(f"⚠️  Client already exists: {client['name']}")
    
    await client.close()
    print("\n🎉 Seeding completed!")

if __name__ == "__main__":
    asyncio.run(seed_categories_and_clients())