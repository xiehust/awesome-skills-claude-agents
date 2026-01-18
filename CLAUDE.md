# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an AI Agent Platform built with React (frontend) and FastAPI (backend) that enables users to create, manage, and chat with customizable AI agents powered by **Claude Agent SDK**. The platform integrates Skills and MCP (Model Context Protocol) servers for extended capabilities.

## Development Commands

### Quick Start (Recommended)

Use the provided scripts to start/stop both services:

```bash
# Start both backend and frontend
./start.sh

# Stop both services
./stop.sh

# View logs
tail -f logs/backend.log   # Backend logs
tail -f logs/frontend.log  # Frontend logs
```

The `start.sh` script will:
- Check and install dependencies if needed
- Create `.env` from `.env.example` if missing
- Start backend on http://localhost:8000
- Start frontend on http://localhost:5173
- Run services in background with logs in `logs/` directory

**Important**: Edit `backend/.env` and add your `ANTHROPIC_API_KEY` before first run.

### Backend (FastAPI + Claude Agent SDK)

```bash
cd backend

# Setup virtual environment with uv (recommended)
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
uv pip install fastapi uvicorn python-multipart pydantic pydantic-settings boto3 pyyaml anyio claude-agent-sdk

# Or with standard pip
pip install -r requirements.txt

# Run development server (with auto-reload)
python main.py

# Alternative: Run with uvicorn directly
uvicorn main:app --reload --port 8000
```

### Frontend (React + Vite + TypeScript)

```bash
cd frontend

# Install dependencies
npm install

# Run development server (http://localhost:5173)
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Lint code
npm run lint

# Run tests
npm run test

# Run tests once (CI mode)
npm run test:run

# Generate test coverage
npm run test:coverage
```

### Running Both Services Manually

For local development, run both services concurrently:
- Terminal 1: `cd backend && python main.py` (http://localhost:8000)
- Terminal 2: `cd frontend && npm run dev` (http://localhost:5173)

The frontend proxies `/api` requests to the backend automatically.

## Architecture Overview

### High-Level Data Flow

1. **User Input** → Frontend React app
2. **HTTP/SSE Request** → FastAPI backend (`/api/chat/stream`)
3. **Agent Manager** → Loads agent config from mock DB
4. **Claude Agent SDK** → Creates `ClaudeSDKClient` with options (tools, MCP, hooks)
5. **Claude Code CLI** → Executes via SDK with built-in tools (Bash, Read, Write, Edit, Glob, Grep, WebFetch)
6. **SSE Streaming** → Backend streams responses back to frontend
7. **UI Update** → Frontend renders streaming messages with tool calls

### Key Architectural Concepts

**Claude Agent SDK Integration**:
- The backend uses `ClaudeSDKClient` from `claude-agent-sdk` to manage Claude Code CLI processes
- Each conversation is a multi-turn session with conversation continuity
- Built-in tools (Bash, Read, Write, Edit, etc.) are provided by Claude Code CLI
- Custom tools can be added via the `@tool` decorator
- MCP servers are configured natively via `mcp_servers` option (stdio, SSE, HTTP)
- Hooks (`PreToolUse`, `PostToolUse`) enable security checks and logging

**Session Management**:
- Sessions are managed via `session_manager` (in-memory storage)
- Each session has a unique `session_id` that tracks conversation context
- Sessions can be resumed for conversation continuity

**Skills Integration**:
- Skills are enabled via Claude Code's built-in `Skill` tool
- When `enable_skills=true`, the Skill tool is added to `allowed_tools`
- Skills are stored in DynamoDB (metadata) and S3 (files), can be uploaded as ZIP or installed via plugins
- See [SKILLS_GUIDE.md](./SKILLS_GUIDE.md) for comprehensive documentation on creating and using Skills

**MCP Server Integration**:
- MCP servers are configured in the agent's `mcp_ids` array
- MCP configs are loaded from database and converted to SDK format
- Supports stdio (command-based), SSE (server-sent events), and HTTP connection types

**Plugin System**:
- Plugins are containers for skills, installed from Git repositories
- When a plugin is installed, all its skills are auto-registered to the skills table
- Plugins can be managed via UI (`/plugins` page) or slash commands (`/plugin install|list|update|remove`)
- Plugin repository structure (either `plugin.yaml` or auto-detected):
  ```
  repo/
  ├── plugin.yaml          # Optional: explicit metadata
  └── skills/              # Required: skill directories
      ├── skill-a/SKILL.md
      └── skill-b/SKILL.md
  ```
- Uninstalling a plugin removes the plugin AND all associated skills

### Backend Structure

```
backend/
├── main.py                   # FastAPI app entry point, CORS, lifespan
├── config.py                 # Settings (Pydantic Settings)
├── routers/                  # API endpoints
│   ├── agents.py            # CRUD for agents
│   ├── skills.py            # CRUD for skills, upload ZIP
│   ├── mcp.py               # CRUD for MCP server configs
│   ├── chat.py              # SSE streaming endpoint (/api/chat/stream)
│   ├── plugins.py           # Plugin management (install from Git)
│   ├── workspace.py         # Workspace file browser
│   ├── settings.py          # Settings management
│   └── auth.py              # Authentication
├── core/
│   ├── agent_manager.py     # AgentManager class, ClaudeSDKClient usage
│   ├── plugin_manager.py    # Plugin installation from Git repos
│   ├── skill_manager.py     # Skill file management and S3 sync
│   ├── workspace_manager.py # Per-agent workspace isolation
│   └── session_manager.py   # Session storage and management
├── database/
│   ├── base.py              # Abstract database interface
│   └── dynamodb.py          # DynamoDB implementation (production)
├── schemas/
│   └── *.py                 # Pydantic models for validation
├── requirements.txt         # Python dependencies
└── pyproject.toml           # Project metadata (uv)
```

**Key Backend Files**:
- `core/agent_manager.py`: Contains `AgentManager` class that wraps `ClaudeSDKClient`. This is where:
  - `ClaudeAgentOptions` are built from agent config
  - Allowed tools are configured (Bash, Read, Write, Skill, etc.)
  - MCP servers are loaded from database and configured
  - Hooks are set up for logging and security (dangerous command blocker)
  - Conversations are run via async iterators (`client.receive_response()`)

- `routers/chat.py`: SSE streaming endpoint that calls `agent_manager.run_conversation()` and yields SSE events

### Frontend Structure

```
frontend/
├── src/
│   ├── App.tsx              # Root component with React Router
│   ├── main.tsx             # Entry point (React 19 + TanStack Query)
│   ├── components/
│   │   ├── common/          # Layout, Sidebar, buttons
│   │   ├── chat/            # Chat interface components
│   │   ├── agents/          # Agent management UI
│   │   ├── skills/          # Skill management UI
│   │   └── mcp/             # MCP server management UI
│   ├── pages/               # Page-level components (ChatPage, AgentsPage, etc.)
│   ├── hooks/               # Custom React hooks (useSSE, useStreamingChat, etc.)
│   ├── services/            # API client (axios, SSE)
│   ├── types/               # TypeScript type definitions
│   └── utils/               # Utility functions
├── package.json
├── vite.config.ts
└── tailwind.config.js
```

**Key Frontend Patterns**:
- **TanStack Query** for server state management (agents, skills, MCP configs)
- **SSE (Server-Sent Events)** for streaming chat responses
- **React Router v7** for navigation
- **Tailwind CSS 4.x** for styling (dark mode: `#101622` background, `#2b6cee` primary)

### API Data Naming Convention (CRITICAL)

**Backend uses `snake_case`, Frontend uses `camelCase`.**

The backend (Python/FastAPI) uses `snake_case` for all field names, while the frontend (TypeScript/React) uses `camelCase`. Manual transformation functions handle the conversion.

**Transformation Functions Location**:
| Service | File | Function |
|---------|------|----------|
| Skills | `frontend/src/services/skills.ts` | `toCamelCase()` |
| Agents | `frontend/src/services/agents.ts` | `toCamelCase()` |
| MCP | `frontend/src/services/mcp.ts` | `toCamelCase()` |
| Plugins | `frontend/src/services/plugins.ts` | `toCamelCase()` |

**IMPORTANT: When adding new fields to a schema:**

1. Add field to backend Pydantic model (`backend/schemas/*.py`) - uses `snake_case`
2. Add field to frontend TypeScript interface (`frontend/src/types/index.ts`) - uses `camelCase`
3. **Update the corresponding `toCamelCase()` function** in `frontend/src/services/*.ts`

**Example - Adding a new field `current_version`:**

```python
# backend/schemas/skill.py
class SkillResponse(BaseModel):
    current_version: int = 0  # snake_case
```

```typescript
// frontend/src/types/index.ts
export interface Skill {
  currentVersion: number;  // camelCase
}

// frontend/src/services/skills.ts - MUST UPDATE THIS!
const toCamelCase = (data: Record<string, unknown>): Skill => {
  return {
    // ... existing fields ...
    currentVersion: (data.current_version as number) ?? 0,  // Map snake_case to camelCase
  };
};
```

**Common Bug**: Forgetting to update `toCamelCase()` results in new fields being `undefined` in the frontend, even though the API returns them correctly.

## Important Implementation Notes

### Claude Agent SDK Usage

The backend uses the official **Claude Agent SDK** (`claude-agent-sdk`). Key concepts:

1. **ClaudeSDKClient**: Main client for managing Claude Code CLI sessions
   ```python
   from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions

   options = ClaudeAgentOptions(
       system_prompt="You are a helpful assistant",
       allowed_tools=["Bash", "Read", "Write"],
       permission_mode="acceptEdits"
   )

   async with ClaudeSDKClient(options=options) as client:
       await client.query("Hello!")
       async for message in client.receive_response():
           # Process streaming messages
   ```

2. **ClaudeAgentOptions Reference**: Complete options for configuring agent behavior:
   ```python
   ClaudeAgentOptions(
       # Core Configuration
       system_prompt="...",           # System prompt for the agent
       model="claude-sonnet-4-20250514",  # Claude model to use
       permission_mode="default",     # "default", "acceptEdits", "plan", "bypassPermissions"

       # Working Directory & Settings
       cwd="/path/to/workspace",      # Working directory for Claude Code CLI
       setting_sources=['project'], # Directory to load <Working Directory>/.claude/settings.json from

       # Tools Configuration
       allowed_tools=["Bash", "Read", "Write", "Edit", "Glob", "Grep", "WebFetch", "Skill"],

       # MCP Servers (stdio, sse, http)
       mcp_servers={
           "server-name": {
               "type": "stdio",        # Connection type
               "command": "uvx",       # Command to run
               "args": ["mcp-server-name", "arg1"]
           }
       },

       # Hooks for security and logging
       hooks={
           "PreToolUse": [HookMatcher(...)],
           "PostToolUse": [HookMatcher(...)]
       }
   )
   ```

   **Key Options Explained**:
   | Option | Type | Description |
   |--------|------|-------------|
   | `system_prompt` | str | Instructions for the agent's behavior |
   | `model` | str | Claude model ID (e.g., `claude-sonnet-4-20250514`, `claude-haiku-4-5-20251001`) |
   | `permission_mode` | str | Controls tool execution permissions |
   | `cwd` | str | Working directory for file operations and bash commands |
   | `setting_sources` | str | Directory containing `.claude/settings.json` for skill/tool configs |
   | `allowed_tools` | list | List of tool names the agent can use |
   | `mcp_servers` | dict | MCP server configurations |
   | `hooks` | dict | Pre/Post tool use hooks for security and logging |

3. **Built-in Tools**: Claude Code CLI provides these out-of-the-box:
   - `Bash`, `Read`, `Write`, `Edit`, `Glob`, `Grep`, `WebFetch`, `TodoWrite`, `NotebookEdit`
   - Skills tool: `Skill` (when enabled via `enable_skills` flag)

4. **MCP Configuration**: MCP servers are configured in `mcp_servers` dict:
   ```python
   mcp_servers = {
       "postgres": {
           "type": "stdio",
           "command": "uvx",
           "args": ["mcp-server-postgres", "postgresql://..."]
       }
   }
   ```

5. **Hooks for Security**: Use hooks to intercept tool calls:
   ```python
   from claude_agent_sdk import HookMatcher

   async def dangerous_command_blocker(input_data, tool_use_id, context):
       if 'rm -rf /' in input_data.get('tool_input', {}).get('command', ''):
           return {
               'hookSpecificOutput': {
                   'permissionDecision': 'deny',
                   'permissionDecisionReason': 'Dangerous command blocked'
               }
           }
       return {}

   hooks = {
       'PreToolUse': [HookMatcher(matcher='Bash', hooks=[dangerous_command_blocker])]
   }
   ```

### Database (DynamoDB)

The backend uses AWS DynamoDB for persistent storage (`database/dynamodb.py`). Tables are auto-created on first startup via `init-aws.sh`:

- **agents**: Agent configurations (name, model, allowed_tools, skill_ids, mcp_ids)
- **skills**: Skill metadata (name, description, s3_location)
- **mcp_servers**: MCP server configs (connection_type, config dict)
- **plugins**: Plugin metadata (git_url, git_ref, skill_ids)
- **sessions**: Chat session data
- **messages**: Chat message history (with TTL auto-expiration)

### SSE Streaming Format

The chat endpoint streams JSON objects via SSE:

```json
// Text message
{"type": "assistant", "content": [{"type": "text", "text": "Response..."}], "model": "claude-sonnet-4-20250514"}

// Tool use
{"type": "assistant", "content": [{"type": "tool_use", "id": "toolu_123", "name": "Read", "input": {...}}], "model": "..."}

// Result (end of conversation turn)
{"type": "result", "session_id": "...", "duration_ms": 1234, "total_cost_usd": 0.05, "num_turns": 3}

// Error
{"type": "error", "error": "Error message"}
```

### Agent Configuration Options

When creating or updating agents, these fields control behavior:

- `model`: Claude model to use (defaults to Claude Code's default)
- `permission_mode`: `"default"`, `"acceptEdits"`, `"plan"`, `"bypassPermissions"`
- `max_turns`: Maximum conversation turns
- `allowed_tools`: List of tool names to enable (e.g., `["Bash", "Read", "Write"]`)
- `skill_ids`: Array of skill IDs to enable
- `mcp_ids`: Array of MCP server IDs to configure
- `enable_bash_tool`, `enable_file_tools`, `enable_web_tools`: Boolean flags
- `enable_tool_logging`, `enable_safety_checks`: Security flags
- `working_directory`: CWD for Claude Code CLI (defaults to `/workspace`)

### Environment Variables

Backend requires:
```env
ANTHROPIC_API_KEY=your-api-key-here  # Required for Claude Agent SDK
```

Optional Claude API Configuration:
```env
# Custom Anthropic API base URL (for proxies or custom endpoints)
ANTHROPIC_BASE_URL=https://your-proxy.example.com

# Use AWS Bedrock instead of Anthropic API
CLAUDE_CODE_USE_BEDROCK=false

# Disable experimental beta features in Claude Code
CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS=false
```

Optional Server Configuration:
```env
DEBUG=true
HOST=0.0.0.0
PORT=8000
DEFAULT_MODEL=claude-sonnet-4-5-20250929
```

These environment variables are automatically passed to Claude Code CLI when creating agent sessions.

## API Endpoints Reference

### Agents
- `GET /api/agents` - List all agents
- `GET /api/agents/{id}` - Get agent by ID
- `POST /api/agents` - Create agent
- `PUT /api/agents/{id}` - Update agent
- `DELETE /api/agents/{id}` - Delete agent

### Skills
- `GET /api/skills` - List all skills
- `POST /api/skills/upload` - Upload skill ZIP
- `POST /api/skills/generate` - AI-generate skill
- `DELETE /api/skills/{id}` - Delete skill

### MCP Servers
- `GET /api/mcp` - List MCP servers
- `POST /api/mcp` - Create MCP config
- `PUT /api/mcp/{id}` - Update MCP config
- `DELETE /api/mcp/{id}` - Delete MCP config

### Plugins
- `GET /api/plugins` - List installed plugins
- `GET /api/plugins/{id}` - Get plugin by ID
- `POST /api/plugins/install` - Install plugin from Git URL
- `POST /api/plugins/{id}/update` - Update plugin (git pull)
- `DELETE /api/plugins/{id}` - Uninstall plugin and its skills

### Chat
- `POST /api/chat/stream` - Stream chat (SSE)
  - Request: `{"agent_id": "...", "message": "...", "session_id": "...", "enable_skills": bool, "enable_mcp": bool}`
  - Response: SSE stream of JSON events

### Frontend Slash Commands

The chat interface supports slash commands (intercepted in frontend, not sent to agent):
- `/clear` - Clear conversation context
- `/compact` - Compact conversation history
- `/plugin install <git-url>` - Install plugin from Git repository
- `/plugin list` - List installed plugins
- `/plugin update <plugin-id>` - Update a plugin
- `/plugin remove <plugin-id>` - Uninstall a plugin

## Testing

Backend testing (when implemented):
```bash
cd backend
pytest
pytest tests/test_agent_manager.py -v
```

Frontend testing:
```bash
cd frontend
npm run test              # Watch mode
npm run test:run          # Run once
npm run test:coverage     # With coverage
```

## Common Patterns

### Adding a New Tool

1. Define tool function with `@tool` decorator (if custom tool needed)
2. Register in `AgentManager._build_options()` by adding to `allowed_tools`
3. Update agent config schema if needed

### Adding a New MCP Server

1. Add MCP server config to database (via `/api/mcp` endpoint)
2. Reference MCP server ID in agent's `mcp_ids` array
3. MCP server will be configured automatically in `AgentManager._build_options()`

### Debugging Agent Conversations

- Check backend logs for `[PRE-TOOL]` entries (tool usage logging)
- Enable `enable_tool_logging=true` in agent config for detailed logs
- Check for `[BLOCKED]` logs if commands are being denied by hooks
- Review SSE stream in browser DevTools Network tab

## Design System

- **Font**: Space Grotesk
- **Colors**:
  - Primary: `#2b6cee` (blue)
  - Background Dark: `#101622`
  - Card: `#1a1f2e`
  - Text: `#ffffff` (dark mode)
  - Muted: `#9da6b9`
- **Icons**: Material Symbols Outlined
- Tailwind CSS with dark mode via `dark:` prefix

## Key Dependencies

**Backend**:
- `claude-agent-sdk>=0.1.6` - Official Claude Agent SDK
- `fastapi>=0.115.0` - Web framework
- `uvicorn[standard]>=0.34.0` - ASGI server
- `pydantic>=2.10.0` - Data validation
- `boto3>=1.35.0` - AWS SDK (for production DynamoDB)

**Frontend**:
- `react@19.1.1` - UI framework
- `@tanstack/react-query@^5.90.5` - Server state management
- `react-router-dom@^7.9.5` - Routing
- `axios@^1.13.1` - HTTP client
- `tailwindcss@^4.1.16` - Styling
- `vite@^7.1.7` - Build tool
- `vitest@^4.0.15` - Testing framework

## Security Architecture

The platform implements a **defense-in-depth security model** with four layers to ensure safe, isolated agent execution. This is critical to understand when working with agents, skills, and file operations.

### Four Security Layers

```
┌─────────────────────────────────────────────────────────┐
│ Layer 4: Bash Command Protection                       │
│ └─ Parse & validate file paths in bash commands        │
├─────────────────────────────────────────────────────────┤
│ Layer 3: File Tool Access Control                      │
│ └─ Validate Read/Write/Edit/Glob/Grep operations       │
├─────────────────────────────────────────────────────────┤
│ Layer 2: Skill Access Control                          │
│ └─ PreToolUse hook validates Skill tool invocations    │
├─────────────────────────────────────────────────────────┤
│ Layer 1: Workspace Isolation                           │
│ └─ Per-agent workspace with symlinked skills           │
└─────────────────────────────────────────────────────────┘
```

### Layer 1: Workspace Isolation

**Code Location**: `backend/core/workspace_manager.py`, `agent_manager.py:326-338`

Each agent with `enable_skills=True` gets an **isolated workspace outside the project tree**:

```
Main Workspace (Skill Storage):
/home/ubuntu/.../workspace/
└── .claude/skills/           ← All available skills stored here

Isolated Agent Workspaces:
/tmp/agent-platform-workspaces/
└── {agent_id}/
    └── .claude/skills/       ← Only authorized skills symlinked here
```

**Key Implementation**:
```python
if enable_skills and agent_id:
    # Use per-agent workspace (all agents with skills get isolated workspaces)
    working_directory = str(workspace_manager.get_agent_workspace(agent_id))
else:
    # Use default workspace (no skills enabled)
    working_directory = settings.agent_workspace_dir
```

- `allow_all_skills=True`: All available skills are symlinked
- `allow_all_skills=False`: Only specified skills from `skill_ids` are symlinked

### Layer 2: Skill Access Control Hook

**Code Location**: `agent_manager.py:163-207`, `316-324`

When `allow_all_skills=False`, a PreToolUse hook blocks unauthorized Skill tool invocations:

```python
async def skill_access_checker(input_data, tool_use_id, context):
    if input_data.get('tool_name') == 'Skill':
        requested_skill = input_data.get('tool_input', {}).get('skill', '')
        if requested_skill not in allowed_skill_names:
            return {
                'hookSpecificOutput': {
                    'permissionDecision': 'deny',
                    'permissionDecisionReason': f'Skill "{requested_skill}" not authorized'
                }
            }
    return {}
```

### Layer 3: File Tool Access Control

**Code Location**: `agent_manager.py:111-157`, `340-351`

The `can_use_tool` permission handler validates file paths for:
- `Read`, `Write`, `Edit` → checks `file_path` parameter
- `Glob`, `Grep` → checks `path` parameter

```python
async def file_access_permission_handler(tool_name, input_data, context):
    # Extract and normalize file path
    normalized_path = os.path.normpath(file_path)

    # Check if path is within allowed directories
    is_allowed = any(
        normalized_path.startswith(allowed_dir + '/') or normalized_path == allowed_dir
        for allowed_dir in allowed_directories
    )

    if not is_allowed:
        return {"behavior": "deny", "message": "File access denied"}
```

**Configuration**:
```python
allowed_directories = [working_directory]  # Agent's workspace
# Optional: Add extra directories from agent config
extra_dirs = agent_config.get("allowed_directories", [])
```

### Layer 4: Bash Command Protection

**Code Location**: `agent_manager.py:159-202`

**Critical**: This layer prevents agents from bypassing file access control via bash commands.

Without this, agents could execute:
```bash
bash cat /etc/passwd
bash echo "data" > /tmp/other-agent/stolen.txt
bash rm /important/file
```

**Implementation**: Parses bash commands using regex to extract file paths:
```python
if tool_name == 'Bash':
    # Extract absolute paths from common file access commands
    suspicious_patterns = [
        r'\s+(/[^\s]+)',  # Absolute paths
        r'(?:cat|head|tail|less|more)\s+([^\s|>&]+)',  # Read commands
        r'(?:echo|printf|tee)\s+.*?>\s*([^\s|>&]+)',  # Write redirects
        r'(?:cp|mv|rm|mkdir|rmdir|touch)\s+.*?([^\s|>&]+)',  # File ops
    ]

    # Validate each extracted absolute path
    for file_path in potential_paths:
        if not file_path.startswith('/'):
            continue  # Relative paths are safe (use cwd)

        if not is_allowed:
            return {"behavior": "deny", "message": "Bash file access denied"}
```

### Agent Permissions Summary

**Agents CAN**:
- ✅ Read/write files within their workspace (`/tmp/agent-platform-workspaces/{agent_id}/`)
- ✅ Execute bash commands with relative paths (protected by `cwd`)
- ✅ Use authorized skills (based on `skill_ids` or `allow_all_skills`)

**Agents CANNOT**:
- 🚫 Access other agents' workspaces
- 🚫 Access system files (`/etc/passwd`, `/var/log/`, etc.)
- 🚫 Access main workspace where skills are stored
- 🚫 Use unauthorized skills
- 🚫 Bypass restrictions via bash commands with absolute paths

### Monitoring Security Events

Check logs for security-related events:
```bash
# File access denials
tail -f logs/backend.log | grep "FILE ACCESS DENIED"

# Bash command denials
tail -f logs/backend.log | grep "BASH FILE ACCESS DENIED"

# Skill access denials
tail -f logs/backend.log | grep "BLOCKED.*Skill"
```

**IMPORTANT**: See [SECURITY.md](./SECURITY.md) for complete security documentation including known limitations, testing procedures, and best practices.

## Production Deployment

The architecture is designed for AWS deployment:
- **Frontend**: S3 + CloudFront
- **Backend**: ECS Fargate with ALB
- **Database**: DynamoDB (replace mock DB)
- **Storage**: S3 for skill packages
- **Secrets**: AWS Secrets Manager for ANTHROPIC_API_KEY

See `ARCHITECTURE.md` for detailed deployment architecture.
