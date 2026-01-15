"""Settings-related Pydantic models."""
from pydantic import BaseModel
from typing import Literal


class SettingsUpdateRequest(BaseModel):
    """Request model for updating settings."""

    # Anthropic API settings
    anthropic_base_url: str | None = None
    anthropic_api_key: str | None = None  # Write-only, stored securely

    # Bedrock toggle
    claude_code_use_bedrock: bool | None = None

    # Bedrock auth method: "credentials" or "bearer_token"
    bedrock_auth_method: Literal["credentials", "bearer_token"] | None = None

    # AWS Credentials auth (Option A)
    aws_region: str | None = None
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None  # Write-only
    aws_session_token: str | None = None  # Write-only, optional

    # Bearer Token auth (Option B)
    aws_bearer_token: str | None = None  # Write-only


class SettingsResponse(BaseModel):
    """Response model for settings (sensitive fields masked)."""

    # Anthropic API settings
    anthropic_base_url: str | None = None
    anthropic_api_key_set: bool = False  # Never expose actual key

    # Bedrock toggle
    claude_code_use_bedrock: bool = False

    # Bedrock auth method: "credentials" or "bearer_token"
    bedrock_auth_method: str = "credentials"

    # AWS settings (visible)
    aws_region: str = "us-west-2"
    aws_access_key_id: str | None = None  # Can show ID

    # AWS secrets (masked)
    aws_secret_access_key_set: bool = False
    aws_session_token_set: bool = False
    aws_bearer_token_set: bool = False

    # Metadata
    updated_at: str | None = None
