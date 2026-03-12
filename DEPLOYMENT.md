# Deployment Quick Start - Safe Ingestion Engine

## 🚀 After Workflow Completes

### Option 1: Docker Compose (Development/Testing)

```bash
# Create .env from template
cp .env.example .env

# Update with your values
REDIS_URL=redis://redis:6379/0
PII_SALT=your-random-32-char-salt
DASHBOARD_ADMIN_PASSWORD=strong-password

# Start the full stack
docker compose up -d

# Verify
curl http://localhost:8000/health
curl http://localhost:8501  # Streamlit dashboard
```

---

### Option 2: Docker Hub Image (Production)

#### Prerequisites

- Docker installed locally or on your server
- Image published to Docker Hub (via GitHub Actions)

#### On your production server:

```bash
# 1. Create .env file
cat > .env << 'EOF'
REDIS_URL=redis://redis:6379/0
PII_SALT=$(openssl rand -base64 24)
DASHBOARD_ADMIN_PASSWORD=$(openssl rand -base64 16)
CORS_ORIGINS=https://safe.teosegypt.com
USER_AGENT=SafeIngestion/1.0
DATA_DIR=/data
EOF

# 2. Pull latest image from Docker Hub
docker pull yourusername/safe-ingestion-engine:latest

# 3. Run API container
docker run -d \
  --name safe-api \
  --restart unless-stopped \
  -p 8000:8000 \
  --env-file .env \
  -v /data:/app/data \
  --link redis:redis \
  yourusername/safe-ingestion-engine:latest \
  uvicorn api.server:app --host 0.0.0.0 --port 8000

# 4. Run worker container
docker run -d \
  --name safe-worker \
  --restart unless-stopped \
  --env-file .env \
  -v /data:/app/data \
  --link redis:redis \
  yourusername/safe-ingestion-engine:latest \
  celery -A api.tasks.celery_app worker --loglevel=info

# 5. Run dashboard (optional)
docker run -d \
  --name safe-dashboard \
  --restart unless-stopped \
  -p 8501:8501 \
  --env-file .env \
  -v /data:/app/data \
  --link redis:redis \
  yourusername/safe-ingestion-engine:latest \
  streamlit run dashboard/app.py --server.port 8501

# 6. Verify
sleep 5
curl http://localhost:8000/health
```

---

### Option 3: Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: safe-ingestion-api
  labels:
    app: safe-ingestion
spec:
  replicas: 2
  selector:
    matchLabels:
      app: safe-ingestion
  template:
    metadata:
      labels:
        app: safe-ingestion
    spec:
      containers:
      - name: api
        image: yourusername/safe-ingestion-engine:latest
        ports:
        - containerPort: 8000
        env:
        - name: REDIS_URL
          value: "redis://redis:6379/0"
        - name: PII_SALT
          valueFrom:
            secretKeyRef:
              name: safe-secrets
              key: pii-salt
        - name: DASHBOARD_ADMIN_PASSWORD
          valueFrom:
            secretKeyRef:
              name: safe-secrets
              key: admin-password
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: safe-ingestion-service
spec:
  selector:
    app: safe-ingestion
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
```

Deploy with:
```bash
kubectl apply -f safe-ingestion-deployment.yaml
```

---

## 📊 Image Tags Reference

| Tag | Use Case | Branch/Event |
|-----|----------|-------------|
| `latest` | Production | `main` branch |
| `main-abc123d` | Specific commit (main) | Any commit to `main` |
| `1.0.0` | Release version | Tag `v1.0.0` |
| `dev` | Development | `dev` branch |

**Pull by tag:**
```bash
docker pull yourusername/safe-ingestion-engine:1.0.0
docker pull yourusername/safe-ingestion-engine:latest
docker pull yourusername/safe-ingestion-engine:dev
```

---

## ✅ Health Checks

### API Health
```bash
curl http://localhost:8000/health
# Expected: {"status": "ok", "timestamp": "..."}
```

### Redis Connection
```bash
redis-cli -h redis ping
# Expected: PONG
```

### Worker Status
```bash
docker logs safe-worker
# Expected: "celery@... ready"
```

### Dashboard (optional)
```bash
curl http://localhost:8501
# Expected: Streamlit web app
```

---

## 🔐 Security Best Practices

1. **Never commit `.env`** — It's in `.gitignore`
2. **Use strong passwords** — Generated via `openssl rand -base64 16`
3. **Rotate API keys** — Update `SHEET_API_SECRET` monthly
4. **Use secrets management** — In Kubernetes, use `kubectl create secret`
5. **Enable TLS/HTTPS** — Use reverse proxy (Nginx, Traefik)

---

## 📈 Scaling

### Multi-instance setup:

```bash
# Run 3 worker instances
for i in {1..3}; do
  docker run -d \
    --name safe-worker-$i \
    --env-file .env \
    -v /data:/app/data \
    --link redis:redis \
    yourusername/safe-ingestion-engine:latest \
    celery -A api.tasks.celery_app worker --loglevel=info
done
```

### Load balancing:

```nginx
upstream safe_api {
  server api1:8000;
  server api2:8000;
  server api3:8000;
}

server {
  listen 80;
  location / {
    proxy_pass http://safe_api;
  }
}
```

---

## 🆘 Troubleshooting

### API won't start
```bash
docker logs safe-api
# Check for: RedisConnectionError, import errors, invalid env vars
```

### Workers failing
```bash
docker logs safe-worker
# Check for: Redis connection, task definition errors
```

### High memory usage
```bash
docker stats safe-api
# Increase container limit in docker run or Kubernetes manifest
```

### Scan timeout
```bash
# Increase timeout in API config
# Default: 300 seconds (5 minutes)
# Edit: api/config.py
```

---

## 📞 Next Steps

1. Push to GitHub → Workflow runs automatically
2. Monitor GitHub Actions for build status
3. Once published, pull image to your server
4. Deploy using docker-compose, Docker, or Kubernetes
5. Point `safe.teosegypt.com` to your deployment
6. Test: `curl https://safe.teosegypt.com/v1/ingest_async`

---

**Status:** 🟢 **Ready to deploy**
