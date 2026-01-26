# AI Service - Quick Start Guide

## 📚 Manuel Başlatma

Eğer servisleri tek tek başlatmak isterseniz:

### 1. Redis
```bash
redis-server --daemonize yes
redis-cli ping  # Test
```

### 2. API Server
```bash
source .venv/bin/activate
python main.py
```

### 3. Worker (Yeni terminal)
```bash
source .venv/bin/activate
python analyze_worker.py
```

## 🧪 Test

### API Docs ile Test
Tarayıcıda aç: http://localhost:8000/docs

### Test Script ile
```bash
source .venv/bin/activate
python test_api.py
```

### Curl ile
```bash
# Job oluştur
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"post_id": "test123", "image_url": "https://example.com/image.jpg"}'

# Job durumunu kontrol et
curl http://localhost:8000/analyze/{job_id}
```

## 📋 Servis Durumunu Kontrol

```bash
# Redis kontrolü
redis-cli ping

# API Server kontrolü
curl http://localhost:8000/docs

# Process kontrolü
ps aux | grep -E "redis-server|main.py|analyze_worker"
```

## 🐛 Sorun Giderme

### Port zaten kullanımda
```bash
# 8000 portunu kullanan process'i bul
lsof -i :8000

# Process'i durdur
kill -9 <PID>
```

### Redis bağlanamıyor
```bash
# Redis'i yeniden başlat
redis-cli shutdown
redis-server --daemonize yes
```

### Worker job almıyor
```bash
# Redis queue'yu kontrol et
redis-cli llen analyze_queue
redis-cli lrange analyze_queue 0 -1
```

## 🔗 API Endpoints

- `POST /analyze` - Görsel analiz job'u oluştur (202 Accepted)
- `GET /analyze/{job_id}` - Job durumunu sorgula
- `GET /docs` - Swagger UI
- `GET /redoc` - ReDoc API Docs

## 🏗️ Sistem Mimarisi

```
Client → FastAPI (port 8000) → Redis Queue
                ↓
            Worker → Redis (Results)
                ↓
            Socket.IO → Client (Notifications)
```
