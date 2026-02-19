"""
Migration script for TaskAct Multi-Tenant Architecture
Run this script once to migrate existing data to multi-tenant structure.

This script will:
1. Create the "Sundesha & Co LLP" tenant with code 'SCO1'
2. Add tenant_id to all existing documents in:
   - users
   - tasks
   - clients
   - categories
   - attendance
   - notifications
   - holidays
   - geofence_settings
   - attendance_rules
   - otp_records

Usage: python -m routes.migration
"""
import asyncio
import os
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path
import uuid

# Load environment variables
ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')


async def run_migration():
    """Run the multi-tenant migration"""
    
    # Connect to MongoDB
    mongo_url = os.environ['MONGO_URL']
    client = AsyncIOMotorClient(mongo_url)
    db = client[os.environ['DB_NAME']]
    
    print("=" * 60)
    print("TaskAct Multi-Tenant Migration")
    print("=" * 60)
    
    # Step 1: Check if migration already ran
    existing_tenant = await db.tenants.find_one({"code": "SCO1"})
    if existing_tenant:
        print("\n[SKIP] Migration already completed. Tenant 'SCO1' exists.")
        tenant_id = existing_tenant["id"]
    else:
        # Step 2: Create Sundesha & Co LLP tenant
        print("\n[1/3] Creating tenant: Sundesha & Co LLP (Code: SCO1)")
        
        tenant_id = str(uuid.uuid4())
        tenant = {
            "id": tenant_id,
            "name": "Sundesha & Co LLP",
            "code": "SCO1",
            "contact_email": "bhavika@sundesha.in",
            "contact_phone": None,
            "address": None,
            "plan": "premium",
            "max_users": 100,
            "active": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "created_by": "migration_script"
        }
        
        await db.tenants.insert_one(tenant)
        print(f"    ✓ Tenant created with ID: {tenant_id}")
    
    # Step 3: Migrate all collections
    print("\n[2/3] Adding tenant_id to existing documents...")
    
    collections_to_migrate = [
        "users",
        "tasks",
        "clients",
        "categories",
        "attendance",
        "notifications",
        "holidays",
        "otp_records"
    ]
    
    total_updated = 0
    
    for collection_name in collections_to_migrate:
        collection = db[collection_name]
        
        # Count documents without tenant_id
        count = await collection.count_documents({"tenant_id": {"$exists": False}})
        
        if count > 0:
            # Update all documents without tenant_id
            result = await collection.update_many(
                {"tenant_id": {"$exists": False}},
                {"$set": {"tenant_id": tenant_id}}
            )
            print(f"    ✓ {collection_name}: {result.modified_count} documents updated")
            total_updated += result.modified_count
        else:
            existing = await collection.count_documents({})
            print(f"    - {collection_name}: {existing} documents (already migrated or empty)")
    
    # Step 4: Handle singleton collections (geofence_settings, attendance_rules)
    print("\n[3/3] Migrating singleton settings...")
    
    # Geofence settings
    geofence = await db.geofence_settings.find_one({"id": "geofence_settings"})
    if geofence and "tenant_id" not in geofence:
        await db.geofence_settings.update_one(
            {"id": "geofence_settings"},
            {"$set": {"tenant_id": tenant_id}}
        )
        print("    ✓ geofence_settings: migrated")
    else:
        print("    - geofence_settings: already migrated or not found")
    
    # Attendance rules
    rules = await db.attendance_rules.find_one({"id": "attendance_rules"})
    if rules and "tenant_id" not in rules:
        await db.attendance_rules.update_one(
            {"id": "attendance_rules"},
            {"$set": {"tenant_id": tenant_id}}
        )
        print("    ✓ attendance_rules: migrated")
    else:
        print("    - attendance_rules: already migrated or not found")
    
    # Step 5: Create indexes for tenant_id
    print("\n[INDEXES] Creating tenant_id indexes...")
    
    for collection_name in collections_to_migrate + ["geofence_settings", "attendance_rules"]:
        try:
            await db[collection_name].create_index("tenant_id")
            print(f"    ✓ {collection_name}: index created")
        except Exception as e:
            print(f"    - {collection_name}: index may already exist ({str(e)[:50]})")
    
    # Summary
    print("\n" + "=" * 60)
    print("Migration Complete!")
    print("=" * 60)
    print(f"\nTenant: Sundesha & Co LLP")
    print(f"Code: SCO1")
    print(f"Tenant ID: {tenant_id}")
    print(f"Total documents updated: {total_updated}")
    print("\nNote: Users can now login with:")
    print("  - Company Code: SCO1")
    print("  - Email: <their email>")
    print("  - Password: <their password>")
    
    client.close()


if __name__ == "__main__":
    asyncio.run(run_migration())
