# Deployment Guide for Koyeb

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Koyeb Web     │     │  Koyeb Worker   │     │     Redis       │
│   (Django API)  │     │  (Huey Tasks)   │     │   (Upstash)     │
│                 │     │                 │     │                 │
│  Dockerfile     │     │ Dockerfile.worker│    │  Managed Redis  │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         └───────────────────────┴───────────────────────┘
                          REDIS_URL
```

## Prerequisites

1. **Redis Instance**: Get a managed Redis from:
   - [Upstash](https://upstash.com/) (recommended, has free tier)
   - [Redis Cloud](https://redis.com/cloud/)
   - Any Redis provider

2. **Koyeb Account**: Sign up at [koyeb.com](https://koyeb.com)

## Deployment Steps

### Step 1: Set Up Redis

1. Create a Redis instance on Upstash (or your preferred provider)
2. Copy the Redis URL (format: `redis://default:password@host:port`)

### Step 2: Deploy Web Service on Koyeb

1. Go to Koyeb Dashboard → Create Service
2. Connect your GitHub repository
3. Configure:
   - **Name**: `foodie-robot-web`
   - **Builder**: Dockerfile
   - **Dockerfile path**: `Dockerfile`
   - **Port**: 8000
4. Add environment variables (all from your `.env` file):
   ```
   SECRET_KEY=your-secret-key
   DEBUG=False
   REDIS_URL=redis://your-redis-url
   DATABASES_DEFAULT_ENGINE=...
   DATABASES_DEFAULT_NAME=...
   DATABASES_DEFAULT_HOST=...
   DATABASES_DEFAULT_PORT=...
   DATABASES_DEFAULT_USER=...
   DATABASES_DEFAULT_PASSWORD=...
   # ... all other env vars
   ```
5. Deploy

### Step 3: Deploy Worker Service on Koyeb

1. Go to Koyeb Dashboard → Create Service
2. Connect the same GitHub repository
3. Configure:
   - **Name**: `foodie-robot-worker`
   - **Builder**: Dockerfile
   - **Dockerfile path**: `Dockerfile.worker`
   - **Service type**: Worker (no exposed ports)
4. Add the **same environment variables** as the web service
5. Deploy

## Environment Variables

Add `REDIS_URL` to your `.env` file:

```env
# Huey/Redis Configuration
REDIS_URL=redis://default:your-password@your-host.upstash.io:6379
```

## Local Development

### Using Docker Compose

```bash
# Start all services (web, worker, redis)
docker-compose up

# Start in background
docker-compose up -d

# View logs
docker-compose logs -f worker

# Stop all services
docker-compose down
```

### Without Docker

```bash
# Terminal 1: Run Django server
python manage.py runserver

# Terminal 2: Run Huey worker
python manage.py run_huey
```

## Scheduled Tasks

| Task | Schedule | Description |
|------|----------|-------------|
| `scheduled_remind_users_to_reply` | Every 30 min | Reminds users who haven't replied in 23-24 hours |
| `scheduled_send_meal_recommendations` | Every 30 min | Sends meal recommendations to active users |

## Management Commands

```bash
# Run remind users task manually (synchronous)
python manage.py remind_users

# Run remind users task async (queued to Huey)
python manage.py remind_users --async

# Run meal recommendations manually (synchronous)
python manage.py send_meal_recommendations

# Run meal recommendations async (queued to Huey)
python manage.py send_meal_recommendations --async
```

## Monitoring

### Check Huey Status

The Huey consumer logs task execution. In Koyeb, view logs for the worker service to monitor:
- Task starts/completions
- Periodic task schedules
- Any errors

### Huey Consumer Options

```bash
# Basic run (periodic tasks enabled by default)
python manage.py run_huey

# With more workers (for high volume)
python manage.py run_huey --workers 2

# Verbose logging
python manage.py run_huey --huey-verbose

# Disable periodic tasks (only process queued tasks)
python manage.py run_huey --no-periodic
```

## Troubleshooting

### Tasks not running?

1. Check worker service is running in Koyeb
2. Verify `REDIS_URL` is correct in both services
3. Check worker logs for errors

### Redis connection errors?

1. Verify Redis URL format: `redis://user:password@host:port`
2. Check if Redis instance is running
3. Ensure firewall/network allows connection

### Tasks running twice?

Only run ONE worker instance. If you need more throughput, increase workers within one instance:
```bash
python manage.py run_huey --workers 4
```
