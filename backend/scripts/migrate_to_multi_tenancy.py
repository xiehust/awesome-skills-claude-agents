#!/usr/bin/env python3
"""Migration script: Add multi-tenancy support to existing data.

This script:
1. Creates a "default-tenant" in the tenants table
2. Backfills tenant_id = "default-tenant" on all existing resources
3. Sets tenant_id = "__SYSTEM__" on skills where is_system=True
4. Assigns all existing users tenant_id = "default-tenant", role = "admin"

Run this BEFORE adding GSIs (DynamoDB only indexes items that have the partition key).

Usage:
    cd backend
    python scripts/migrate_to_multi_tenancy.py
"""
import asyncio
import sys
import os
from datetime import datetime

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings


async def get_dynamodb_resource():
    """Get a DynamoDB resource."""
    import aioboto3
    session = aioboto3.Session()
    kwargs = {"region_name": settings.aws_region}
    if settings.aws_access_key_id:
        kwargs["aws_access_key_id"] = settings.aws_access_key_id
        kwargs["aws_secret_access_key"] = settings.aws_secret_access_key
    return session, kwargs


async def scan_all_items(table):
    """Scan all items from a DynamoDB table, handling pagination."""
    items = []
    response = await table.scan()
    items.extend(response.get("Items", []))
    while "LastEvaluatedKey" in response:
        response = await table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
        items.extend(response.get("Items", []))
    return items


async def migrate():
    """Run the migration."""
    session, kwargs = await get_dynamodb_resource()

    default_tenant_id = "default-tenant"
    system_tenant_id = "__SYSTEM__"
    now = datetime.now().isoformat()

    async with session.resource("dynamodb", **kwargs) as dynamodb:
        # Step 1: Create default tenant
        print("\n=== Step 1: Create default tenant ===")
        tenants_table = await dynamodb.Table(settings.dynamodb_tenants_table)

        # Check if default tenant already exists
        response = await tenants_table.get_item(Key={"id": default_tenant_id})
        if "Item" in response:
            print(f"  Default tenant already exists: {response['Item'].get('name')}")
        else:
            tenant_item = {
                "id": default_tenant_id,
                "name": "Default Tenant",
                "slug": "default",
                "owner_user_id": "",  # Will be updated when first user is assigned
                "plan": "free",
                "max_agents": 100,
                "max_skills": 500,
                "max_mcp_servers": 100,
                "rate_limit_per_minute": 1000,
                "status": "active",
                "created_at": now,
                "updated_at": now,
            }
            await tenants_table.put_item(Item=tenant_item)
            print(f"  Created default tenant: {default_tenant_id}")

        # Step 2: Backfill tenant_id on all resource tables
        print("\n=== Step 2: Backfill tenant_id on resource tables ===")

        # Handle agents table specially - "default" agent gets __SYSTEM__
        print("\n  Processing agents...")
        try:
            agents_table = await dynamodb.Table(settings.dynamodb_agents_table)
            agents = await scan_all_items(agents_table)
            updated = 0
            for agent in agents:
                if not agent.get("tenant_id"):
                    tid = system_tenant_id if agent.get("id") == "default" else default_tenant_id
                    await agents_table.update_item(
                        Key={"id": agent["id"]},
                        UpdateExpression="SET tenant_id = :tid, updated_at = :now",
                        ExpressionAttributeValues={":tid": tid, ":now": now},
                    )
                    updated += 1
            print(f"  Updated {updated}/{len(agents)} agents (default agent -> __SYSTEM__)")
        except Exception as e:
            print(f"  Warning: Error processing agents: {e}")

        tables_to_backfill = [
            (settings.dynamodb_mcp_table, "mcp_servers"),
            (settings.dynamodb_sessions_table, "sessions"),
            (settings.dynamodb_messages_table, "messages"),
            (settings.dynamodb_plugins_table, "plugins"),
            (settings.dynamodb_settings_table, "settings"),
            (settings.dynamodb_skill_versions_table, "skill_versions"),
        ]

        for table_name, label in tables_to_backfill:
            print(f"\n  Processing {label} ({table_name})...")
            try:
                table = await dynamodb.Table(table_name)
                items = await scan_all_items(table)
                updated = 0
                for item in items:
                    if not item.get("tenant_id"):
                        await table.update_item(
                            Key={"id": item["id"]},
                            UpdateExpression="SET tenant_id = :tid, updated_at = :now",
                            ExpressionAttributeValues={
                                ":tid": default_tenant_id,
                                ":now": now,
                            },
                        )
                        updated += 1
                print(f"  Updated {updated}/{len(items)} items in {label}")
            except Exception as e:
                print(f"  ⚠️  Error processing {label}: {e}")

        # Step 3: Handle skills table specially (system skills)
        print("\n=== Step 3: Backfill skills with system skill handling ===")
        try:
            skills_table = await dynamodb.Table(settings.dynamodb_skills_table)
            skills = await scan_all_items(skills_table)
            updated_tenant = 0
            updated_system = 0
            for skill in skills:
                if not skill.get("tenant_id"):
                    if skill.get("is_system", False):
                        tid = system_tenant_id
                        updated_system += 1
                    else:
                        tid = default_tenant_id
                        updated_tenant += 1
                    await skills_table.update_item(
                        Key={"id": skill["id"]},
                        UpdateExpression="SET tenant_id = :tid, updated_at = :now",
                        ExpressionAttributeValues={
                            ":tid": tid,
                            ":now": now,
                        },
                    )
            print(f"  Updated {updated_tenant} tenant skills, {updated_system} system skills (of {len(skills)} total)")
        except Exception as e:
            print(f"  ⚠️  Error processing skills: {e}")

        # Step 4: Update users with tenant_id and role
        print("\n=== Step 4: Assign users to default tenant ===")
        try:
            users_table = await dynamodb.Table(settings.dynamodb_users_table)
            users = await scan_all_items(users_table)
            updated = 0
            first_user_id = None
            for user in users:
                if not user.get("tenant_id"):
                    if first_user_id is None:
                        first_user_id = user["id"]
                    await users_table.update_item(
                        Key={"id": user["id"]},
                        UpdateExpression="SET tenant_id = :tid, #r = :role, is_platform_admin = :admin, updated_at = :now",
                        ExpressionAttributeNames={"#r": "role"},
                        ExpressionAttributeValues={
                            ":tid": default_tenant_id,
                            ":role": "admin",
                            ":admin": False,
                            ":now": now,
                        },
                    )
                    updated += 1
            print(f"  Updated {updated}/{len(users)} users")

            # Set first user as tenant owner
            if first_user_id:
                await users_table.update_item(
                    Key={"id": first_user_id},
                    UpdateExpression="SET #r = :role",
                    ExpressionAttributeNames={"#r": "role"},
                    ExpressionAttributeValues={":role": "owner"},
                )
                await tenants_table.update_item(
                    Key={"id": default_tenant_id},
                    UpdateExpression="SET owner_user_id = :uid",
                    ExpressionAttributeValues={":uid": first_user_id},
                )
                print(f"  Set user {first_user_id} as tenant owner")
        except Exception as e:
            print(f"  ⚠️  Error processing users: {e}")

    print("\n=== Migration complete! ===")
    print("Next steps:")
    print("  1. Run init-aws.sh to add GSIs to tables")
    print("  2. Wait for GSIs to finish building (check AWS console)")
    print("  3. Deploy updated backend code")


if __name__ == "__main__":
    asyncio.run(migrate())
