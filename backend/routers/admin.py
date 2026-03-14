"""Platform admin API endpoints."""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from database import db
from middleware.tenant import TenantContext, require_platform_admin
from schemas.tenant import TenantResponse

router = APIRouter(prefix="/admin", tags=["admin"])


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


# --- Request models ---

class TenantStatusRequest(BaseModel):
    status: Literal["active", "suspended"]


class SystemSkillRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str


class SystemMCPRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str
    connection_type: Literal["stdio", "sse", "http"]
    config: dict[str, Any]


# --- Endpoints ---

@router.get("/tenants", response_model=list[TenantResponse])
async def list_all_tenants(
    ctx: TenantContext = Depends(require_platform_admin()),
):
    """List all tenants. Platform admin only."""
    tenants = await db.tenants.list()
    return [_tenant_to_response(t) for t in tenants]


@router.put("/tenants/{tenant_id}/status")
async def update_tenant_status(
    tenant_id: str,
    request: TenantStatusRequest,
    ctx: TenantContext = Depends(require_platform_admin()),
):
    """Suspend or activate a tenant. Platform admin only."""
    tenant = await db.tenants.get(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    await db.tenants.update(tenant_id, {"status": request.status})
    return {"message": f"Tenant {tenant_id} status updated to {request.status}"}


@router.post("/skills")
async def create_system_skill(
    request: SystemSkillRequest,
    ctx: TenantContext = Depends(require_platform_admin()),
):
    """Create a system skill visible to all tenants. Platform admin only."""
    skill_data = {
        "id": str(uuid4()),
        "name": request.name,
        "description": request.description,
        "tenant_id": "__SYSTEM__",
        "is_system": True,
        "created_by": ctx.user_id,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    await db.skills.put(skill_data)
    return skill_data


@router.post("/mcp")
async def create_system_mcp(
    request: SystemMCPRequest,
    ctx: TenantContext = Depends(require_platform_admin()),
):
    """Create a system MCP server visible to all tenants. Platform admin only."""
    mcp_data = {
        "id": str(uuid4()),
        "name": request.name,
        "description": request.description,
        "connection_type": request.connection_type,
        "config": request.config,
        "tenant_id": "__SYSTEM__",
        "created_by": ctx.user_id,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    await db.mcp_servers.put(mcp_data)
    return mcp_data
