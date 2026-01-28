# AI Service - Docker Deployment Guide

## 🐳 Quick Start

### Tüm Servisleri Başlat (Tek Komut)

```bash
cd docker
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

`.env` dosyası oluşturun (`.env.example` dosyasını kopyalayın):

```bash
cp .env.example .env
```

Sonra düzenleyin:

```env
REDIS_HOST=redis
REDIS_PORT=6379
LOG_LEVEL=INFO
```

### Worker Sayısını Değiştir

```bash
# 5 worker başlat
docker-compose up -d --scale worker=5

# 1 worker'a düşür
docker-compose up -d --scale worker=1
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

# Health check
curl http://localhost:8000/docs

# Test job oluştur
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"post_id": "test123", "image_url": "https://example.com/image.jpg"}'
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

### Production ortamı için değişiklikler:

**docker-compose.prod.yml:**

```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    restart: always
    volumes:
      - redis_data:/data
    # Port expose etme (güvenlik)
    # ports kaldırıldı

  api:
    build:
      context: ..
      dockerfile: docker/Dockerfile
    command: uv run uvicorn app:combined_app --host 0.0.0.0 --port 8000 --workers 4
    restart: always
    environment:
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - LOG_LEVEL=WARNING
    # Hot reload volume'ünü kaldır
    # volumes kaldırıldı

  worker:
    build:
      context: ..
      dockerfile: docker/Dockerfile
    command: uv run python -m src.workers.analyze_worker
    restart: always
    environment:
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - LOG_LEVEL=WARNING
    deploy:
      replicas: 5  # Production'da daha fazla worker
```

**Kullanım:**

```bash
cd docker
docker-compose -f docker-compose.prod.yml up -d
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

1. **Secrets Management**: Hassas bilgileri `.env` dosyasında tutun ve `.gitignore`'a ekleyin
2. **Network Isolation**: Redis'i sadece internal network'te expose edin
3. **Resource Limits**: Container'lara CPU/Memory limitleri ekleyin
4. **Health Checks**: Tüm servislere health check ekleyin
5. **Logging**: Centralized logging (ELK, Loki) kullanın

## 📝 Notes

- **Development**: Hot reload için volume mount edilmiş
- **Production**: Volume mount kaldırılmalı, optimize image kullanılmalı
- **Scaling**: Worker'ları ihtiyaca göre scale edin
- **Monitoring**: Prometheus + Grafana eklenebilir
