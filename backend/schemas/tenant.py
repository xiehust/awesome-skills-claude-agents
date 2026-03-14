"""Tenant-related Pydantic models for multi-tenancy."""
from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field, field_validator
import re


class TenantCreateRequest(BaseModel):
    """Request schema for creating a tenant."""
    name: str = Field(..., min_length=1, max_length=255, description="Tenant display name")
    slug: str = Field(..., min_length=1, max_length=63, description="URL-friendly identifier")

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        if not re.match(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$", v) and len(v) > 1:
            raise ValueError("Slug must be lowercase alphanumeric with hyphens, cannot start/end with hyphen")
        if len(v) == 1 and not v.isalnum():
            raise ValueError("Single char slug must be alphanumeric")
        return v.lower()


class TenantUpdateRequest(BaseModel):
    """Request schema for updating tenant settings."""
    name: str | None = None
    max_agents: int | None = Field(default=None, ge=1, le=1000)
    max_skills: int | None = Field(default=None, ge=1, le=1000)
    max_mcp_servers: int | None = Field(default=None, ge=1, le=100)
    rate_limit_per_minute: int | None = Field(default=None, ge=1, le=10000)


class TenantAPIKeyRequest(BaseModel):
    """Request schema for setting/rotating tenant API key."""
    anthropic_api_key: str = Field(..., min_length=1, description="Anthropic API key")
    anthropic_base_url: str | None = Field(default=None, description="Custom API base URL")
    use_bedrock: bool = Field(default=False, description="Use AWS Bedrock instead of Anthropic API")


class TenantResponse(BaseModel):
    """Response schema for tenant information."""
    id: str
    name: str
    slug: str
    owner_user_id: str
    plan: str = "free"
    max_agents: int = 10
    max_skills: int = 50
    max_mcp_servers: int = 20
    rate_limit_per_minute: int = 100
    status: str = "active"
    api_key_set: bool = False  # Never expose actual key
    use_bedrock: bool = False
    anthropic_base_url: str | None = None
    created_at: str
    updated_at: str


class TenantUserResponse(BaseModel):
    """Response schema for a user within a tenant."""
    id: str
    email: str
    name: str | None = None
    role: str  # owner, admin, member, viewer
    created_at: str
    last_login: str | None = None


class InviteUserRequest(BaseModel):
    """Request schema for inviting a user to a tenant."""
    email: str = Field(..., description="Email of user to invite")
    role: Literal["admin", "member", "viewer"] = Field(default="member", description="Role to assign")

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_regex, v):
            raise ValueError("Invalid email format")
        return v.lower()


class ChangeUserRoleRequest(BaseModel):
    """Request schema for changing a user's role."""
    role: Literal["admin", "member", "viewer"] = Field(..., description="New role")
