"""Agent workspace management for skill isolation.

This module manages per-agent workspaces with symlinks to allowed skills,
enabling fine-grained control over which skills each agent can access.

IMPORTANT: Agent workspaces are created OUTSIDE the project tree to prevent
Claude's Skill tool from discovering unauthorized skills in parent directories.

Directory structure:
    /home/ubuntu/.../workspace/          <- Project workspace (main skill storage)
    └── .claude/skills/                  <- All available skills
        ├── skill-1/
        ├── skill-2/
        └── skill-3/

    /tmp/agent-platform-workspaces/      <- Isolated agent workspaces (outside project!)
    └── {agent_id}/
        └── .claude/skills/              <- Absolute symlinks to allowed skills only
            ├── skill-1 -> /home/ubuntu/.../workspace/.claude/skills/skill-1
            └── skill-2 -> /home/ubuntu/.../workspace/.claude/skills/skill-2
"""
import logging
import shutil
from pathlib import Path
from typing import Optional

from config import settings
from database import db

logger = logging.getLogger(__name__)


class WorkspaceManager:
    """Manages per-agent workspaces with skill isolation via symlinks."""

    def __init__(self):
        self.main_workspace = Path(settings.agent_workspace_dir)
        self.agents_workspace = Path(settings.agent_workspaces_dir)
        self.main_skills_dir = self.main_workspace / ".claude" / "skills"

    def _ensure_dirs(self):
        """Ensure required directories exist."""
        self.main_skills_dir.mkdir(parents=True, exist_ok=True)
        self.agents_workspace.mkdir(parents=True, exist_ok=True)

    def get_agent_workspace(self, agent_id: str) -> Path:
        """Get the workspace path for a specific agent."""
        return self.agents_workspace / agent_id

    def get_agent_skills_dir(self, agent_id: str) -> Path:
        """Get the skills directory path for a specific agent."""
        return self.get_agent_workspace(agent_id) / ".claude" / "skills"

    async def get_skill_name_by_id(self, skill_id: str) -> Optional[str]:
        """Get skill folder name from skill ID.

        The skill folder name is extracted from s3_location or derived from skill name.
        """
        skill = await db.skills.get(skill_id)
        if not skill:
            logger.warning(f"Skill not found: {skill_id}")
            return None

        # Extract folder name from s3_location or draft_s3_location
        s3_location = skill.get("s3_location") or skill.get("draft_s3_location", "")
        if s3_location:
            # Extract from s3://bucket/skills/name/... format
            import re
            match = re.search(r'/skills/([^/]+)/', s3_location)
            if match:
                return match.group(1)

        # Fallback: sanitize skill name
        import re
        return re.sub(r'[^a-zA-Z0-9_-]', '-', skill.get("name", "").lower())

    async def get_all_skill_names(self) -> list[str]:
        """Get all available skill folder names."""
        skill_names = []
        if self.main_skills_dir.exists():
            for item in self.main_skills_dir.iterdir():
                if item.is_dir() and not item.name.startswith('.'):
                    skill_md = item / "SKILL.md"
                    if skill_md.exists():
                        skill_names.append(item.name)
        return skill_names

    async def rebuild_agent_workspace(
        self,
        agent_id: str,
        skill_ids: list[str],
        allow_all_skills: bool = False
    ) -> Path:
        """Rebuild an agent's workspace with symlinks to allowed skills.

        Args:
            agent_id: The agent's ID
            skill_ids: List of skill IDs the agent is allowed to access
            allow_all_skills: If True, symlink all available skills

        Returns:
            Path to the agent's workspace directory
        """
        self._ensure_dirs()

        agent_workspace = self.get_agent_workspace(agent_id)
        agent_skills_dir = self.get_agent_skills_dir(agent_id)

        # Remove existing skills directory and recreate
        if agent_skills_dir.exists():
            shutil.rmtree(agent_skills_dir)
        agent_skills_dir.mkdir(parents=True, exist_ok=True)

        # Determine which skills to link
        if allow_all_skills:
            # Link all available skills
            skill_names = await self.get_all_skill_names()
            logger.info(f"Agent {agent_id}: linking ALL skills ({len(skill_names)} skills)")
        else:
            # Link only specified skills
            skill_names = []
            for skill_id in skill_ids:
                skill_name = await self.get_skill_name_by_id(skill_id)
                if skill_name:
                    skill_names.append(skill_name)
                else:
                    logger.warning(f"Could not resolve skill ID to name: {skill_id}")
            logger.info(f"Agent {agent_id}: linking {len(skill_names)} skills: {skill_names}")

        # Create symlinks using ABSOLUTE paths
        # This is critical for isolated workspaces outside the project tree
        linked_count = 0
        for skill_name in skill_names:
            source_path = self.main_skills_dir / skill_name
            if source_path.exists():
                target_path = agent_skills_dir / skill_name
                # Use absolute path for symlink (required for isolated workspaces)
                absolute_source = source_path.resolve()
                try:
                    target_path.symlink_to(absolute_source)
                    linked_count += 1
                    logger.debug(f"Created symlink: {target_path} -> {absolute_source}")
                except OSError as e:
                    logger.error(f"Failed to create symlink for {skill_name}: {e}")
            else:
                logger.warning(f"Skill directory not found: {source_path}")

        logger.info(f"Agent {agent_id} workspace rebuilt: {linked_count} skills linked")
        return agent_workspace

    async def delete_agent_workspace(self, agent_id: str):
        """Delete an agent's workspace directory."""
        agent_workspace = self.get_agent_workspace(agent_id)
        if agent_workspace.exists():
            shutil.rmtree(agent_workspace)
            logger.info(f"Deleted workspace for agent {agent_id}")
        else:
            logger.debug(f"No workspace to delete for agent {agent_id}")

    async def get_allowed_skill_names(
        self,
        skill_ids: list[str],
        allow_all_skills: bool = False
    ) -> list[str]:
        """Get list of allowed skill names for permission checking.

        Args:
            skill_ids: List of skill IDs
            allow_all_skills: If True, return all available skill names

        Returns:
            List of skill folder names that are allowed
        """
        if allow_all_skills:
            return await self.get_all_skill_names()

        skill_names = []
        for skill_id in skill_ids:
            skill_name = await self.get_skill_name_by_id(skill_id)
            if skill_name:
                skill_names.append(skill_name)
        return skill_names

    def workspace_exists(self, agent_id: str) -> bool:
        """Check if an agent's workspace exists."""
        return self.get_agent_workspace(agent_id).exists()


# Global instance
workspace_manager = WorkspaceManager()
