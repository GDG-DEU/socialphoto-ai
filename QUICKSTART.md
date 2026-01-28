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
python -m src.workers.analyze_worker
```

## 🧪 Test

### Unit Testler (Pytest)
```bash
# Tüm unit testleri çalıştır
uv run pytest

# Detaylı çıktı
uv run pytest -v

# Coverage raporu ile
uv run pytest --cov=src

# Belirli test sınıfını çalıştır
uv run pytest -k "TestChatEndpoint"
```

### Integration Testler
```bash
# Sunucu çalışırken
source .venv/bin/activate
python tests/integration/test_api.py
```

### API Docs ile Test
Tarayıcıda aç: http://localhost:8000/docs

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

| Endpoint | Method | Açıklama |
|----------|--------|----------|
| `/analyze` | POST | Görsel analiz job'u oluştur (202 Accepted) |
| `/analyze/{job_id}` | GET | Job durumunu sorgula |
| `/sim-search` | POST | Metin/görsel benzerlik araması |
| `/chat` | POST | Agent sohbet |
| `/health` | GET | Servis sağlık durumu |
| `/docs` | GET | Swagger UI |
| `/redoc` | GET | ReDoc API Docs |

## 🏗️ Sistem Mimarisi

```
Client → FastAPI (port 8000) → Redis Queue
                ↓
            Worker → Redis (Results)
                ↓
            Socket.IO → Client (Notifications)
```
