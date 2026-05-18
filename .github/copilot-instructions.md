# Project Memory Bank: AI Service (Python/FastAPI)

## Project Architecture
- This is a **Multi-repo** project. 
- This specific repository is the **AI Service**.
- Main Backend: Node.js (located in a sibling repo).
- Communication: REST API with an internal Secret Key.

## Tech Stack
- Framework: FastAPI (Python 3.12), served as a combined ASGI app with Socket.IO.
- Credential Management: Environment variables via Pydantic Settings in `src/config.py` (loads `.env`).
- Database: PostgreSQL (Managed by Node.js, we only read/write specific AI fields).
- Vector DB: Pinecone (used for image similarity search via encoder + fusion pipeline).
- Queue: Redis — background job queues consumed by worker processes.
- ML: PyTorch + Transformers (NSFW detection, image encoding).
- Real-time: Socket.IO (push notifications to clients).

## Architecture Patterns
- **Worker pattern**: Workers run as separate processes, consuming jobs from Redis queues via `blpop`.
- **Service layer**: All business logic lives in `src/services/`; route handlers stay thin.
- **Combined ASGI app**: FastAPI and Socket.IO are mounted together in `app.py`.

## Coding Standards
- Use **Pydantic** for all request/response models, settings, environment variables.
- Implement **Type Hinting** for all function signatures.
- Prefer **async def** for all I/O-bound operations.
- Follow standard software design principles (SOLID, DRY, KISS, separation of concerns).