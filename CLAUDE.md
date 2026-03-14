# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project Overview

Multi-tenant AI Agent Platform — React frontend + FastAPI backend, powered by **Claude Agent SDK**. Users belong to tenants (organizations), each with isolated resources, API keys, and RBAC.

## Quick Commands

```bash
./start.sh          # Start both services
./stop.sh           # Stop both services
cd backend && python main.py      # Backend only (http://localhost:8000)
cd frontend && npm run dev        # Frontend only (http://localhost:5173)
cd frontend && npm run test:run   # Frontend tests (CI mode)
```

## Architecture

### Data Flow
User → React (AuthContext + JWT) → FastAPI (TenantContext middleware) → AgentManager → ClaudeSDKClient → Claude Code CLI → Anthropic API

### Multi-Tenancy Model
- **Tenants**: Organizations with isolated resources, own API keys (KMS/Fernet encrypted)
- **RBAC**: owner > admin > member > viewer (platform admins bypass all)
- **Data isolation**: All tables have `tenant_id-index` GSI; `get_with_tenant()` validates ownership
- **System resources**: `tenant_id = "__SYSTEM__"` visible to all tenants
- **Workspace paths**: `{workspaces_dir}/{tenant_id}/{agent_id}/`

### Backend Structure

```
backend/
├── main.py                    # FastAPI entry, CORS, lifespan
├── config.py                  # Pydantic Settings from .env
├── routers/
│   ├── agents.py, skills.py, mcp.py, chat.py, plugins.py  # Resource CRUD (tenant-scoped)
│   ├── auth.py                # Register, login, refresh, /me
│   ├── tenants.py             # Tenant CRUD, API key mgmt, user invite
│   ├── admin.py               # Platform admin (system resources)
│   ├── workspace.py, settings.py
├── middleware/
│   ├── auth.py                # JWT verification → get_current_user()
│   └── tenant.py              # TenantContext, require_role(), require_platform_admin()
├── core/
│   ├── agent_manager.py       # ClaudeSDKClient lifecycle, per-tenant env injection
│   ├── key_manager.py         # API key encryption (KMS envelope / Fernet fallback)
│   ├── workspace_manager.py   # Per-tenant per-agent workspace isolation
│   ├── skill_manager.py       # S3 sync, tenant-scoped prefixes
│   ├── session_manager.py, plugin_manager.py
│   └── auth.py                # JWT create/verify (embeds tenant_id + role)
├── database/
│   ├── base.py                # Abstract: put, get, list, list_by_tenant, get_with_tenant
│   └── dynamodb.py            # DynamoDB impl + TenantsTable (slug lookup)
├── schemas/                   # Pydantic models (all have tenant_id, created_by)
│   ├── tenant.py, auth.py, agent.py, skill.py, mcp.py, message.py, plugin.py, settings.py
└── scripts/
    └── migrate_to_multi_tenancy.py  # Backfill tenant_id on existing data
```

### Frontend Structure

```
frontend/src/
├── App.tsx                    # AuthProvider + ProtectedRoute + Router
├── contexts/AuthContext.tsx   # Auth state, login/register/logout
├── components/common/ProtectedRoute.tsx
├── pages/
│   ├── LoginPage.tsx, RegisterPage.tsx, TenantSettingsPage.tsx  # Auth/tenant UI
│   ├── ChatPage, AgentsPage, SkillsPage, PluginsPage, MCPPage, etc.
├── services/
│   ├── auth.ts               # Token mgmt (localStorage: auth_token)
│   ├── api.ts                # Axios + auth interceptor
│   ├── chat.ts               # SSE with Authorization header
│   ├── agents.ts, skills.ts, mcp.ts, plugins.ts  # CRUD + toCamelCase()
├── types/index.ts             # All interfaces (Agent, Skill, Tenant, etc.)
```

## Critical Conventions

### snake_case ↔ camelCase

Backend uses `snake_case`, frontend uses `camelCase`. When adding a new field:
1. Add to backend Pydantic model (`backend/schemas/*.py`)
2. Add to frontend TypeScript interface (`frontend/src/types/index.ts`)
3. **Update `toCamelCase()` in the matching `frontend/src/services/*.ts`** — forgetting this = field is `undefined`

### Authentication Flow

- All endpoints (except `/auth/login`, `/auth/register`) require `TenantContext = Depends(get_tenant_context)`
- JWT contains `sub` (user_id), `tid` (tenant_id), `role`
- SSE endpoints (`chat.ts`) pass token via `Authorization` header in fetch
- Frontend stores tokens in `localStorage` (`auth_token`, `auth_refresh_token`)

### Database Operations

```python
# List tenant resources (merging with system):
tenant_items, system_items = await asyncio.gather(
    db.skills.list_by_tenant(ctx.tenant_id),
    db.skills.list_by_tenant("__SYSTEM__"),
)

# Get with tenant validation (returns None on cross-tenant, not 403):
item = await db.agents.get_with_tenant(agent_id, ctx.tenant_id)

# Create with tenant context:
agent_data = {**data, "tenant_id": ctx.tenant_id, "created_by": ctx.user_id}
```

### Per-Tenant API Key Injection

`agent_manager._create_client_with_tenant_env()` uses `asyncio.Lock` to safely set/restore `os.environ` around `ClaudeSDKClient` creation. Keys are decrypted from the tenant record via `key_manager.get_tenant_api_key()`.

## Security (6 Layers)

```
Layer 5: Bash command path validation
Layer 4: File tool access control (Read/Write/Edit/Glob/Grep)
Layer 3: Skill access hook (PreToolUse)
Layer 2: Per-tenant per-agent workspace isolation
Layer 1: Database tenant isolation (tenant_id-index GSI)
Layer 0: JWT authentication + RBAC
```

See [SECURITY.md](./SECURITY.md) for details.

## Environment Variables

```env
# Required (or set per-tenant via UI)
ANTHROPIC_API_KEY=your-key

# Multi-tenancy encryption
TENANT_KEY_ENCRYPTION_SECRET=change-this-in-production  # MUST change for prod
USE_KMS_ENCRYPTION=false                                 # true for prod with KMS

# Optional
CLAUDE_CODE_USE_BEDROCK=true
DEFAULT_MODEL=claude-sonnet-4-5-20250929
DEBUG=true
```

## API Endpoints

### Auth
`POST /api/auth/register` · `POST /api/auth/login` · `POST /api/auth/refresh` · `GET /api/auth/me`

### Tenants
`POST /api/tenants` · `GET /api/tenants/current` · `PUT /api/tenants/current` · `PUT /api/tenants/current/api-key` · `GET /api/tenants/current/users` · `POST /api/tenants/current/users/invite`

### Resources (all tenant-scoped)
`GET|POST /api/agents` · `GET|PUT|DELETE /api/agents/{id}` · `GET|POST /api/skills` · `GET|POST /api/mcp` · `POST /api/chat/stream` (SSE)

### Admin (platform admin only)
`GET /api/admin/tenants` · `PUT /api/admin/tenants/{id}/status` · `POST /api/admin/skills` · `POST /api/admin/mcp`

## Design System

- **Primary**: `#2b6cee` · **Background**: `#101622` · **Card**: `#1a1f2e` · **Muted**: `#9da6b9`
- **Font**: Space Grotesk · **Icons**: Material Symbols Outlined
- Tailwind CSS 4.x dark mode

## Production Deployment

- **Frontend**: S3 + CloudFront
- **Backend**: ECS Fargate with ALB
- **Database**: DynamoDB with tenant_id-index GSIs
- **Storage**: S3 (tenant-scoped prefixes: `tenants/{tid}/skills/`)
- **Secrets**: KMS for tenant API keys, Secrets Manager for platform keys
