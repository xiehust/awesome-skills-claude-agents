"""Claude Code CLI management for desktop application."""
import asyncio
import subprocess
import shutil
import logging
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class CLIStatus:
    """Status information about Claude Code CLI."""
    installed: bool = False
    path: Optional[str] = None
    version: Optional[str] = None
    node_installed: bool = False
    node_version: Optional[str] = None
    npm_installed: bool = False
    npm_version: Optional[str] = None


@dataclass
class InstallResult:
    """Result of CLI installation."""
    success: bool
    message: str
    version: Optional[str] = None
    error: Optional[str] = None


class ClaudeCodeCLIManager:
    """Manages Claude Code CLI installation and status.

    This manager handles:
    - Checking if Claude Code CLI is installed
    - Checking Node.js/npm prerequisites
    - Installing Claude Code CLI via npm
    - Getting version information
    """

    CLI_PACKAGE = "@anthropic-ai/claude-code"
    CLI_COMMAND = "claude"

    def __init__(self):
        self._cached_status: Optional[CLIStatus] = None

    async def _run_command(
        self,
        args: list[str],
        check: bool = False
    ) -> subprocess.CompletedProcess:
        """Run a command asynchronously."""
        return await asyncio.to_thread(
            subprocess.run,
            args,
            capture_output=True,
            text=True,
            check=check
        )

    def _find_executable(self, name: str) -> Optional[str]:
        """Find an executable in PATH."""
        return shutil.which(name)

    async def check_node(self) -> tuple[bool, Optional[str]]:
        """Check if Node.js is installed and get version.

        Returns:
            Tuple of (installed, version)
        """
        node_path = self._find_executable("node")
        if not node_path:
            return False, None

        try:
            result = await self._run_command(["node", "--version"])
            if result.returncode == 0:
                version = result.stdout.strip()
                return True, version
        except Exception as e:
            logger.warning(f"Error checking Node.js version: {e}")

        return False, None

    async def check_npm(self) -> tuple[bool, Optional[str]]:
        """Check if npm is installed and get version.

        Returns:
            Tuple of (installed, version)
        """
        npm_path = self._find_executable("npm")
        if not npm_path:
            return False, None

        try:
            result = await self._run_command(["npm", "--version"])
            if result.returncode == 0:
                version = result.stdout.strip()
                return True, version
        except Exception as e:
            logger.warning(f"Error checking npm version: {e}")

        return False, None

    async def check_cli(self) -> tuple[bool, Optional[str], Optional[str]]:
        """Check if Claude Code CLI is installed.

        Returns:
            Tuple of (installed, path, version)
        """
        cli_path = self._find_executable(self.CLI_COMMAND)
        if not cli_path:
            return False, None, None

        try:
            result = await self._run_command([self.CLI_COMMAND, "--version"])
            if result.returncode == 0:
                version = result.stdout.strip()
                # Parse version from output like "claude-code v1.0.0"
                if "v" in version:
                    version = version.split("v")[-1].split()[0]
                return True, cli_path, version
        except Exception as e:
            logger.warning(f"Error checking Claude CLI version: {e}")

        return True, cli_path, None

    async def get_status(self, refresh: bool = False) -> CLIStatus:
        """Get comprehensive CLI status.

        Args:
            refresh: If True, force refresh instead of using cache

        Returns:
            CLIStatus with all information
        """
        if self._cached_status and not refresh:
            return self._cached_status

        status = CLIStatus()

        # Check Node.js
        status.node_installed, status.node_version = await self.check_node()

        # Check npm
        status.npm_installed, status.npm_version = await self.check_npm()

        # Check Claude CLI
        status.installed, status.path, status.version = await self.check_cli()

        self._cached_status = status
        return status

    async def install(self) -> InstallResult:
        """Install Claude Code CLI via npm.

        Returns:
            InstallResult with success status and details
        """
        # Check prerequisites
        status = await self.get_status(refresh=True)

        if not status.node_installed:
            return InstallResult(
                success=False,
                message="Node.js is required but not installed.",
                error="Please install Node.js from https://nodejs.org/"
            )

        if not status.npm_installed:
            return InstallResult(
                success=False,
                message="npm is required but not installed.",
                error="npm should come with Node.js. Please reinstall Node.js."
            )

        if status.installed:
            return InstallResult(
                success=True,
                message=f"Claude Code CLI is already installed (v{status.version}).",
                version=status.version
            )

        try:
            logger.info(f"Installing {self.CLI_PACKAGE}...")

            # Install globally via npm
            result = await self._run_command([
                "npm", "install", "-g", self.CLI_PACKAGE
            ])

            if result.returncode != 0:
                error_msg = result.stderr if result.stderr else "Unknown error"
                logger.error(f"npm install failed: {error_msg}")
                return InstallResult(
                    success=False,
                    message="Installation failed.",
                    error=error_msg
                )

            # Verify installation
            status = await self.get_status(refresh=True)
            if status.installed:
                logger.info(f"Successfully installed Claude Code CLI v{status.version}")
                return InstallResult(
                    success=True,
                    message=f"Successfully installed Claude Code CLI v{status.version}",
                    version=status.version
                )
            else:
                return InstallResult(
                    success=False,
                    message="Installation completed but CLI not found.",
                    error="The npm install succeeded but the claude command is not in PATH."
                )

        except Exception as e:
            logger.error(f"Installation error: {e}")
            return InstallResult(
                success=False,
                message="Installation failed due to an error.",
                error=str(e)
            )

    async def uninstall(self) -> InstallResult:
        """Uninstall Claude Code CLI.

        Returns:
            InstallResult with success status
        """
        status = await self.get_status()

        if not status.installed:
            return InstallResult(
                success=True,
                message="Claude Code CLI is not installed."
            )

        try:
            result = await self._run_command([
                "npm", "uninstall", "-g", self.CLI_PACKAGE
            ])

            if result.returncode != 0:
                error_msg = result.stderr if result.stderr else "Unknown error"
                return InstallResult(
                    success=False,
                    message="Uninstallation failed.",
                    error=error_msg
                )

            # Clear cache
            self._cached_status = None

            return InstallResult(
                success=True,
                message="Successfully uninstalled Claude Code CLI."
            )

        except Exception as e:
            return InstallResult(
                success=False,
                message="Uninstallation failed due to an error.",
                error=str(e)
            )

    async def update(self) -> InstallResult:
        """Update Claude Code CLI to latest version.

        Returns:
            InstallResult with success status
        """
        status = await self.get_status()

        if not status.npm_installed:
            return InstallResult(
                success=False,
                message="npm is required for updates.",
                error="Please install Node.js and npm first."
            )

        try:
            # Uninstall first if installed
            if status.installed:
                await self._run_command([
                    "npm", "uninstall", "-g", self.CLI_PACKAGE
                ])

            # Install latest
            result = await self._run_command([
                "npm", "install", "-g", self.CLI_PACKAGE
            ])

            if result.returncode != 0:
                error_msg = result.stderr if result.stderr else "Unknown error"
                return InstallResult(
                    success=False,
                    message="Update failed.",
                    error=error_msg
                )

            # Get new version
            new_status = await self.get_status(refresh=True)

            if new_status.installed:
                return InstallResult(
                    success=True,
                    message=f"Successfully updated to Claude Code CLI v{new_status.version}",
                    version=new_status.version
                )
            else:
                return InstallResult(
                    success=False,
                    message="Update completed but CLI not found.",
                    error="The npm install succeeded but the claude command is not in PATH."
                )

        except Exception as e:
            return InstallResult(
                success=False,
                message="Update failed due to an error.",
                error=str(e)
            )


# Global instance
cli_manager = ClaudeCodeCLIManager()
