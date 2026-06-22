# Deploying foodie_robot on Alibaba Cloud (Option B — managed DB + Redis)

## Services to provision
| Component | Alibaba Cloud product | Notes |
|-----------|----------------------|-------|
| App host (web + worker + nginx) | **ECS** (2 vCPU / 4 GB Linux) | Runs `docker-compose.prod.yml` |
| Database | **ApsaraDB RDS for PostgreSQL** | Run `CREATE EXTENSION postgis;` — app uses geo features |
| Cache / queue | **ApsaraDB for Redis (Tair)** | Used by Channels, Huey, Django cache |
| Image registry | **ACR** (Container Registry) | Optional; push images instead of building on ECS |
| Public IP / TLS | **EIP** + Security Group | Open 80/443; certbot for HTTPS |
| Media | **Cloudinary** | External, already configured |
| LLM | **Model Studio / DashScope (Qwen)** | `DASHSCOPE_API_KEY` |

## 1. Environment variables (.env on the ECS box)
Existing keys stay as-is. Point DB/Redis at the managed services:

```
DEBUG=False
ALLOWED_HOST=your-domain.com
DATABASES_DEFAULT_ENGINE=django.contrib.gis.db.backends.postgis   # if using PostGIS backend
DATABASES_DEFAULT_HOST=<rds-internal-endpoint>
DATABASES_DEFAULT_PORT=5432
DATABASES_DEFAULT_NAME=foodie
DATABASES_DEFAULT_USER=<rds-user>
DATABASES_DEFAULT_PASSWORD=<rds-password>
REDIS_URL=redis://:<password>@<tair-endpoint>:6379/0
```

### AI models (Alibaba Cloud Model Studio / DashScope)
`DASHSCOPE_API_KEY` is the only required key. Optional overrides (defaults shown):

```
# AI_API_KEY=<defaults to DASHSCOPE_API_KEY>
# AI_BASE_URL=https://dashscope-intl.aliyuncs.com/compatible-mode/v1
# AI_CHAT_MODEL=qwen-max
# AI_VISION_MODEL=qwen-vl-max
# AI_EMBEDDING_MODEL=text-embedding-v4
# AI_EMBEDDING_DIMENSIONS=1536
# AI_EMBEDDING_BATCH_SIZE=10
# AI_REASONING_EFFORT=
```

## 2. Bring it up
```bash
# On the ECS instance (Docker + compose installed)
git clone <repo> && cd foodie_robot_backend
cp .env.example .env   # then fill in real values

# Issue TLS cert (one time)
sudo certbot certonly --standalone -d your-domain.com
# Edit deploy/nginx.conf and replace YOUR_DOMAIN

docker compose -f docker-compose.prod.yml --env-file .env up -d --build
```
`pre_run.sh` runs `collectstatic` + `migrate` automatically when `web` starts.

## 3. One-time: build embeddings
Generate meal embeddings and clear the cached tool embeddings.

```bash
# Build all meal embeddings
docker compose -f docker-compose.prod.yml exec web \
  python manage.py compute_meal_embeddings --force

# Clear the tool-embedding cache (Django DatabaseCache, table api_cache_table).
# It also auto-expires in 7 days; this forces an immediate refresh.
docker compose -f docker-compose.prod.yml exec web \
  python manage.py shell -c "from django.core.cache import cache; cache.clear()"
```

## 4. Verify
```bash
docker compose -f docker-compose.prod.yml logs -f web worker
```
Send a WhatsApp test message and confirm tool calls + meal analysis work.
