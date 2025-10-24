# DTaaS Production Deployment Guide

## Pre-Deployment Checklist

- [ ] Database migrated from SQLite to PostgreSQL
- [ ] Redis configured with persistence and HA
- [ ] Environment variables configured
- [ ] Security settings reviewed
- [ ] SSL/TLS certificates obtained
- [ ] Monitoring and logging configured
- [ ] Backup strategy implemented

## Environment Configuration

### Backend (.env)

```env
# Production Environment
ENVIRONMENT=production

# Database - PostgreSQL for production
DATABASE_URL=postgresql://user:password@db-host:5432/dtaas

# Redis - Use managed service in production
REDIS_URL=redis://:password@redis-host:6379/0

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=false

# CORS - Only allow your frontend domain
CORS_ORIGINS=https://your-domain.com

# Security - Generate strong secret key
SECRET_KEY=<generate-with: python -c "import secrets; print(secrets.token_urlsafe(32))">

# Celery
CELERY_BROKER_URL=redis://:password@redis-host:6379/0
CELERY_RESULT_BACKEND=redis://:password@redis-host:6379/0

# Logging
LOG_LEVEL=INFO

# WebSocket
WEBSOCKET_BROADCAST_INTERVAL=1.0
```

### Frontend (.env.production)

```env
VITE_API_BASE_URL=https://api.your-domain.com
VITE_WS_URL=wss://api.your-domain.com/ws
VITE_ENV=production
```

## Docker Deployment

### 1. Build Images

```bash
# Build backend image
docker build -t dtaas-backend:latest -f backend/Dockerfile backend/

# Build frontend image
docker build -t dtaas-frontend:latest -f frontend/Dockerfile frontend/
```

### 2. Deploy with Docker Compose

Update `docker-compose.yml` for production:

```yaml
version: '3.8'

services:
  backend:
    image: dtaas-backend:latest
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
    volumes:
      - ./logs:/app/logs
    restart: always

  celery:
    image: dtaas-backend:latest
    command: celery -A celery_app worker --loglevel=info
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
    restart: always

  frontend:
    image: dtaas-frontend:latest
    ports:
      - "80:80"
    restart: always

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis-data:/data
    restart: always

volumes:
  redis-data:
```

### 3. Deploy

```bash
docker-compose -f docker-compose.prod.yml up -d
```

## Kubernetes Deployment

### 1. Create Secrets

```bash
kubectl create secret generic dtaas-secrets \
  --from-literal=database-url=postgresql://... \
  --from-literal=redis-url=redis://... \
  --from-literal=secret-key=...
```

### 2. Deploy Resources

```yaml
# backend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dtaas-backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: dtaas-backend
  template:
    metadata:
      labels:
        app: dtaas-backend
    spec:
      containers:
      - name: backend
        image: dtaas-backend:latest
        ports:
        - containerPort: 8000
        env:
        - name: ENVIRONMENT
          value: "production"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: dtaas-secrets
              key: database-url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: dtaas-secrets
              key: redis-url
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
---
apiVersion: v1
kind: Service
metadata:
  name: dtaas-backend-service
spec:
  selector:
    app: dtaas-backend
  ports:
    - protocol: TCP
      port: 80
      targetPort: 8000
  type: LoadBalancer
```

```bash
kubectl apply -f kubernetes/
```

## Nginx Reverse Proxy

```nginx
# /etc/nginx/sites-available/dtaas

# Frontend
server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    root /var/www/dtaas/dist;
    index index.html;
    
    location / {
        try_files $uri $uri/ /index.html;
    }
}

# Backend API
server {
    listen 443 ssl http2;
    server_name api.your-domain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /ws {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Database Setup

### PostgreSQL

```sql
-- Create database
CREATE DATABASE dtaas;

-- Create user
CREATE USER dtaas_user WITH PASSWORD 'secure_password';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE dtaas TO dtaas_user;

-- Connect and initialize
\c dtaas
-- Run migrations
```

### Migration from SQLite

```bash
# Install tools
pip install sqlite3-to-postgres

# Convert
sqlite3-to-postgres --sqlite-file dtaas.db --postgres-uri postgresql://user:pass@host/dtaas
```

## Monitoring & Logging

### Application Logs

Logs are written to:
- Console (stdout/stderr) in JSON format
- `dtaas.log` file in production

### Metrics to Monitor

- API response time
- Task execution success rate
- Queue depth (Celery tasks pending)
- Database connection pool usage
- Memory usage
- CPU usage
- WebSocket connections

### Recommended Tools

- **APM**: Datadog, New Relic, or Sentry
- **Logs**: ELK Stack or Splunk
- **Metrics**: Prometheus + Grafana
- **Uptime**: UptimeRobot or Pingdom

## Security Checklist

- [ ] Change default SECRET_KEY
- [ ] Use environment variables for credentials
- [ ] Enable SSL/TLS for all connections
- [ ] Use strong database passwords
- [ ] Enable Redis authentication
- [ ] Configure CORS properly (only allow frontend domain)
- [ ] Implement rate limiting (optional)
- [ ] Regular security updates
- [ ] Regular backups
- [ ] Implement authentication (JWT recommended)
- [ ] Audit logging enabled

## Backup Strategy

### Database Backup

```bash
# Daily automated backup
#!/bin/bash
pg_dump -U dtaas_user -h localhost dtaas | gzip > /backups/dtaas_$(date +%Y%m%d).sql.gz

# Retention: Keep 30 days
find /backups -name "dtaas_*.sql.gz" -mtime +30 -delete
```

### Redis Backup

Redis with AOF (Append Only File) enabled automatically persists data.

```bash
# Backup Redis dump
cp /var/lib/redis/appendonly.aof /backups/redis_$(date +%Y%m%d).aof
```

## Scaling

### Horizontal Scaling

1. **Backend API**: Deploy multiple instances behind load balancer
2. **Celery Workers**: Add more worker instances
3. **Redis**: Use Redis Cluster or Sentinel for HA
4. **Database**: Use read replicas for reporting queries

### Vertical Scaling

- Increase memory for workers processing large datasets
- Increase CPU for faster task execution
- Use SSD storage for database

## Health Checks

### API Health Check

```bash
curl https://api.your-domain.com/health
# Expected: {"status": "healthy"}
```

### Celery Health Check

```bash
celery -A celery_app inspect ping
```

### Database Health Check

```bash
psql -h localhost -U dtaas_user -d dtaas -c "SELECT 1"
```

## Troubleshooting

### High Memory Usage

- Reduce batch sizes
- Reduce parallel table count
- Add more workers with less memory each

### Slow Performance

- Check database query performance
- Optimize indexes
- Increase worker count
- Use connection pooling

### Connection Issues

- Check firewall rules
- Verify network security groups
- Test connectivity between services

## Support

For production issues:
1. Check application logs
2. Review metrics dashboard
3. Test connectivity between services
4. Contact support team

---

For detailed architecture and features, see [README.md](./README.md)

