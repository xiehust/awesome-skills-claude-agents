"""Tenant context middleware and RBAC dependencies."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from fastapi import Depends

from database import db
from middleware.auth import get_current_user
from core.exceptions import AuthorizationException

logger = logging.getLogger(__name__)


@dataclass
class TenantContext:
    """Holds tenant and user information for the current request."""
    tenant_id: str
    user_id: str
    role: str  # owner, admin, member, viewer
    is_platform_admin: bool


async def get_tenant_context(
    user: dict = Depends(get_current_user),
) -> TenantContext:
    """Extract tenant context from the authenticated user.

    Reads tenant_id and role from the user record and verifies
    the tenant is active.

    Returns:
        TenantContext with tenant and user info

    Raises:
        AuthorizationException: If user has no tenant or tenant is inactive
    """
    tenant_id = user.get("tenant_id")
    if not tenant_id:
        raise AuthorizationException(
            message="User is not associated with any tenant",
            suggested_action="Please join or create a tenant",
        )

    user_id = user.get("id", "")
    role = user.get("role", "member")
    is_platform_admin = user.get("is_platform_admin", False)

    # Verify tenant is active (with short-circuit for platform admins)
    if not is_platform_admin:
        tenant = await db.tenants.get(tenant_id)
        if tenant is None:
            raise AuthorizationException(
                message="Tenant not found",
                suggested_action="Please contact your administrator",
            )
        if tenant.get("status") != "active":
            raise AuthorizationException(
                message="Tenant is suspended",
                suggested_action="Please contact platform support",
            )

    return TenantContext(
        tenant_id=tenant_id,
        user_id=user_id,
        role=role,
        is_platform_admin=is_platform_admin,
    )


def require_role(*roles: str):
    """Dependency factory that checks if the user has one of the required roles.

    Platform admins bypass all role checks.

    Usage:
        @router.post("/resource")
        async def create_resource(ctx: TenantContext = Depends(require_role("owner", "admin"))):
            ...
    """
    async def _check_role(
        ctx: TenantContext = Depends(get_tenant_context),
    ) -> TenantContext:
        if ctx.is_platform_admin:
            return ctx
        if ctx.role not in roles:
            raise AuthorizationException(
                message=f"Insufficient permissions. Required role: {' or '.join(roles)}",
                suggested_action="Contact your tenant administrator for access",
            )
        return ctx

    return _check_role


def require_platform_admin():
    """Dependency that requires platform admin privileges.

    Usage:
        @router.post("/admin/resource")
        async def admin_endpoint(ctx: TenantContext = Depends(require_platform_admin())):
            ...
    """
    async def _check_admin(
        ctx: TenantContext = Depends(get_tenant_context),
    ) -> TenantContext:
        if not ctx.is_platform_admin:
            raise AuthorizationException(
                message="Platform admin access required",
                suggested_action="This endpoint is restricted to platform administrators",
            )
        return ctx

    return _check_admin


def check_resource_ownership(resource: Optional[dict], ctx: TenantContext, action: str = "modify") -> bool:
    """Check if a member can modify a resource they own.

    Members can only modify resources where created_by matches their user_id.
    Owners and admins can modify any resource in their tenant.

    Returns True if allowed, raises AuthorizationException if not.
    """
    if ctx.is_platform_admin or ctx.role in ("owner", "admin"):
        return True

    if resource is None:
        return True

    resource_creator = resource.get("created_by")
    if resource_creator and resource_creator != ctx.user_id:
        raise AuthorizationException(
            message=f"Cannot {action} resource created by another user",
            suggested_action="Contact the resource owner or a tenant admin",
        )
    return True
