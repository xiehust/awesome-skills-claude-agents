"""Tenant management API endpoints."""
from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from database import db
from middleware.tenant import TenantContext, get_tenant_context, require_role
from schemas.tenant import (
    TenantCreateRequest,
    TenantUpdateRequest,
    TenantAPIKeyRequest,
    TenantResponse,
    TenantUserResponse,
    InviteUserRequest,
    ChangeUserRoleRequest,
)
from core.key_manager import get_key_manager
from middleware.auth import get_current_user

router = APIRouter(prefix="/tenants", tags=["tenants"])


def _tenant_to_response(tenant: dict) -> dict:
    """Convert tenant record to response format."""
    return {
        "id": tenant.get("id", ""),
        "name": tenant.get("name", ""),
        "slug": tenant.get("slug", ""),
        "owner_user_id": tenant.get("owner_user_id", ""),
        "plan": tenant.get("plan", "free"),
        "max_agents": tenant.get("max_agents", 10),
        "max_skills": tenant.get("max_skills", 50),
        "max_mcp_servers": tenant.get("max_mcp_servers", 20),
        "rate_limit_per_minute": tenant.get("rate_limit_per_minute", 100),
        "status": tenant.get("status", "active"),
        "api_key_set": bool(tenant.get("encrypted_anthropic_api_key")),
        "use_bedrock": tenant.get("use_bedrock", False),
        "anthropic_base_url": tenant.get("anthropic_base_url"),
        "created_at": tenant.get("created_at", ""),
        "updated_at": tenant.get("updated_at", ""),
    }


@router.post("", response_model=TenantResponse)
async def create_tenant(
    request: TenantCreateRequest,
    user: dict = Depends(get_current_user),
):
    """Create a new tenant. The creating user becomes the owner."""
    # Check if slug is already taken
    existing = await db.tenants.get_by_slug(request.slug)
    if existing:
        raise HTTPException(status_code=409, detail="Tenant slug already exists")

    # Check if user already belongs to a tenant
    if user.get("tenant_id"):
        raise HTTPException(status_code=400, detail="User already belongs to a tenant")

    tenant_id = str(uuid4())
    now = datetime.now().isoformat()

    tenant_data = {
        "id": tenant_id,
        "name": request.name,
        "slug": request.slug,
        "owner_user_id": user["id"],
        "plan": "free",
        "max_agents": 10,
        "max_skills": 50,
        "max_mcp_servers": 20,
        "rate_limit_per_minute": 100,
        "status": "active",
        "created_at": now,
        "updated_at": now,
    }

    await db.tenants.put(tenant_data)

    # Update user with tenant_id and owner role
    await db.users.update(user["id"], {
        "tenant_id": tenant_id,
        "role": "owner",
    })

    return _tenant_to_response(tenant_data)


@router.get("/current", response_model=TenantResponse)
async def get_current_tenant(
    ctx: TenantContext = Depends(get_tenant_context),
):
    """Get the current user's tenant information."""
    tenant = await db.tenants.get(ctx.tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return _tenant_to_response(tenant)


@router.put("/current", response_model=TenantResponse)
async def update_current_tenant(
    request: TenantUpdateRequest,
    ctx: TenantContext = Depends(require_role("owner", "admin")),
):
    """Update current tenant settings. Requires owner or admin role."""
    updates = request.model_dump(exclude_unset=True)
    if not updates:
        tenant = await db.tenants.get(ctx.tenant_id)
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        return _tenant_to_response(tenant)

    tenant = await db.tenants.update(ctx.tenant_id, updates)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return _tenant_to_response(tenant)


@router.put("/current/api-key")
async def set_tenant_api_key(
    request: TenantAPIKeyRequest,
    ctx: TenantContext = Depends(require_role("owner", "admin")),
):
    """Set or rotate the tenant's Anthropic API key."""
    key_manager = get_key_manager()

    # Encrypt the API key
    encrypted = await key_manager.encrypt_api_key(request.anthropic_api_key)

    # Invalidate cached key
    key_manager.invalidate_cache(ctx.tenant_id)

    updates = {
        "encrypted_anthropic_api_key": encrypted,
        "use_bedrock": request.use_bedrock,
    }
    if request.anthropic_base_url is not None:
        updates["anthropic_base_url"] = request.anthropic_base_url

    await db.tenants.update(ctx.tenant_id, updates)

    return {"message": "API key updated successfully"}


@router.get("/current/users", response_model=list[TenantUserResponse])
async def list_tenant_users(
    ctx: TenantContext = Depends(get_tenant_context),
):
    """List all users in the current tenant."""
    users = await db.users.list_by_tenant(ctx.tenant_id)
    return [
        {
            "id": u.get("id", ""),
            "email": u.get("email", ""),
            "name": u.get("name"),
            "role": u.get("role", "member"),
            "created_at": u.get("created_at", ""),
            "last_login": u.get("last_login"),
        }
        for u in users
    ]


@router.post("/current/users/invite")
async def invite_user(
    request: InviteUserRequest,
    ctx: TenantContext = Depends(require_role("owner", "admin")),
):
    """Invite a user to the tenant. User must already have an account."""
    # Find user by email
    all_users = await db.users.list()
    target_user = None
    for u in all_users:
        if u.get("email") == request.email:
            target_user = u
            break

    if not target_user:
        raise HTTPException(status_code=404, detail="User not found. They must register first.")

    if target_user.get("tenant_id"):
        raise HTTPException(status_code=400, detail="User already belongs to a tenant")

    # Add user to tenant
    await db.users.update(target_user["id"], {
        "tenant_id": ctx.tenant_id,
        "role": request.role,
    })

    return {"message": f"User {request.email} added to tenant with role {request.role}"}


@router.put("/current/users/{user_id}/role")
async def change_user_role(
    user_id: str,
    request: ChangeUserRoleRequest,
    ctx: TenantContext = Depends(require_role("owner", "admin")),
):
    """Change a user's role within the tenant."""
    user = await db.users.get_with_tenant(user_id, ctx.tenant_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found in tenant")

    # Cannot change owner's role (must transfer ownership instead)
    if user.get("role") == "owner":
        raise HTTPException(status_code=400, detail="Cannot change owner's role")

    # Only owners can promote to admin
    if request.role == "admin" and ctx.role != "owner" and not ctx.is_platform_admin:
        raise HTTPException(status_code=403, detail="Only owners can promote to admin")

    await db.users.update(user_id, {"role": request.role})
    return {"message": f"User role updated to {request.role}"}


@router.delete("/current/users/{user_id}")
async def remove_user(
    user_id: str,
    ctx: TenantContext = Depends(require_role("owner", "admin")),
):
    """Remove a user from the tenant."""
    if user_id == ctx.user_id:
        raise HTTPException(status_code=400, detail="Cannot remove yourself")

    user = await db.users.get_with_tenant(user_id, ctx.tenant_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found in tenant")

    if user.get("role") == "owner":
        raise HTTPException(status_code=400, detail="Cannot remove the tenant owner")

    await db.users.update(user_id, {
        "tenant_id": "",
        "role": "member",
    })
    return {"message": "User removed from tenant"}
