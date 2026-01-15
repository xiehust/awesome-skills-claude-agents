"""Settings API endpoints for managing runtime configuration."""
import logging
from datetime import datetime
from fastapi import APIRouter
from schemas.settings import SettingsUpdateRequest, SettingsResponse
from database import db
from config import settings as env_settings

logger = logging.getLogger(__name__)
router = APIRouter()

# Global settings record ID (single record for the entire application)
SETTINGS_ID = "global"

# In-memory cache for sensitive values (cleared on restart)
# These are stored separately from the database for security
_secrets_cache: dict[str, str] = {}


@router.get("", response_model=SettingsResponse)
async def get_settings():
    """Get current runtime settings.

    Returns settings with sensitive fields masked (only showing *_set booleans).
    """
    stored = await db.settings.get(SETTINGS_ID)

    if not stored:
        # Return defaults from environment variables
        return SettingsResponse(
            anthropic_base_url=env_settings.anthropic_base_url,
            anthropic_api_key_set=bool(env_settings.anthropic_api_key),
            claude_code_use_bedrock=env_settings.claude_code_use_bedrock,
            bedrock_auth_method="credentials",  # Default
            aws_region=env_settings.aws_region,
            aws_access_key_id=env_settings.aws_access_key_id or None,
            aws_secret_access_key_set=bool(env_settings.aws_secret_access_key),
            aws_session_token_set=bool(env_settings.aws_session_token),
            aws_bearer_token_set=bool(env_settings.aws_bearer_token_bedrock),
        )

    return SettingsResponse(
        anthropic_base_url=stored.get("anthropic_base_url"),
        anthropic_api_key_set=stored.get("anthropic_api_key_set", False),
        claude_code_use_bedrock=stored.get("claude_code_use_bedrock", False),
        bedrock_auth_method=stored.get("bedrock_auth_method", "credentials"),
        aws_region=stored.get("aws_region", "us-west-2"),
        aws_access_key_id=stored.get("aws_access_key_id"),
        aws_secret_access_key_set=stored.get("aws_secret_access_key_set", False),
        aws_session_token_set=stored.get("aws_session_token_set", False),
        aws_bearer_token_set=stored.get("aws_bearer_token_set", False),
        updated_at=stored.get("updated_at"),
    )


@router.put("", response_model=SettingsResponse)
async def update_settings(request: SettingsUpdateRequest):
    """Update runtime settings.

    Sensitive fields (API keys, secrets, tokens) are cached in-memory
    and only their presence is stored in the database (*_set booleans).
    """
    updates: dict = {
        "id": SETTINGS_ID,
        "updated_at": datetime.now().isoformat(),
    }

    # Handle non-sensitive fields
    if request.anthropic_base_url is not None:
        updates["anthropic_base_url"] = request.anthropic_base_url or None
    if request.claude_code_use_bedrock is not None:
        updates["claude_code_use_bedrock"] = request.claude_code_use_bedrock
    if request.bedrock_auth_method is not None:
        updates["bedrock_auth_method"] = request.bedrock_auth_method
    if request.aws_region is not None:
        updates["aws_region"] = request.aws_region
    if request.aws_access_key_id is not None:
        updates["aws_access_key_id"] = request.aws_access_key_id or None

    # Handle sensitive fields (store indicator, cache actual value)
    if request.anthropic_api_key is not None:
        updates["anthropic_api_key_set"] = bool(request.anthropic_api_key)
        if request.anthropic_api_key:
            _secrets_cache["anthropic_api_key"] = request.anthropic_api_key
        elif "anthropic_api_key" in _secrets_cache:
            del _secrets_cache["anthropic_api_key"]

    if request.aws_secret_access_key is not None:
        updates["aws_secret_access_key_set"] = bool(request.aws_secret_access_key)
        if request.aws_secret_access_key:
            _secrets_cache["aws_secret_access_key"] = request.aws_secret_access_key
        elif "aws_secret_access_key" in _secrets_cache:
            del _secrets_cache["aws_secret_access_key"]

    if request.aws_session_token is not None:
        updates["aws_session_token_set"] = bool(request.aws_session_token)
        if request.aws_session_token:
            _secrets_cache["aws_session_token"] = request.aws_session_token
        elif "aws_session_token" in _secrets_cache:
            del _secrets_cache["aws_session_token"]

    if request.aws_bearer_token is not None:
        updates["aws_bearer_token_set"] = bool(request.aws_bearer_token)
        if request.aws_bearer_token:
            _secrets_cache["aws_bearer_token"] = request.aws_bearer_token
        elif "aws_bearer_token" in _secrets_cache:
            del _secrets_cache["aws_bearer_token"]

    # Merge with existing settings
    existing = await db.settings.get(SETTINGS_ID) or {}
    merged = {**existing, **updates}

    await db.settings.put(merged)
    logger.info("Settings updated successfully")

    return await get_settings()


# Helper functions for other modules to access runtime credentials

def get_runtime_api_key() -> str | None:
    """Get API key from cache or environment."""
    return _secrets_cache.get("anthropic_api_key") or env_settings.anthropic_api_key


def get_runtime_aws_credentials() -> dict:
    """Get AWS credentials from cache or environment.

    Returns dict with:
    - aws_access_key_id
    - aws_secret_access_key
    - aws_session_token (optional)
    """
    return {
        "aws_access_key_id": _secrets_cache.get("aws_access_key_id") or env_settings.aws_access_key_id,
        "aws_secret_access_key": _secrets_cache.get("aws_secret_access_key") or env_settings.aws_secret_access_key,
        "aws_session_token": _secrets_cache.get("aws_session_token") or env_settings.aws_session_token or None,
    }


def get_runtime_bearer_token() -> str | None:
    """Get AWS Bedrock Bearer Token from cache or environment."""
    return _secrets_cache.get("aws_bearer_token") or env_settings.aws_bearer_token_bedrock or None
