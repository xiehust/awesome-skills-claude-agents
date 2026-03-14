"""Plugin management API endpoints."""
from fastapi import APIRouter, Depends

from schemas.plugin import (
    PluginInstallRequest,
    PluginUpdateRequest,
    PluginResponse,
    PluginListResponse,
)
from core.plugin_manager import plugin_manager
from database import db
from core.exceptions import PluginNotFoundException
from middleware.tenant import TenantContext, get_tenant_context, require_role

router = APIRouter()


@router.get("", response_model=PluginListResponse)
async def list_plugins(ctx: TenantContext = Depends(get_tenant_context)):
    """List all installed plugins for the current tenant."""
    plugins = await db.plugins.list_by_tenant(ctx.tenant_id)
    return PluginListResponse(plugins=plugins, total=len(plugins))


@router.get("/{plugin_id}", response_model=PluginResponse)
async def get_plugin(plugin_id: str, ctx: TenantContext = Depends(get_tenant_context)):
    """Get a specific plugin by ID."""
    plugin = await db.plugins.get_with_tenant(plugin_id, ctx.tenant_id)
    if not plugin:
        raise PluginNotFoundException(
            detail=f"Plugin with ID '{plugin_id}' does not exist"
        )
    return plugin


@router.post("/install", response_model=PluginResponse, status_code=201)
async def install_plugin(request: PluginInstallRequest, ctx: TenantContext = Depends(get_tenant_context)):
    """Install a plugin from a Git repository.

    The repository must contain a plugin.yaml file with the following structure:
    ```yaml
    name: my-plugin
    version: 1.0.0
    description: Description of the plugin
    author: author-name
    skills:
      - skill-a
      - skill-b
    ```

    Skills should be placed in a `skills/` directory with SKILL.md files.
    """
    result = await plugin_manager.install_from_git(
        git_url=request.git_url,
        git_ref=request.git_ref
    )
    # Add tenant ownership to the plugin record
    if result and result.get("id"):
        await db.plugins.update(result["id"], {
            "tenant_id": ctx.tenant_id,
            "created_by": ctx.user_id,
        })
        result["tenant_id"] = ctx.tenant_id
        result["created_by"] = ctx.user_id
    return result


@router.post("/{plugin_id}/update", response_model=PluginResponse)
async def update_plugin(plugin_id: str, request: PluginUpdateRequest = None, ctx: TenantContext = Depends(get_tenant_context)):
    """Update an installed plugin by pulling the latest from git.

    Optionally provide a new git_ref to switch branches/tags.
    """
    # Verify plugin belongs to tenant
    plugin = await db.plugins.get_with_tenant(plugin_id, ctx.tenant_id)
    if not plugin:
        raise PluginNotFoundException(
            detail=f"Plugin with ID '{plugin_id}' does not exist"
        )
    git_ref = request.git_ref if request else None
    return await plugin_manager.update_plugin(plugin_id, git_ref=git_ref)


@router.delete("/{plugin_id}", status_code=204)
async def uninstall_plugin(plugin_id: str, ctx: TenantContext = Depends(get_tenant_context)):
    """Uninstall a plugin and all its associated skills.

    WARNING: This will permanently delete all skills that were installed
    as part of this plugin.
    """
    # Verify plugin belongs to tenant
    plugin = await db.plugins.get_with_tenant(plugin_id, ctx.tenant_id)
    if not plugin:
        raise PluginNotFoundException(
            detail=f"Plugin with ID '{plugin_id}' does not exist"
        )
    await plugin_manager.uninstall_plugin(plugin_id)
