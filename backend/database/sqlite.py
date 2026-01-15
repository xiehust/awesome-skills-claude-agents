"""SQLite database client for local desktop storage."""
from __future__ import annotations

import aiosqlite
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, TypeVar, Generic
from uuid import uuid4

from database.base import BaseTable, BaseDatabase

T = TypeVar("T", bound=dict)


class SQLiteTable(BaseTable[T], Generic[T]):
    """SQLite table implementation of BaseTable interface."""

    def __init__(self, table_name: str, db_path: Path):
        self.table_name = table_name
        self.db_path = db_path

    async def _get_connection(self) -> aiosqlite.Connection:
        """Get an async SQLite connection."""
        conn = await aiosqlite.connect(str(self.db_path))
        conn.row_factory = aiosqlite.Row
        return conn

    def _row_to_dict(self, row: aiosqlite.Row) -> dict:
        """Convert a SQLite row to a dictionary, parsing JSON fields."""
        if row is None:
            return None
        result = dict(row)
        # Parse JSON fields (lists and nested objects)
        for key, value in result.items():
            if isinstance(value, str) and (value.startswith('[') or value.startswith('{')):
                try:
                    result[key] = json.loads(value)
                except json.JSONDecodeError:
                    pass
        return result

    def _serialize_value(self, value) -> str | int | float | None:
        """Serialize a value for SQLite storage."""
        if isinstance(value, (list, dict)):
            return json.dumps(value)
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, bool):
            return 1 if value else 0
        return value

    async def put(self, item: T) -> T:
        """Insert or update an item."""
        if "id" not in item:
            item["id"] = str(uuid4())
        if "created_at" not in item:
            item["created_at"] = datetime.now().isoformat()
        item["updated_at"] = datetime.now().isoformat()

        # Get existing item to decide insert vs update
        existing = await self.get(item["id"])

        async with await self._get_connection() as conn:
            if existing:
                # Update
                columns = [k for k in item.keys() if k != "id"]
                set_clause = ", ".join(f"{col} = ?" for col in columns)
                values = [self._serialize_value(item[col]) for col in columns]
                values.append(item["id"])

                await conn.execute(
                    f"UPDATE {self.table_name} SET {set_clause} WHERE id = ?",
                    values
                )
            else:
                # Insert
                columns = list(item.keys())
                placeholders = ", ".join("?" for _ in columns)
                values = [self._serialize_value(item[col]) for col in columns]

                await conn.execute(
                    f"INSERT INTO {self.table_name} ({', '.join(columns)}) VALUES ({placeholders})",
                    values
                )

            await conn.commit()
        return item

    async def get(self, item_id: str) -> Optional[T]:
        """Get an item by ID."""
        async with await self._get_connection() as conn:
            async with conn.execute(
                f"SELECT * FROM {self.table_name} WHERE id = ?",
                (item_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return self._row_to_dict(row) if row else None

    async def list(self, user_id: Optional[str] = None) -> list[T]:
        """List all items, optionally filtered by user_id."""
        async with await self._get_connection() as conn:
            if user_id:
                query = f"SELECT * FROM {self.table_name} WHERE user_id = ? ORDER BY created_at DESC"
                params = (user_id,)
            else:
                query = f"SELECT * FROM {self.table_name} ORDER BY created_at DESC"
                params = ()

            async with conn.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                return [self._row_to_dict(row) for row in rows]

    async def delete(self, item_id: str) -> bool:
        """Delete an item by ID."""
        async with await self._get_connection() as conn:
            cursor = await conn.execute(
                f"DELETE FROM {self.table_name} WHERE id = ?",
                (item_id,)
            )
            await conn.commit()
            return cursor.rowcount > 0

    async def update(self, item_id: str, updates: dict) -> Optional[T]:
        """Update an item."""
        if not updates:
            return await self.get(item_id)

        updates["updated_at"] = datetime.now().isoformat()

        async with await self._get_connection() as conn:
            columns = list(updates.keys())
            set_clause = ", ".join(f"{col} = ?" for col in columns)
            values = [self._serialize_value(updates[col]) for col in columns]
            values.append(item_id)

            cursor = await conn.execute(
                f"UPDATE {self.table_name} SET {set_clause} WHERE id = ?",
                values
            )
            await conn.commit()

            if cursor.rowcount == 0:
                return None

        return await self.get(item_id)


class SQLiteMessagesTable(SQLiteTable[T], Generic[T]):
    """Specialized SQLite table for messages with session_id querying support and TTL."""

    # TTL duration in seconds (7 days)
    TTL_SECONDS = 7 * 24 * 60 * 60  # 604800 seconds

    async def put(self, item: T) -> T:
        """Insert or update a message with TTL expiration (7 days)."""
        if "id" not in item:
            item["id"] = str(uuid4())
        if "created_at" not in item:
            item["created_at"] = datetime.now().isoformat()
        item["updated_at"] = datetime.now().isoformat()

        # Set TTL: expires 7 days from now (Unix epoch timestamp in seconds)
        item["expires_at"] = int(time.time()) + self.TTL_SECONDS

        return await super().put(item)

    async def list_by_session(self, session_id: str) -> list[T]:
        """List all messages for a session, ordered by timestamp."""
        async with await self._get_connection() as conn:
            async with conn.execute(
                f"SELECT * FROM {self.table_name} WHERE session_id = ? ORDER BY created_at ASC",
                (session_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [self._row_to_dict(row) for row in rows]

    async def delete_by_session(self, session_id: str) -> int:
        """Delete all messages for a session. Returns count of deleted items."""
        async with await self._get_connection() as conn:
            cursor = await conn.execute(
                f"DELETE FROM {self.table_name} WHERE session_id = ?",
                (session_id,)
            )
            await conn.commit()
            return cursor.rowcount

    async def cleanup_expired(self) -> int:
        """Delete expired messages based on TTL. Returns count of deleted items."""
        current_time = int(time.time())
        async with await self._get_connection() as conn:
            cursor = await conn.execute(
                f"DELETE FROM {self.table_name} WHERE expires_at < ?",
                (current_time,)
            )
            await conn.commit()
            return cursor.rowcount


class SQLiteSkillVersionsTable(SQLiteTable[T], Generic[T]):
    """Specialized SQLite table for skill versions with skill_id querying support."""

    async def list_by_skill(self, skill_id: str) -> list[T]:
        """List all versions for a skill, ordered by version number descending."""
        async with await self._get_connection() as conn:
            async with conn.execute(
                f"SELECT * FROM {self.table_name} WHERE skill_id = ? ORDER BY version DESC",
                (skill_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [self._row_to_dict(row) for row in rows]

    async def get_by_skill_and_version(self, skill_id: str, version: int) -> Optional[T]:
        """Get a specific version of a skill."""
        async with await self._get_connection() as conn:
            async with conn.execute(
                f"SELECT * FROM {self.table_name} WHERE skill_id = ? AND version = ?",
                (skill_id, version)
            ) as cursor:
                row = await cursor.fetchone()
                return self._row_to_dict(row) if row else None

    async def delete_by_skill(self, skill_id: str) -> int:
        """Delete all versions for a skill. Returns count of deleted items."""
        async with await self._get_connection() as conn:
            cursor = await conn.execute(
                f"DELETE FROM {self.table_name} WHERE skill_id = ?",
                (skill_id,)
            )
            await conn.commit()
            return cursor.rowcount


class SQLiteDatabase(BaseDatabase):
    """SQLite database client implementing BaseDatabase interface."""

    # SQL Schema for all tables
    SCHEMA = """
    -- Agents table
    CREATE TABLE IF NOT EXISTS agents (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT,
        model TEXT,
        permission_mode TEXT DEFAULT 'default',
        max_turns INTEGER,
        system_prompt TEXT,
        allowed_tools TEXT DEFAULT '[]',
        skill_ids TEXT DEFAULT '[]',
        allow_all_skills INTEGER DEFAULT 0,
        mcp_ids TEXT DEFAULT '[]',
        working_directory TEXT,
        enable_bash_tool INTEGER DEFAULT 1,
        enable_file_tools INTEGER DEFAULT 1,
        enable_web_tools INTEGER DEFAULT 0,
        enable_tool_logging INTEGER DEFAULT 1,
        enable_safety_checks INTEGER DEFAULT 1,
        enable_file_access_control INTEGER DEFAULT 1,
        allowed_directories TEXT DEFAULT '[]',
        sandbox TEXT DEFAULT '{}',
        status TEXT DEFAULT 'active',
        user_id TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_agents_user_id ON agents(user_id);

    -- Skills table
    CREATE TABLE IF NOT EXISTS skills (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT,
        folder_name TEXT UNIQUE,
        local_path TEXT,
        git_url TEXT,
        git_branch TEXT DEFAULT 'main',
        s3_location TEXT,
        created_by TEXT,
        version TEXT DEFAULT '1.0.0',
        is_system INTEGER DEFAULT 0,
        current_version INTEGER DEFAULT 0,
        has_draft INTEGER DEFAULT 0,
        draft_s3_location TEXT,
        user_id TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_skills_user_id ON skills(user_id);
    CREATE INDEX IF NOT EXISTS idx_skills_folder_name ON skills(folder_name);

    -- Skill versions table
    CREATE TABLE IF NOT EXISTS skill_versions (
        id TEXT PRIMARY KEY,
        skill_id TEXT NOT NULL,
        version INTEGER NOT NULL,
        s3_location TEXT,
        git_commit TEXT,
        change_summary TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (skill_id) REFERENCES skills(id) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS idx_skill_versions_skill_id ON skill_versions(skill_id);

    -- MCP servers table
    CREATE TABLE IF NOT EXISTS mcp_servers (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT,
        connection_type TEXT NOT NULL,
        config TEXT NOT NULL DEFAULT '{}',
        is_active INTEGER DEFAULT 1,
        user_id TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_mcp_servers_user_id ON mcp_servers(user_id);

    -- Sessions table
    CREATE TABLE IF NOT EXISTS sessions (
        id TEXT PRIMARY KEY,
        agent_id TEXT,
        user_id TEXT,
        title TEXT,
        status TEXT DEFAULT 'active',
        metadata TEXT DEFAULT '{}',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
    CREATE INDEX IF NOT EXISTS idx_sessions_agent_id ON sessions(agent_id);

    -- Messages table (with TTL support)
    CREATE TABLE IF NOT EXISTS messages (
        id TEXT PRIMARY KEY,
        session_id TEXT NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        metadata TEXT DEFAULT '{}',
        expires_at INTEGER,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id);
    CREATE INDEX IF NOT EXISTS idx_messages_expires_at ON messages(expires_at);

    -- Users table (for local single-user, may only have one record)
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        username TEXT UNIQUE,
        email TEXT,
        preferences TEXT DEFAULT '{}',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    """

    def __init__(self, db_path: str | Path | None = None):
        """Initialize SQLite database.

        Args:
            db_path: Path to the SQLite database file. If None, uses default location.
        """
        if db_path is None:
            # Default to user data directory
            import platform
            if platform.system() == "Darwin":
                data_dir = Path.home() / "Library" / "Application Support" / "ClaudeAgentPlatform"
            elif platform.system() == "Windows":
                data_dir = Path.home() / "AppData" / "Local" / "ClaudeAgentPlatform"
            else:
                data_dir = Path.home() / ".local" / "share" / "claude-agent-platform"
            data_dir.mkdir(parents=True, exist_ok=True)
            db_path = data_dir / "data.db"
        else:
            db_path = Path(db_path)
            db_path.parent.mkdir(parents=True, exist_ok=True)

        self.db_path = db_path
        self._initialized = False

        # Initialize tables
        self._agents = SQLiteTable[dict]("agents", self.db_path)
        self._skills = SQLiteTable[dict]("skills", self.db_path)
        self._mcp_servers = SQLiteTable[dict]("mcp_servers", self.db_path)
        self._sessions = SQLiteTable[dict]("sessions", self.db_path)
        self._messages = SQLiteMessagesTable[dict]("messages", self.db_path)
        self._users = SQLiteTable[dict]("users", self.db_path)
        self._skill_versions = SQLiteSkillVersionsTable[dict]("skill_versions", self.db_path)

    async def initialize(self) -> None:
        """Initialize database schema."""
        if self._initialized:
            return

        async with aiosqlite.connect(str(self.db_path)) as conn:
            await conn.executescript(self.SCHEMA)
            await conn.commit()

        self._initialized = True

    @property
    def agents(self) -> SQLiteTable:
        """Get the agents table."""
        return self._agents

    @property
    def skills(self) -> SQLiteTable:
        """Get the skills table."""
        return self._skills

    @property
    def mcp_servers(self) -> SQLiteTable:
        """Get the MCP servers table."""
        return self._mcp_servers

    @property
    def sessions(self) -> SQLiteTable:
        """Get the sessions table."""
        return self._sessions

    @property
    def messages(self) -> SQLiteMessagesTable:
        """Get the messages table."""
        return self._messages

    @property
    def users(self) -> SQLiteTable:
        """Get the users table."""
        return self._users

    @property
    def skill_versions(self) -> SQLiteSkillVersionsTable:
        """Get the skill versions table."""
        return self._skill_versions

    async def health_check(self) -> bool:
        """Check if the database is healthy."""
        try:
            async with aiosqlite.connect(str(self.db_path)) as conn:
                await conn.execute("SELECT 1")
            return True
        except Exception:
            return False

    async def cleanup_expired_messages(self) -> int:
        """Clean up expired messages. Returns count of deleted messages."""
        return await self._messages.cleanup_expired()
