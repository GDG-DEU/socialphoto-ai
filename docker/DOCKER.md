# AI Service - Docker Deployment Guide

## 🐳 Quick Start

### Tüm Servisleri Başlat (Tek Komut)

```bash
cd docker
docker-compose up -d

# Veya production build için (dev dependencies olmadan)
docker-compose build --build-arg INSTALL_DEV=false
docker-compose up -d
```

Bu komut:
- ✅ Redis container'ı başlatır
- ✅ API Server container'ı başlatır (port 8000)
- ✅ 2 adet Worker container'ı başlatır
- ✅ Otomatik restart policy ile çalışır

### Logları İzle

```bash
# Tüm servislerin logları
docker-compose logs -f

# Sadece API logları
docker-compose logs -f api

# Sadece Worker logları
docker-compose logs -f worker
```

### Servisleri Durdur

```bash
cd docker
docker-compose down
```

### Her Şeyi Temizle (Volumes Dahil)

```bash
cd docker
docker-compose down -v
```

## 🔧 Configuration

### Environment Variables

Proje kök dizininde `.env` dosyası oluşturun:

```env
# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Application Configuration
LOG_LEVEL=INFO

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# Security Configuration
API_KEY=your-secret-api-key-change-this-in-production
SOCKET_IO_SECRET=your-secret-socketio-token-change-this-in-production

# Worker Configuration
WORKER_RETRY_DELAY=1
WORKER_MAX_RETRY_DELAY=30

# TTL Configuration (seconds)
JOB_QUEUED_TTL=86400
JOB_COMPLETED_TTL=1800
JOB_FAILED_TTL=1800
```

> **⚠️ IMPORTANT:** Production ortamında `API_KEY` ve `SOCKET_IO_SECRET` değerlerini mutlaka değiştirin!

### Docker Compose Configuration

Docker Compose, yukarıdaki `.env` dosyasını otomatik olarak kullanır (`env_file` directive ile). `REDIS_HOST` Docker network için `redis` olarak override edilir.

### Worker Sayısını Değiştir

```bash
# 5 worker başlat
docker-compose up -d --scale worker=5

# 1 worker'a düşür
docker-compose up -d --scale worker=1
```

### Build Arguments

Dockerfile `INSTALL_DEV` build argument'ini destekler:

- **Development (default)**: `INSTALL_DEV=true` - Test dependencies dahil (pytest, httpx, vb.)
- **Production**: `INSTALL_DEV=false` - Sadece runtime dependencies (daha küçük image)

```bash
# Development build (docker-compose default)
docker-compose build  # INSTALL_DEV=true

# Production build (manuel)
docker build -t ai-service:prod --build-arg INSTALL_DEV=false -f docker/Dockerfile .
```

## 📦 Docker Commands

### Build & Start

```bash
cd docker

# Build images
docker-compose build

# Start services
docker-compose up -d

# Build and start
docker-compose up -d --build
```

### Status & Monitoring

```bash
# Container durumları
docker-compose ps

# Resource kullanımı
docker stats

# Belirli bir service'e bağlan
docker-compose exec api bash
docker-compose exec worker bash
```

> **Not:** Container içinde Python komutları çalıştırırken `uv run` kullanın:
> ```bash
> # Container içinde
> uv run python -c "import redis; print(redis.__version__)"
> uv run pytest
> uv run python -m src.workers.analyze_worker
> ```

### Restart & Update

```bash
cd docker

# Tüm servisleri restart et
docker-compose restart

# Sadece API'yi restart et
docker-compose restart api

# Kod değişikliğinden sonra rebuild
docker-compose up -d --build
```

## 🧪 Testing

API çalıştıktan sonra:

```bash
# Swagger UI
open http://localhost:8000/docs

# Health check (authentication gerektirmez)
curl http://localhost:8000/health

# Test job oluştur (API Key gerekli)
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-api-key-change-this-in-production" \
  -d '{"post_id": "test123", "image_url": "https://example.com/image.jpg"}'

# Job status kontrolü (API Key gerekli)
curl -X GET http://localhost:8000/analyze/{job_id} \
  -H "X-API-Key: your-secret-api-key-change-this-in-production"
```

## 🐛 Troubleshooting

### Container çalışmıyor

```bash
# Container loglarını kontrol et
docker-compose logs api

# Container'a gir ve debug yap
docker-compose exec api bash
```

### Redis bağlantı hatası

```bash
# Redis health check
docker-compose exec redis redis-cli ping

# Redis loglarını kontrol et
docker-compose logs redis
```

### Port zaten kullanımda

```bash
# docker-compose.yml'de port değiştir
ports:
  - "8001:8000"  # 8000 yerine 8001 kullan
```

### Worker job almıyor

```bash
# Redis queue'yu kontrol et
docker-compose exec redis redis-cli llen analyze_queue
docker-compose exec redis redis-cli lrange analyze_queue 0 -1

# Worker loglarını kontrol et
docker-compose logs -f worker
```

### Image rebuild gerekiyor

```bash
# Cache'siz rebuild
docker-compose build --no-cache

# Tüm images'ları sil ve rebuild et
docker-compose down --rmi all
docker-compose up -d --build
```

## 🚀 Production Deployment

**Kullanım:**

```bash
cd docker
docker-compose -f docker-compose.yml up -d --build
```

## 📊 Architecture

```
┌─────────────────────────────────────────┐
│         Docker Network                  │
│                                         │
│  ┌──────────┐      ┌──────────┐       │
│  │   API    │◄────►│  Redis   │       │
│  │  :8000   │      │  :6379   │       │
│  └──────────┘      └────▲─────┘       │
│                          │              │
│  ┌──────────┐           │              │
│  │ Worker 1 │───────────┤              │
│  └──────────┘           │              │
│  ┌──────────┐           │              │
│  │ Worker 2 │───────────┘              │
│  └──────────┘                          │
│                                         │
└─────────────────────────────────────────┘
```

## 🔐 Security Best Practices

### Authentication & Authorization

1. **API Key Authentication**: 
   - Tüm endpoint'ler (health hariç) `X-API-Key` header gerektir
   - Backend servisi her istekte bu key'i göndermeli
   - Production'da güçlü, unique key kullanın (min 32 karakter)

2. **Socket.IO Authentication**:
   - Socket.IO bağlantıları auth token gerektir
   - Backend bağlanırken `auth={'token': 'YOUR_TOKEN'}` göndermeli
   - Token, `SOCKET_IO_SECRET` ile eşleşmezse bağlantı reddedilir

### Infrastructure Security

3. **Secrets Management**: 
   - Hassas bilgileri `.env` dosyasında tutun ve `.gitignore`'a ekleyin
   - Production secret'ları asla commit etmeyin
   - Secret rotation policy uygulayın

4. **Network Isolation**: 
   - Redis'i sadece internal network'te expose edin (dış port binding yok)
   - API service'i gerektiğinde public expose edin
   - Worker'lar internal-only tutun

5. **Resource Limits**: 
   - Container'lara CPU/Memory limitleri ekleyin
   - OOM (Out of Memory) durumlarına karşı protect edin

6. **Health Checks**: 
   - Tüm servislere health check ekleyin
   - Health endpoint authentication gerektirmez (monitoring için)

7. **Logging & Monitoring**: 
   - Centralized logging (ELK, Loki) kullanın
   - Failed authentication denemelerini log'layın
   - Rate limiting ekleyin

## 📝 Notes

- **Development**: Hot reload için volume mount edilmiş
- **Production**: Volume mount kaldırılmalı, optimize image kullanılmalı
- **Scaling**: Worker'ları ihtiyaca göre scale edin
- **Monitoring**: Prometheus + Grafana eklenebilir
