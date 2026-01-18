"""Plugin schemas for request/response validation."""

from pydantic import BaseModel, Field
from typing import Literal


class PluginInstallRequest(BaseModel):
    """Request schema for installing a plugin from git."""

    git_url: str = Field(..., min_length=1, description="Git repository URL")
    git_ref: str = Field(default="main", description="Git branch, tag, or commit")


class PluginUpdateRequest(BaseModel):
    """Request schema for updating a plugin."""

    git_ref: str | None = Field(default=None, description="New git ref to checkout")


class PluginResponse(BaseModel):
    """Response schema for plugin data."""

    id: str
    name: str
    description: str
    git_url: str
    git_ref: str
    version: str
    author: str
    created_at: str
    updated_at: str
    skill_ids: list[str] = Field(default_factory=list)
    status: Literal["installed", "updating", "error"]
    error_message: str | None = None
    marketplace: str | None = Field(default=None, description="Marketplace name if from a marketplace repo")


class PluginListResponse(BaseModel):
    """Response schema for listing plugins."""

    plugins: list[PluginResponse]
    total: int
