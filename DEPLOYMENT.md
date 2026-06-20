"""
Setup and deployment instructions for Ethera v2.0
"""

# Local Development

```bash
# 1. Clone repository
git clone https://github.com/yourusername/ethera-AI-assessment.git
cd ethera-AI-assessment

# 2. Setup environment
cp .env.example .env
# Edit .env if needed (defaults work for local)

# 3. Start with Docker Compose (includes Redis, Kafka, PostgreSQL)
docker compose up --build

# 4. Services available:
# - Frontend: http://localhost:3000
# - Backend API: http://localhost:8000
# - API Docs: http://localhost:8000/docs
# - Redis: localhost:6379
# - PostgreSQL: localhost:5432
# - Kafka: localhost:9092

# 5. Run tests
docker exec ethera-backend pytest

# 6. Load testing
pip install locust
locust -f tests/load_test.py --users=100 -H http://localhost:8000
```

## Production Deployment

### Backend (Render)

```yaml
# render.yaml already configured
# Just push to GitHub and Render auto-deploys
# Features:
# - Auto-SSL
# - Auto database migration
# - Auto scaling
```

### Frontend (Netlify)

```bash
# 1. Install Netlify CLI
npm install -g netlify-cli

# 2. Deploy
netlify deploy --prod --dir=frontend/build

# 3. Set environment variable
# Site Settings > Build & Deploy > Environment
# REACT_APP_API_URL = https://your-backend.onrender.com
```

### Docker Hub

```bash
# Build and push image
docker build -t yourusername/ethera-backend:latest ./backend
docker push yourusername/ethera-backend:latest

# Pull on server
docker pull yourusername/ethera-backend:latest
docker run -p 8000:8000 yourusername/ethera-backend:latest
```

## Configuration Reference

### Database

```env
DATABASE_URL=postgresql://user:password@host:5432/dbname
# Async URL format: postgresql+asyncpg://...
```

### Cache (Redis)

```env
REDIS_URL=redis://host:6379/0
ENABLE_CACHE=true
```

### Event Streaming (Kafka)

```env
KAFKA_BROKERS=kafka:9092
KAFKA_ENABLED=true
```

### API Security

```env
JWT_SECRET=very-long-random-string-min-32-chars
RATE_LIMIT_ENABLED=true
REQUESTS_PER_MINUTE=60
```

### Logging

```env
LOG_LEVEL=INFO          # INFO, WARNING, ERROR, DEBUG
JSON_LOGS=true          # Structured JSON logging
```

## Performance Tuning

### 1. Connection Pooling

Edit `backend/app/database.py`:
```python
engine = create_async_engine(
    DATABASE_URL,
    pool_size=50,        # Increase for more concurrent users
    max_overflow=20,
)
```

### 2. Cache TTL

Edit `backend/app/main.py`:
```python
await cache_manager.set(key, value, ttl=600)  # 10 minutes
```

### 3. Pagination Limits

Edit `backend/app/schemas.py`:
```python
limit: int = Query(20, ge=1, le=500)  # Max 500 items
```

### 4. Uvicorn Workers

Edit `backend/Dockerfile`:
```dockerfile
CMD ["uvicorn", "app.main:app", "--workers", "8"]  # Increase workers
```

## Monitoring

### Prometheus Metrics

```python
from prometheus_client import Counter, Histogram

request_count = Counter('requests_total', 'Total requests')
request_duration = Histogram('request_duration_seconds', 'Request latency')
```

### Log Aggregation (ELK Stack)

```yaml
# docker-compose.yml addition
elasticsearch:
  image: docker.elastic.co/elasticsearch/elasticsearch:8.0.0

kibana:
  image: docker.elastic.co/kibana/kibana:8.0.0
  ports:
    - "5601:5601"
```

### Error Tracking (Sentry)

```python
import sentry_sdk
sentry_sdk.init("https://key@sentry.io/project-id")
```

## Scaling Guide

### Vertical Scaling (Bigger Server)

1. Increase `pool_size` in database config
2. Increase `--workers` in Dockerfile
3. Increase Redis memory allocation
4. Monitor CPU/memory usage

### Horizontal Scaling (Multiple Servers)

```yaml
# Load balancer (Nginx)
upstream backend {
    server api1.example.com:8000;
    server api2.example.com:8000;
    server api3.example.com:8000;
}

server {
    location /api {
        proxy_pass http://backend;
    }
}
```

### Database Scaling

1. **Read Replicas:** Separate read/write operations
2. **Sharding:** Distribute data across multiple databases
3. **Connection Pooling:** Use PgBouncer

```sql
-- Create read replica
CREATE PUBLICATION pub_all FOR ALL TABLES;
CREATE SUBSCRIPTION sub_replica CONNECTION '...' PUBLICATION pub_all;
```

## Troubleshooting

### Issue: "too many connections"
- Increase `pool_size`
- Enable connection pooling (PgBouncer)
- Check for connection leaks

### Issue: High latency
- Enable Redis caching
- Check database indexes
- Run ANALYZE on tables
- Check Kafka broker health

### Issue: Memory leak
- Check for unclosed database sessions
- Monitor Redis memory usage
- Review async context managers

### Issue: Kafka broker unreachable
- Check Kafka container is running
- Verify `KAFKA_BROKERS` environment variable
- Check firewall rules

## Backup & Recovery

### Database Backup

```bash
# Daily backup
pg_dump postgresql://user:pass@localhost/dbname > backup-$(date +%Y%m%d).sql

# Restore
psql postgresql://user:pass@localhost/dbname < backup-20240120.sql
```

### Redis Backup

```bash
# Auto-save enabled in docker-compose.yml
# Manual snapshot
redis-cli BGSAVE
```

## Security Hardening

1. **Enable JWT authentication**
   ```env
   ENABLE_AUTH=true
   ```

2. **Set strong secrets**
   ```bash
   JWT_SECRET=$(openssl rand -base64 32)
   ```

3. **Use environment variables**
   - Never hardcode credentials
   - Use .env files (in .gitignore)

4. **Enable rate limiting**
   ```env
   RATE_LIMIT_ENABLED=true
   REQUESTS_PER_MINUTE=60
   ```

5. **HTTPS/SSL**
   - Render auto-provides SSL
   - Configure in Netlify > Domain settings

## Performance Benchmarks

Expected performance with optimizations:

| Scenario | Throughput | Latency | Notes |
|----------|-----------|---------|-------|
| Single server, 10 users | 100 req/s | 50ms | Baseline |
| Single server, 100 users | 500 req/s | 100ms | Cache helps |
| Single server, 1000 users | 1000 req/s | 200ms | Cache critical |
| 3 servers (LB) | 2500 req/s | 150ms | Horizontal scale |
| 5 servers (LB) | 4000 req/s | 120ms | Optimal |

## Maintenance

### Weekly
- Check error logs
- Monitor cache hit rate
- Verify backups completed

### Monthly
- Analyze slow queries
- Review database stats
- Check disk space

### Quarterly
- Performance testing
- Security audit
- Disaster recovery drill
