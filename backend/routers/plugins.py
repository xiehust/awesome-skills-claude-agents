"""Plugin management API endpoints."""
from fastapi import APIRouter

from schemas.plugin import (
    PluginInstallRequest,
    PluginUpdateRequest,
    PluginResponse,
    PluginListResponse,
)
from core.plugin_manager import plugin_manager

router = APIRouter()


@router.get("", response_model=PluginListResponse)
async def list_plugins():
    """List all installed plugins."""
    plugins = await plugin_manager.list_plugins()
    return PluginListResponse(plugins=plugins, total=len(plugins))


@router.get("/{plugin_id}", response_model=PluginResponse)
async def get_plugin(plugin_id: str):
    """Get a specific plugin by ID."""
    return await plugin_manager.get_plugin(plugin_id)


@router.post("/install", response_model=PluginResponse, status_code=201)
async def install_plugin(request: PluginInstallRequest):
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
    return await plugin_manager.install_from_git(
        git_url=request.git_url,
        git_ref=request.git_ref
    )


@router.post("/{plugin_id}/update", response_model=PluginResponse)
async def update_plugin(plugin_id: str, request: PluginUpdateRequest = None):
    """Update an installed plugin by pulling the latest from git.

    Optionally provide a new git_ref to switch branches/tags.
    """
    git_ref = request.git_ref if request else None
    return await plugin_manager.update_plugin(plugin_id, git_ref=git_ref)


@router.delete("/{plugin_id}", status_code=204)
async def uninstall_plugin(plugin_id: str):
    """Uninstall a plugin and all its associated skills.

    WARNING: This will permanently delete all skills that were installed
    as part of this plugin.
    """
    await plugin_manager.uninstall_plugin(plugin_id)
