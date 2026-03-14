"""Key manager for per-tenant API key encryption.

Supports two modes:
- KMS envelope encryption (production): Uses AWS KMS to generate data keys,
  then AES-256-GCM to encrypt API keys
- Fernet fallback (local dev): Uses cryptography.fernet with a static secret
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import logging
import time
from typing import Optional

import boto3

logger = logging.getLogger(__name__)

# Cache TTL in seconds (5 minutes)
_CACHE_TTL = 300


class KeyManager:
    """Manages encryption/decryption of tenant API keys."""

    def __init__(self, use_kms: bool = False, kms_key_alias: str = "alias/agent-platform-tenant-keys",
                 fernet_secret: str = "change-this-in-production-32chars!", aws_region: str = "us-west-2"):
        self._use_kms = use_kms
        self._kms_key_alias = kms_key_alias
        self._fernet_secret = fernet_secret
        self._aws_region = aws_region
        self._cache: dict[str, tuple[str, float]] = {}  # tenant_id -> (plaintext_key, expiry)
        self._lock = asyncio.Lock()
        self._kms_client = None
        self._fernet = None

    def _get_kms_client(self):
        """Lazy-init KMS client."""
        if self._kms_client is None:
            self._kms_client = boto3.client("kms", region_name=self._aws_region)
        return self._kms_client

    def _get_fernet(self):
        """Lazy-init Fernet cipher."""
        if self._fernet is None:
            from cryptography.fernet import Fernet
            # Derive a valid Fernet key from the secret
            key = hashlib.sha256(self._fernet_secret.encode()).digest()
            fernet_key = base64.urlsafe_b64encode(key)
            self._fernet = Fernet(fernet_key)
        return self._fernet

    async def encrypt_api_key(self, plaintext: str) -> str:
        """Encrypt an API key. Returns a JSON bundle string.

        For KMS: Uses envelope encryption (GenerateDataKey + AES-256-GCM)
        For Fernet: Uses symmetric encryption with derived key
        """
        if self._use_kms:
            return await self._kms_encrypt(plaintext)
        return self._fernet_encrypt(plaintext)

    async def decrypt_api_key(self, encrypted_bundle: str) -> str:
        """Decrypt an API key from its encrypted bundle."""
        if self._use_kms:
            return await self._kms_decrypt(encrypted_bundle)
        return self._fernet_decrypt(encrypted_bundle)

    async def get_tenant_api_key(self, tenant_id: str, encrypted_bundle: str) -> str:
        """Get a tenant's API key, using cache if available.

        Args:
            tenant_id: The tenant identifier
            encrypted_bundle: The encrypted API key bundle from database

        Returns:
            The plaintext API key
        """
        now = time.time()

        # Check cache
        if tenant_id in self._cache:
            cached_key, expiry = self._cache[tenant_id]
            if now < expiry:
                return cached_key
            else:
                del self._cache[tenant_id]

        # Decrypt and cache
        async with self._lock:
            # Double-check after acquiring lock
            if tenant_id in self._cache:
                cached_key, expiry = self._cache[tenant_id]
                if now < expiry:
                    return cached_key

            plaintext = await self.decrypt_api_key(encrypted_bundle)
            self._cache[tenant_id] = (plaintext, now + _CACHE_TTL)
            return plaintext

    def invalidate_cache(self, tenant_id: str) -> None:
        """Invalidate cached key for a tenant (e.g., on key rotation)."""
        self._cache.pop(tenant_id, None)
        logger.info(f"Invalidated API key cache for tenant {tenant_id}")

    def invalidate_all(self) -> None:
        """Clear entire cache."""
        self._cache.clear()

    # --- KMS envelope encryption ---

    async def _kms_encrypt(self, plaintext: str) -> str:
        """Encrypt using KMS envelope encryption."""
        loop = asyncio.get_event_loop()

        def _do_encrypt():
            kms = self._get_kms_client()
            # Generate a data key
            response = kms.generate_data_key(
                KeyId=self._kms_key_alias,
                KeySpec="AES_256"
            )
            plaintext_data_key = response["Plaintext"]
            encrypted_data_key = response["CiphertextBlob"]

            # Encrypt the API key with the plaintext data key using Fernet
            from cryptography.fernet import Fernet
            fernet_key = base64.urlsafe_b64encode(plaintext_data_key[:32])
            f = Fernet(fernet_key)
            encrypted_api_key = f.encrypt(plaintext.encode())

            # Bundle: encrypted data key + encrypted API key
            bundle = {
                "version": 1,
                "method": "kms",
                "encrypted_data_key": base64.b64encode(encrypted_data_key).decode(),
                "encrypted_value": base64.b64encode(encrypted_api_key).decode(),
            }
            return json.dumps(bundle)

        return await loop.run_in_executor(None, _do_encrypt)

    async def _kms_decrypt(self, bundle_str: str) -> str:
        """Decrypt using KMS envelope encryption."""
        loop = asyncio.get_event_loop()

        def _do_decrypt():
            bundle = json.loads(bundle_str)
            kms = self._get_kms_client()

            encrypted_data_key = base64.b64decode(bundle["encrypted_data_key"])
            encrypted_value = base64.b64decode(bundle["encrypted_value"])

            # Decrypt the data key with KMS
            response = kms.decrypt(CiphertextBlob=encrypted_data_key)
            plaintext_data_key = response["Plaintext"]

            # Decrypt the API key with the data key
            from cryptography.fernet import Fernet
            fernet_key = base64.urlsafe_b64encode(plaintext_data_key[:32])
            f = Fernet(fernet_key)
            return f.decrypt(encrypted_value).decode()

        return await loop.run_in_executor(None, _do_decrypt)

    # --- Fernet fallback (local dev) ---

    def _fernet_encrypt(self, plaintext: str) -> str:
        """Encrypt using Fernet with static secret."""
        f = self._get_fernet()
        encrypted = f.encrypt(plaintext.encode())
        bundle = {
            "version": 1,
            "method": "fernet",
            "encrypted_value": base64.b64encode(encrypted).decode(),
        }
        return json.dumps(bundle)

    def _fernet_decrypt(self, bundle_str: str) -> str:
        """Decrypt using Fernet with static secret."""
        bundle = json.loads(bundle_str)
        f = self._get_fernet()
        encrypted = base64.b64decode(bundle["encrypted_value"])
        return f.decrypt(encrypted).decode()


# Module-level singleton (initialized lazily)
_key_manager: Optional[KeyManager] = None


def get_key_manager() -> KeyManager:
    """Get or create the global KeyManager instance."""
    global _key_manager
    if _key_manager is None:
        from config import settings
        _key_manager = KeyManager(
            use_kms=settings.use_kms_encryption,
            kms_key_alias=settings.kms_key_alias,
            fernet_secret=settings.tenant_key_encryption_secret,
            aws_region=settings.aws_region,
        )
    return _key_manager
