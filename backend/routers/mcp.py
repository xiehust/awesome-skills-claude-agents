"""MCP Server CRUD API endpoints."""
import asyncio
from fastapi import APIRouter, Depends
from schemas.mcp import MCPCreateRequest, MCPUpdateRequest, MCPResponse
from database import db
from core.exceptions import (
    MCPServerNotFoundException,
    ValidationException,
)
from middleware.tenant import TenantContext, get_tenant_context, require_role

router = APIRouter()


@router.get("", response_model=list[MCPResponse])
async def list_mcp_servers(ctx: TenantContext = Depends(get_tenant_context)):
    """List all MCP servers (tenant + system)."""
    tenant_servers, system_servers = await asyncio.gather(
        db.mcp_servers.list_by_tenant(ctx.tenant_id),
        db.mcp_servers.list_by_tenant("__SYSTEM__"),
    )
    return tenant_servers + system_servers


@router.get("/{mcp_id}", response_model=MCPResponse)
async def get_mcp_server(mcp_id: str, ctx: TenantContext = Depends(get_tenant_context)):
    """Get a specific MCP server by ID."""
    # Try tenant-owned first, then fall back to system
    server = await db.mcp_servers.get_with_tenant(mcp_id, ctx.tenant_id)
    if not server:
        server = await db.mcp_servers.get_with_tenant(mcp_id, "__SYSTEM__")
    if not server:
        raise MCPServerNotFoundException(
            detail=f"MCP server with ID '{mcp_id}' does not exist",
            suggested_action="Please check the MCP server ID and try again"
        )
    return server


@router.post("", response_model=MCPResponse, status_code=201)
async def create_mcp_server(request: MCPCreateRequest, ctx: TenantContext = Depends(get_tenant_context)):
    """Create a new MCP server configuration."""
    # Validate config based on connection type
    if request.connection_type == "stdio":
        if not request.config.get("command"):
            raise ValidationException(
                message="Invalid MCP server configuration",
                detail="stdio connection type requires 'command' in config",
                fields=[{"field": "config.command", "error": "This field is required for stdio connection"}]
            )
    elif request.connection_type in ("sse", "http"):
        if not request.config.get("url"):
            raise ValidationException(
                message="Invalid MCP server configuration",
                detail=f"{request.connection_type} connection type requires 'url' in config",
                fields=[{"field": "config.url", "error": f"This field is required for {request.connection_type} connection"}]
            )

    # Generate endpoint based on connection type
    endpoint = ""
    if request.connection_type == "stdio":
        command = request.config.get("command", "")
        args = request.config.get("args", [])
        endpoint = f"{command} {' '.join(args)}"
    else:
        url = request.config.get("url", "")
        endpoint = url.replace("http://", "").replace("https://", "")

    server_data = {
        "name": request.name,
        "description": request.description,
        "connection_type": request.connection_type,
        "config": request.config,
        "allowed_tools": request.allowed_tools,
        "rejected_tools": request.rejected_tools,
        "endpoint": endpoint,
        "version": "v1.0.0",
        "tenant_id": ctx.tenant_id,
        "created_by": ctx.user_id,
    }
    server = await db.mcp_servers.put(server_data)
    return server


@router.put("/{mcp_id}", response_model=MCPResponse)
async def update_mcp_server(mcp_id: str, request: MCPUpdateRequest, ctx: TenantContext = Depends(get_tenant_context)):
    """Update an existing MCP server configuration."""
    existing = await db.mcp_servers.get_with_tenant(mcp_id, ctx.tenant_id)
    if not existing:
        raise MCPServerNotFoundException(
            detail=f"MCP server with ID '{mcp_id}' does not exist",
            suggested_action="Please check the MCP server ID and try again"
        )

    updates = request.model_dump(exclude_unset=True)

    # Validate config if being updated
    if "config" in updates:
        connection_type = updates.get("connection_type") or existing.get("connection_type")
        if connection_type == "stdio":
            if "command" in updates["config"] and not updates["config"]["command"]:
                raise ValidationException(
                    message="Invalid MCP server configuration",
                    detail="stdio connection type requires 'command' in config",
                    fields=[{"field": "config.command", "error": "This field cannot be empty for stdio connection"}]
                )
        elif connection_type in ("sse", "http"):
            if "url" in updates["config"] and not updates["config"]["url"]:
                raise ValidationException(
                    message="Invalid MCP server configuration",
                    detail=f"{connection_type} connection type requires 'url' in config",
                    fields=[{"field": "config.url", "error": f"This field cannot be empty for {connection_type} connection"}]
                )

    # Update endpoint if config changed
    if "config" in updates:
        connection_type = updates.get("connection_type") or existing.get("connection_type")
        if connection_type == "stdio":
            command = updates["config"].get("command", "")
            args = updates["config"].get("args", [])
            updates["endpoint"] = f"{command} {' '.join(args)}"
        else:
            url = updates["config"].get("url", "")
            updates["endpoint"] = url.replace("http://", "").replace("https://", "")

    server = await db.mcp_servers.update(mcp_id, updates)
    return server


@router.delete("/{mcp_id}", status_code=204)
async def delete_mcp_server(mcp_id: str, ctx: TenantContext = Depends(get_tenant_context)):
    """Delete an MCP server configuration."""
    # Verify server belongs to tenant before deleting
    existing = await db.mcp_servers.get_with_tenant(mcp_id, ctx.tenant_id)
    if not existing:
        raise MCPServerNotFoundException(
            detail=f"MCP server with ID '{mcp_id}' does not exist",
            suggested_action="Please check the MCP server ID and try again"
        )
    deleted = await db.mcp_servers.delete(mcp_id)
    if not deleted:
        raise MCPServerNotFoundException(
            detail=f"MCP server with ID '{mcp_id}' does not exist",
            suggested_action="Please check the MCP server ID and try again"
        )
