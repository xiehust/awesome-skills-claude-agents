<div align="center">

# Claude Code Agent Skill Platform

### Claude Code智能体技能平台

[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![React](https://img.shields.io/badge/React-19-61DAFB?style=flat&logo=react&logoColor=black)](https://react.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.x-3178C6?style=flat&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Claude](https://img.shields.io/badge/Claude-Agent_SDK-191919?style=flat&logo=anthropic&logoColor=white)](https://github.com/anthropics/claude-code)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat)](./LICENSE)

[![English](https://img.shields.io/badge/lang-English-blue?style=flat)](./README_EN.md) | **简体中文**

基于 Claude Agent SDK 的全栈 AI 智能体平台，用于管理和交互可定制的 AI 智能体。

[✨ 特性](#功能特性) • [🚀 快速开始](#快速开始) • [🛡️ 安全性](#安全性) • [📚 文档](#架构) • [🎨 设计](#设计系统)

</div>

---

## 概述

本平台为用户提供以下功能：
- **多租户隔离**：组织级多租户架构，每个租户独立管理 API 密钥、资源和用户
- **与 AI 智能体对话**：通过 SSE 流式传输的交互式聊天界面
- **管理智能体**：创建、配置和监控 AI 智能体
- **管理技能**：上传和生成自定义技能
- **管理 MCP 服务器**：配置模型上下文协议（Model Context Protocol）服务器连接
- **用户认证与权限**：JWT 认证、基于角色的访问控制（owner/admin/member/viewer）

## 技术栈

### 前端
- React 18 + TypeScript
- Vite（构建工具）
- Tailwind CSS 4.x（样式）
- TanStack Query（状态管理）
- React Router v6（路由）
- Axios（HTTP 客户端）

### 后端
- FastAPI（Python Web 框架）
- Uvicorn（ASGI 服务器）
- Pydantic v2（数据验证）
- DynamoDB（生产数据库）
- AWS KMS / Fernet（API 密钥加密）
- JWT + RBAC（认证与授权）

## 安全性

平台实施了全面的**纵深防御安全模型**，通过多层保护确保智能体安全隔离运行：

### 🛡️ 四层安全防护

0. **多租户隔离（新增）**：组织级数据隔离
   - 每个租户拥有独立的工作空间目录：`{workspaces_dir}/{tenant_id}/{agent_id}/`
   - 所有数据库查询通过 `tenant_id-index` GSI 限定租户范围
   - 跨租户访问尝试返回 404（防止存在性泄露）并记录安全日志
   - 每租户独立的 Anthropic API 密钥（KMS 信封加密）

1. **工作空间隔离**：每个智能体在独立的工作空间中运行，通过符号链接访问技能
   - 每个智能体独立的工作空间：`/tmp/agent-platform-workspaces/{agent_id}/`
   - 只有授权的技能被符号链接（基于智能体配置）
   - 防止通过父目录遍历发现未授权技能

2. **技能访问控制**：PreToolUse 钩子验证技能调用
   - 阻止未授权的 Skill 工具调用（当 `allow_all_skills=False` 时）
   - 与工作空间隔离提供冗余保护

3. **文件工具访问控制**：验证 Read/Write/Edit/Glob/Grep 的文件路径
   - 确保智能体只能访问其工作空间内的文件
   - 阻止访问系统文件、其他智能体的工作空间和主工作空间
   - 使用 `os.path.normpath()` 防止路径遍历攻击

4. **Bash 命令保护**：解析和验证 bash 命令中的文件路径
   - 防止通过 bash 命令绕过文件访问控制
   - 检测如 `cat /etc/passwd`、`echo "data" > /tmp/bad.txt` 等命令
   - 允许相对路径（由于 `cwd` 限制是安全的）

### 🔒 智能体的权限范围

**智能体可以**：
- ✅ 读写其工作空间内的文件
- ✅ 使用相对路径执行 bash 命令
- ✅ 使用其授权的技能
- ✅ 通过 bash 命令访问其工作空间内的文件

**智能体不能**：
- 🚫 访问其他智能体的工作空间
- 🚫 访问系统文件（`/etc/passwd`、`/var/log/` 等）
- 🚫 访问主工作空间（技能存储位置）
- 🚫 使用未授权的技能
- 🚫 通过带绝对路径的 bash 命令绕过限制

### 📚 详细文档

要了解完整的安全细节，包括：
- 安全架构图
- 各层的实现细节
- 配置选项
- 测试和验证
- 已知限制和缓解措施
- 管理员和开发者最佳实践

请查看 **[SECURITY.md](./SECURITY.md)** 获取完整的安全文档。

## 项目结构

```
awesome-skills-claude-agents/
├── ARCHITECTURE.md          # 系统架构文档
├── DEVELOPMENT_PLAN.md      # 开发计划和路线图
├── SECURITY.md              # 安全架构和访问控制
├── README.md                # 英文版本
├── README_CN.md             # 中文版本（本文件）
├── frontend/                # React 前端应用
│   ├── src/
│   │   ├── components/      # 可复用 UI 组件
│   │   │   ├── common/      # 布局、侧边栏、按钮等
│   │   │   ├── chat/        # 聊天相关组件
│   │   │   ├── agents/      # 智能体管理组件
│   │   │   ├── skills/      # 技能管理组件
│   │   │   └── mcp/         # MCP 管理组件
│   │   ├── contexts/        # React Contexts
│   │   │   └── AuthContext.tsx # 认证上下文（新增）
│   │   ├── pages/           # 页面组件
│   │   │   ├── LoginPage.tsx    # 登录页面（新增）
│   │   │   ├── RegisterPage.tsx # 注册页面（新增）
│   │   │   └── TenantSettingsPage.tsx # 租户设置（新增）
│   │   ├── hooks/           # 自定义 React Hooks
│   │   ├── services/        # API 服务函数
│   │   ├── types/           # TypeScript 类型定义
│   │   └── utils/           # 工具函数
│   ├── package.json
│   └── vite.config.ts
└── backend/                 # FastAPI 后端应用
    ├── main.py              # 应用入口
    ├── config.py            # 配置设置
    ├── routers/             # API 路由处理器
    │   ├── agents.py        # 智能体 CRUD 端点
    │   ├── skills.py        # 技能 CRUD 端点
    │   ├── mcp.py           # MCP CRUD 端点
    │   ├── chat.py          # 聊天流式端点
    │   ├── auth.py           # 认证端点
    │   ├── tenants.py        # 租户管理端点（新增）
    │   └── admin.py          # 平台管理端点（新增）
    ├── middleware/           # 中间件
    │   ├── auth.py           # JWT 认证中间件
    │   └── tenant.py         # 租户上下文与 RBAC（新增）
    ├── core/                # 业务逻辑
    │   ├── agent_manager.py # 智能体生命周期管理
    │   ├── key_manager.py   # API 密钥加密管理（新增）
    │   ├── session_manager.py # 会话管理
    │   └── workspace_manager.py # 工作空间隔离管理
    ├── database/            # 数据库层
    │   └── dynamodb.py      # DynamoDB 数据库
    ├── schemas/             # Pydantic 模型
    └── requirements.txt
```

## 快速开始

### 前置要求

- Node.js 18+ 和 npm
- Python 3.12+
- uv（Python 包管理器，推荐）或 pip
- ANTHROPIC_API_KEY 环境变量

### 快速启动（推荐）

使用提供的脚本是运行平台最简单的方式：

```bash
# 启动后端和前端
./start.sh

# 停止所有服务
./stop.sh
```

`start.sh` 脚本将：
- 检查并在需要时安装依赖
- 如果不存在则从 `.env.example` 创建 `.env` 文件
- 在 http://localhost:8000 启动后端
- 在 http://localhost:5173 启动前端
- 显示日志位置和状态

**重要提示**：首次运行 `./start.sh` 后，请编辑 `backend/.env` 并添加您的 `ANTHROPIC_API_KEY`。

### 手动设置

#### 前端设置

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端将在 http://localhost:5173 可用

#### 后端设置

```bash
cd backend

# 创建虚拟环境（使用 uv）
uv sync
source .venv/bin/activate  # Windows: .venv\Scripts\activate


# 创建 .env 文件
cp .env.example .env
# 编辑 .env 并添加您的 ANTHROPIC_API_KEY

# 启动服务器
python main.py
# 或直接使用 uvicorn：
# uvicorn main:app --reload --port 8000
```

后端 API 将在 http://localhost:8000 可用

API 文档：http://localhost:8000/docs

### 手动运行两个服务

对于开发，运行两个服务：

1. 终端 1（后端）：
   ```bash
   cd backend && python main.py
   ```

2. 终端 2（前端）：
   ```bash
   cd frontend && npm run dev
   ```

前端已配置为将 `/api` 请求代理到后端。

### 查看日志

使用 `./start.sh` 运行时，日志存储在 `logs/` 目录：

```bash
# 查看后端日志
tail -f logs/backend.log

# 查看前端日志
tail -f logs/frontend.log
```

## 功能特性

### 聊天界面
- 通过 SSE 实时流式响应
- 消息历史侧边栏
- 工具调用可视化
- 启用/禁用技能和 MCP 开关

### 智能体管理
- 创建、编辑和删除智能体
- 配置模型、最大令牌数和权限
- 为智能体分配技能和 MCP 服务器
- 切换智能体状态（激活/停用）

### 技能管理
- 列出和搜索技能
- 上传技能包（ZIP）
- AI 生成技能创建
- 删除自定义技能

### MCP 服务器管理
- 列出和搜索 MCP 服务器
- 添加新的 MCP 服务器配置
- 支持 stdio、SSE 和 HTTP 连接类型
- 连接状态监控
- 测试连接

### 用户认证
- 邮箱/密码注册与登录
- JWT 令牌认证（访问令牌 + 刷新令牌）
- 受保护路由（未认证重定向到登录页）

### 多租户管理
- 创建和管理组织（租户）
- 邀请用户并分配角色（owner/admin/member/viewer）
- 每租户独立的 Anthropic API 密钥管理
- 租户资源隔离（智能体、技能、会话等）

## API 端点

### 智能体
- `GET /api/agents` - 列出所有智能体
- `GET /api/agents/{id}` - 通过 ID 获取智能体
- `POST /api/agents` - 创建智能体
- `PUT /api/agents/{id}` - 更新智能体
- `DELETE /api/agents/{id}` - 删除智能体

### 技能
- `GET /api/skills` - 列出所有技能
- `POST /api/skills/upload` - 上传技能 ZIP
- `POST /api/skills/generate` - AI 生成技能
- `DELETE /api/skills/{id}` - 删除技能

### MCP 服务器
- `GET /api/mcp` - 列出所有 MCP 服务器
- `POST /api/mcp` - 创建 MCP 服务器
- `PUT /api/mcp/{id}` - 更新 MCP 服务器
- `DELETE /api/mcp/{id}` - 删除 MCP 服务器
- `POST /api/mcp/{id}/test` - 测试连接

### 聊天
- `POST /api/chat/stream` - 流式聊天（SSE）
- `GET /api/chat/sessions` - 列出会话
- `DELETE /api/chat/sessions/{id}` - 删除会话

### 认证
- `POST /api/auth/register` - 用户注册
- `POST /api/auth/login` - 用户登录
- `POST /api/auth/refresh` - 刷新令牌
- `GET /api/auth/me` - 获取当前用户信息

### 租户管理
- `POST /api/tenants` - 创建租户
- `GET /api/tenants/current` - 获取当前租户信息
- `PUT /api/tenants/current` - 更新租户设置
- `PUT /api/tenants/current/api-key` - 设置/轮换 API 密钥
- `GET /api/tenants/current/users` - 列出租户用户
- `POST /api/tenants/current/users/invite` - 邀请用户

### 平台管理（管理员）
- `GET /api/admin/tenants` - 列出所有租户
- `PUT /api/admin/tenants/{id}/status` - 暂停/激活租户
- `POST /api/admin/skills` - 创建系统技能
- `POST /api/admin/mcp` - 创建系统 MCP 服务器

## 配置

### 环境变量

后端通过 `backend/.env` 中的环境变量支持多种配置选项：

#### 必需
- `ANTHROPIC_API_KEY` - 您的 Anthropic API 密钥（必需）

#### 可选 - Claude API 配置
- `ANTHROPIC_BASE_URL` - 自定义 API 端点 URL（用于代理或自定义端点）
- `CLAUDE_CODE_USE_BEDROCK` - 设置为 `true` 以使用 AWS Bedrock 而非 Anthropic API
- `CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS` - 设置为 `true` 以禁用实验性功能
- `DEFAULT_MODEL` - 默认 Claude 模型（默认：`claude-sonnet-4-5-20250929`）

#### 可选 - 服务器配置
- `DEBUG` - 启用调试模式（默认：`true`）
- `HOST` - 服务器主机（默认：`0.0.0.0`）
- `PORT` - 服务器端口（默认：`8000`）

#### 可选 - 多租户配置
- `TENANT_KEY_ENCRYPTION_SECRET` - 租户 API 密钥加密密钥（生产环境必须修改）
- `USE_KMS_ENCRYPTION` - 设置为 `true` 使用 AWS KMS 加密（生产推荐）
- `KMS_KEY_ALIAS` - KMS 密钥别名（默认：`alias/agent-platform-tenant-keys`）

完整配置模板请参见 `backend/.env.example`。

## 设计系统

UI 遵循一致的深色主题设计：

- **主色调**：`#2b6cee`（蓝色）
- **背景**：`#101622`（深色）
- **卡片背景**：`#1a1f2e`
- **字体**：Space Grotesk
- **图标**：Material Symbols Outlined

## 开发

### 前端命令

```bash
npm run dev          # 启动开发服务器
npm run build        # 构建生产版本
npm run preview      # 预览生产构建
npm run lint         # 运行 ESLint
npm run test         # 运行测试
```

### 后端命令

```bash
python main.py       # 启动并自动重载
uvicorn main:app --reload  # 替代启动方式
```

## 架构

详细的架构文档请参见 [ARCHITECTURE.md](./ARCHITECTURE.md)。

开发计划和路线图请参见 [DEVELOPMENT_PLAN.md](./DEVELOPMENT_PLAN.md)。

## 许可证

MIT License
