# Quick Start Guide

## 🚀 Starting the Platform

```bash
./start.sh
```

This will:
- ✅ Check and install dependencies
- ✅ Create `.env` from `.env.example` (if missing)
- ✅ Start backend on http://localhost:8000
- ✅ Start frontend on http://localhost:5173
- ✅ Save logs to `logs/` directory

**⚠️ Important**: After first run, edit `backend/.env` and add your `ANTHROPIC_API_KEY`

## 🔐 First-Time Setup

After starting the platform:

1. Open http://localhost:5173 — you'll be redirected to the **login page**
2. Click **Register** to create your account (email + password)
3. After registration, create a **tenant** (organization) via the Tenant Settings page (`/tenant`)
4. Set your **Anthropic API key** in Tenant Settings (each tenant manages their own key)
5. Start creating agents and chatting!

## 🛑 Stopping the Platform

```bash
./stop.sh
```

## 🔄 Restarting the Platform

```bash
./restart.sh
```

## 📊 Check Status

```bash
./status.sh
```

Shows:
- Process status (running/stopped)
- Port availability
- Log file locations and sizes
- Quick command reference

## 📝 View Logs

```bash
# Backend logs
tail -f logs/backend.log

# Frontend logs
tail -f logs/frontend.log

# Both logs
tail -f logs/*.log
```

## 🌐 Access Points

- **Frontend UI**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Login Page**: http://localhost:5173/login
- **Register Page**: http://localhost:5173/register
- **Tenant Settings**: http://localhost:5173/tenant

## 🔧 Troubleshooting

### Port Already in Use

```bash
# Kill process on port 8000 (backend)
lsof -ti:8000 | xargs kill -9

# Kill process on port 5173 (frontend)
lsof -ti:5173 | xargs kill -9

# Or just run stop script
./stop.sh
```

### Services Not Starting

1. Check logs: `tail -f logs/backend.log` or `tail -f logs/frontend.log`
2. Verify `.env` file exists with `ANTHROPIC_API_KEY`
3. Ensure dependencies are installed:
   - Backend: `cd backend && source .venv/bin/activate && uv pip install -r requirements.txt`
   - Frontend: `cd frontend && npm install`

### Clean Restart

```bash
# Stop everything
./stop.sh

# Clean up PIDs and logs
rm -rf .pids logs

# Start fresh
./start.sh
```

## 🔄 Data Migration (Existing Installations)

If upgrading from a pre-multi-tenancy version:

```bash
# 1. Run the migration script to backfill tenant_id on existing data
cd backend
python scripts/migrate_to_multi_tenancy.py

# 2. Run init-aws.sh to add GSIs to DynamoDB tables
cd .. && bash init-aws.sh
```

This creates a "default-tenant", assigns all existing resources and users to it, and adds the required database indexes.

## 📚 Documentation

- **CLAUDE.md** - Comprehensive guide for Claude Code
- **README.md** - Full project documentation
- **ARCHITECTURE.md** - System architecture details
- **backend/.env.example** - Environment variables template

## 💡 Common Tasks

### Update Dependencies

```bash
# Backend
cd backend
source .venv/bin/activate
uv pip install --upgrade -r requirements.txt

# Frontend
cd frontend
npm update
```

### Run Tests

```bash
# Frontend tests
cd frontend
npm run test
```

### Build for Production

```bash
# Frontend
cd frontend
npm run build

# Preview production build
npm run preview
```
