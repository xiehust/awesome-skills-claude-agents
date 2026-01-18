"""Plugin management for installing plugins from Git repositories."""
import asyncio
import shutil
import tempfile
import logging
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

import json
import yaml

from config import settings
from database import db
from core.skill_manager import SkillManager
from core.exceptions import PluginNotFoundException, ValidationException

logger = logging.getLogger(__name__)


@dataclass
class PluginMetadata:
    """Metadata extracted from plugin.yaml."""
    name: str
    version: str
    description: str
    author: str
    skills: list[str]
    marketplace: str | None = None  # Marketplace name if from a marketplace repo


class PluginManager:
    """Manages plugin installation from Git repositories.

    Plugin repository structure:
    - plugin.yaml: Required metadata file
    - skills/: Directory containing skill subdirectories
      - skill-a/SKILL.md, ...
      - skill-b/SKILL.md, ...
    """

    def __init__(self):
        self.skill_manager = SkillManager()

    async def install_from_git(self, git_url: str, git_ref: str = "main") -> dict:
        """Install a plugin from a Git repository.

        Args:
            git_url: Git repository URL (https:// or git@)
            git_ref: Branch, tag, or commit to checkout

        Returns:
            Plugin record dict

        Raises:
            ValidationException: If plugin structure is invalid
        """
        temp_dir = None
        try:
            # Clone to temp directory
            temp_dir = Path(tempfile.mkdtemp(prefix="plugin_"))
            clone_dir = temp_dir / "repo"

            logger.info(f"Cloning {git_url} (ref: {git_ref}) to {clone_dir}")

            # Clone the repository
            process = await asyncio.create_subprocess_exec(
                "git", "clone", "--depth", "1", "--branch", git_ref,
                git_url, str(clone_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown git error"
                raise ValidationException(
                    message="Failed to clone repository",
                    detail=error_msg
                )

            # Parse plugin.yaml or auto-detect
            metadata = self._parse_plugin_yaml(clone_dir, git_url)

            # Check if plugin already exists
            existing = await self._find_plugin_by_git_url(git_url)
            if existing:
                raise ValidationException(
                    message="Plugin already installed",
                    detail=f"Plugin from {git_url} is already installed with ID: {existing['id']}"
                )

            # Install skills from plugin
            skill_ids = await self._install_skills(clone_dir, metadata)

            # Create plugin record
            plugin_data = {
                "name": metadata.name,
                "description": metadata.description,
                "git_url": git_url,
                "git_ref": git_ref,
                "version": metadata.version,
                "author": metadata.author,
                "skill_ids": skill_ids,
                "status": "installed",
                "error_message": None,
                "marketplace": metadata.marketplace,
            }

            plugin = await db.plugins.put(plugin_data)
            marketplace_info = f" (marketplace: {metadata.marketplace})" if metadata.marketplace else ""
            logger.info(f"Installed plugin: {metadata.name} with {len(skill_ids)} skills{marketplace_info}")
            return plugin

        except ValidationException:
            raise
        except Exception as e:
            logger.error(f"Error installing plugin from {git_url}: {e}")
            raise ValidationException(
                message="Plugin installation failed",
                detail=str(e)
            )
        finally:
            # Cleanup temp directory
            if temp_dir and temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)

    async def update_plugin(self, plugin_id: str, git_ref: Optional[str] = None) -> dict:
        """Update an installed plugin by pulling latest from git.

        Args:
            plugin_id: ID of the plugin to update
            git_ref: Optional new git ref to checkout

        Returns:
            Updated plugin record
        """
        plugin = await db.plugins.get(plugin_id)
        if not plugin:
            raise PluginNotFoundException(
                detail=f"Plugin with ID '{plugin_id}' does not exist"
            )

        # Update status to updating
        await db.plugins.update(plugin_id, {"status": "updating"})

        temp_dir = None
        try:
            git_url = plugin["git_url"]
            ref = git_ref or plugin["git_ref"]

            # Clone fresh copy
            temp_dir = Path(tempfile.mkdtemp(prefix="plugin_update_"))
            clone_dir = temp_dir / "repo"

            process = await asyncio.create_subprocess_exec(
                "git", "clone", "--depth", "1", "--branch", ref,
                git_url, str(clone_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown git error"
                await db.plugins.update(plugin_id, {
                    "status": "error",
                    "error_message": error_msg
                })
                raise ValidationException(
                    message="Failed to update plugin",
                    detail=error_msg
                )

            # Parse plugin.yaml or auto-detect
            metadata = self._parse_plugin_yaml(clone_dir, git_url)

            # Remove old skills
            await self._remove_skills(plugin.get("skill_ids", []))

            # Install new skills
            skill_ids = await self._install_skills(clone_dir, metadata)

            # Update plugin record
            updates = {
                "version": metadata.version,
                "description": metadata.description,
                "author": metadata.author,
                "git_ref": ref,
                "skill_ids": skill_ids,
                "status": "installed",
                "error_message": None,
            }
            updated_plugin = await db.plugins.update(plugin_id, updates)
            logger.info(f"Updated plugin: {metadata.name}")
            return updated_plugin

        except ValidationException:
            raise
        except Exception as e:
            logger.error(f"Error updating plugin {plugin_id}: {e}")
            await db.plugins.update(plugin_id, {
                "status": "error",
                "error_message": str(e)
            })
            raise
        finally:
            if temp_dir and temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)

    async def uninstall_plugin(self, plugin_id: str) -> bool:
        """Uninstall a plugin and all its associated skills.

        Args:
            plugin_id: ID of the plugin to uninstall

        Returns:
            True if successfully uninstalled
        """
        plugin = await db.plugins.get(plugin_id)
        if not plugin:
            raise PluginNotFoundException(
                detail=f"Plugin with ID '{plugin_id}' does not exist"
            )

        # Remove associated skills
        skill_ids = plugin.get("skill_ids", [])
        await self._remove_skills(skill_ids)

        # Delete plugin record
        await db.plugins.delete(plugin_id)
        logger.info(f"Uninstalled plugin: {plugin['name']} with {len(skill_ids)} skills")
        return True

    async def list_plugins(self) -> list[dict]:
        """List all installed plugins."""
        return await db.plugins.list()

    async def get_plugin(self, plugin_id: str) -> dict:
        """Get a plugin by ID."""
        plugin = await db.plugins.get(plugin_id)
        if not plugin:
            raise PluginNotFoundException(
                detail=f"Plugin with ID '{plugin_id}' does not exist"
            )
        return plugin

    def _detect_marketplace(self, repo_dir: Path) -> str | None:
        """Detect if repository is a marketplace by checking .claude-plugin/marketplace.json.

        Args:
            repo_dir: Path to cloned repository

        Returns:
            Marketplace name if found, None otherwise
        """
        marketplace_json = repo_dir / ".claude-plugin" / "marketplace.json"
        if marketplace_json.exists():
            try:
                with open(marketplace_json, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                marketplace_name = data.get("name")
                if marketplace_name:
                    logger.info(f"Detected marketplace: {marketplace_name}")
                    return marketplace_name
            except (json.JSONDecodeError, Exception) as e:
                logger.warning(f"Failed to parse marketplace.json: {e}")
        return None

    def _parse_plugin_yaml(self, repo_dir: Path, git_url: str = "") -> PluginMetadata:
        """Parse plugin.yaml from repository directory, or auto-detect skills.

        Args:
            repo_dir: Path to cloned repository
            git_url: Git URL (used to extract repo name if plugin.yaml is missing)

        Returns:
            PluginMetadata object

        Raises:
            ValidationException: If no valid plugin structure found
        """
        # First check if this is a marketplace
        marketplace = self._detect_marketplace(repo_dir)

        plugin_yaml = repo_dir / "plugin.yaml"

        # If plugin.yaml exists, use it
        if plugin_yaml.exists():
            try:
                with open(plugin_yaml, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
            except yaml.YAMLError as e:
                raise ValidationException(
                    message="Invalid plugin.yaml",
                    detail=f"YAML parse error: {e}"
                )

            # Validate required fields
            required_fields = ["name", "version", "description"]
            missing = [f for f in required_fields if f not in data]
            if missing:
                raise ValidationException(
                    message="Invalid plugin.yaml",
                    detail=f"Missing required fields: {', '.join(missing)}"
                )

            return PluginMetadata(
                name=data["name"],
                version=data["version"],
                description=data["description"],
                author=data.get("author", "unknown"),
                skills=data.get("skills", []),
                marketplace=marketplace
            )

        # No plugin.yaml - try to auto-detect skills
        skills_dir = repo_dir / "skills"
        if not skills_dir.exists() or not skills_dir.is_dir():
            raise ValidationException(
                message="Invalid plugin structure",
                detail="Repository must have either plugin.yaml or a skills/ directory"
            )

        # Auto-detect skills
        detected_skills = []
        for item in skills_dir.iterdir():
            if item.is_dir() and (item / "SKILL.md").exists():
                detected_skills.append(item.name)

        if not detected_skills:
            raise ValidationException(
                message="Invalid plugin structure",
                detail="No valid skills found in skills/ directory (each skill needs SKILL.md)"
            )

        # Extract repo name from git URL
        repo_name = self._extract_repo_name(git_url)

        # Try to read description from README.md
        description = f"Plugin with {len(detected_skills)} skill(s)"
        readme_path = repo_dir / "README.md"
        if readme_path.exists():
            try:
                with open(readme_path, 'r', encoding='utf-8') as f:
                    # Get first non-empty, non-heading line as description
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            description = line[:200]  # Limit description length
                            break
            except Exception:
                pass

        marketplace_info = f" from marketplace '{marketplace}'" if marketplace else ""
        logger.info(f"Auto-detected plugin '{repo_name}' with {len(detected_skills)} skills{marketplace_info}")

        return PluginMetadata(
            name=repo_name,
            version="1.0.0",
            description=description,
            author="unknown",
            skills=detected_skills,
            marketplace=marketplace
        )

    def _extract_repo_name(self, git_url: str) -> str:
        """Extract repository name from git URL."""
        import re
        # Handle various git URL formats:
        # https://github.com/org/repo.git
        # https://github.com/org/repo
        # git@github.com:org/repo.git
        match = re.search(r'[/:]([^/:]+)/([^/]+?)(?:\.git)?$', git_url)
        if match:
            return match.group(2)
        return "unknown-plugin"

    async def _install_skills(self, repo_dir: Path, metadata: PluginMetadata) -> list[str]:
        """Install skills from a plugin repository.

        Args:
            repo_dir: Path to cloned repository
            metadata: Plugin metadata

        Returns:
            List of installed skill IDs
        """
        skills_dir = repo_dir / "skills"
        if not skills_dir.exists():
            logger.warning(f"Plugin {metadata.name} has no skills directory")
            return []

        skill_ids = []
        skills_to_install = metadata.skills if metadata.skills else [
            d.name for d in skills_dir.iterdir() if d.is_dir()
        ]

        for skill_name in skills_to_install:
            skill_path = skills_dir / skill_name
            if not skill_path.exists():
                logger.warning(f"Skill {skill_name} not found in {skills_dir}")
                continue

            skill_md = skill_path / "SKILL.md"
            if not skill_md.exists():
                logger.warning(f"Skill {skill_name} missing SKILL.md, skipping")
                continue

            try:
                # Extract skill metadata
                skill_metadata = self.skill_manager.extract_skill_metadata(skill_path)

                # Upload to S3 as draft
                s3_location = await self.skill_manager.upload_to_draft(
                    skill_name,
                    skill_path
                )

                # Create skill record in DB
                skill_data = {
                    "name": skill_metadata.name,
                    "description": skill_metadata.description,
                    "version": skill_metadata.version,
                    "author": skill_metadata.author,
                    "s3_location": s3_location,
                    "created_by": f"plugin:{metadata.name}",
                    "is_system": False,
                    "current_version": 1,
                    "has_draft": False,
                    "draft_s3_location": None,
                    "plugin_id": None,  # Will be set after plugin is created
                }

                skill = await db.skills.put(skill_data)
                skill_ids.append(skill["id"])
                logger.info(f"Installed skill: {skill_name} (ID: {skill['id']})")

            except Exception as e:
                logger.error(f"Failed to install skill {skill_name}: {e}")
                continue

        return skill_ids

    async def _remove_skills(self, skill_ids: list[str]) -> int:
        """Remove skills by their IDs.

        Args:
            skill_ids: List of skill IDs to remove

        Returns:
            Number of skills removed
        """
        removed = 0
        for skill_id in skill_ids:
            try:
                skill = await db.skills.get(skill_id)
                if skill:
                    # Delete from S3
                    if skill.get("s3_location"):
                        try:
                            await self.skill_manager.delete_skill_files(skill["name"])
                        except Exception as e:
                            logger.warning(f"Failed to delete S3 files for skill {skill_id}: {e}")

                    # Delete from DB
                    await db.skills.delete(skill_id)
                    removed += 1
                    logger.info(f"Removed skill: {skill_id}")
            except Exception as e:
                logger.error(f"Failed to remove skill {skill_id}: {e}")
                continue
        return removed

    async def _find_plugin_by_git_url(self, git_url: str) -> Optional[dict]:
        """Find an existing plugin by its git URL."""
        plugins = await db.plugins.list()
        for plugin in plugins:
            if plugin.get("git_url") == git_url:
                return plugin
        return None


# Singleton instance
plugin_manager = PluginManager()
