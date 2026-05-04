from fastapi import FastAPI, HTTPException, Depends, Request
from src.models.schemas import *
from src.services.redis_client import redis_client
from src.services.notification_service import notification_service
from src.services.health_service import health_service
from src.services.auth_service import verify_api_key
from src.services.pinecone_service import PineconeService, pinecone_service
from src.services.agent import AgentService, GeminiClient, ToolExecutor
from src.services.agent.tools import SimSearchTool, UserContextTool
from src.services.indexing_service import IndexingService
from src.services.sim_search_service import SimSearchService, init_sim_search_service
from src.services.sim_search.encoder import Encoder
import json
import logging
import uuid
from contextlib import asynccontextmanager
from src.config import get_settings
from src.models.schemas import SimSearchRequest


from typing import Optional
from pydantic import BaseModel
import asyncio


settings = get_settings()
logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize ML + External Services
    try:
        app.state.encoder = await asyncio.to_thread(Encoder)
        app.state.pinecone_service = pinecone_service
        app.state.indexing_service = IndexingService(encoder=app.state.encoder, pc_service=app.state.pinecone_service)
        app.state.sim_search_service = init_sim_search_service(
            encoder=app.state.encoder,
            pc_service=app.state.pinecone_service,
        )
        logger.info("Services and models initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize models/services: {e}")
        raise

    # Startup: Test Redis connection
    try:
        await redis_client.ping()
        logger.info("Redis connected successfully")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        raise
    
    # Register health checks
    health_service.register("redis", redis_client.ping)


    sim_search_tool = SimSearchTool(app.state.sim_search_service)
    user_context_tool = UserContextTool()
    tools = [sim_search_tool, user_context_tool]
    tool_executor = ToolExecutor(tools=tools)

    try:
        gemini_client = GeminiClient(tools=tools)
        app.state.agent_service = AgentService(gemini_client, tool_executor)
        logger.info("Agent service initialized successfully")
    except Exception as e:
        logger.warning(f"Agent service is unavailable: {e}")

    # TODO: Register ML model health checks when implemented
    # health_service.register("clip", clip_model.health_check)
    # health_service.register("aesthetic_scorer", aesthetic_scorer.health_check)
    # health_service.register("tagger", tagger_model.health_check)
    # health_service.register("pinecone", pinecone_client.health_check)
    
    yield
    
    # Shutdown: Close Redis connection
    await redis_client.close()
    logger.info("Redis connection closed")

app = FastAPI(title="AI Service", version="1.0.0", lifespan=lifespan)

# Combine FastAPI and Socket.IO into one ASGI app
combined_app = notification_service.get_asgi_app(app)


# This endpoint has been implemented for manual testing purposes. Originally, jobs are enqueued by backend service.
@app.post("/analyze", response_model=AnalyzeJobResponse, status_code=202)
async def analyze_image(req: AnalyzeRequest, api_key: str = Depends(verify_api_key)):
    try:
        job_id = str(uuid.uuid4())
        job_key = f"analyze_job:{job_id}"

        # job metadata
        await redis_client.hset(
            job_key,
            mapping={
                "job_id": job_id,
                "post_id": req.post_id,
                "cloudinary_public_id": req.cloudinary_public_id,
                "status": "queued"
            }
        )
        await redis_client.expire(job_key, 86400)  # 24 saatlik TTL

        # enqueue job to analyze_queue list
        await redis_client.rpush("analyze_queue", job_id)

        return {"job_id": job_id, "status": "queued"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@app.get("/analyze/{job_id}", response_model=AnalyzeJobStatusResponse)
async def get_analyze_job_status(job_id: str, api_key: str = Depends(verify_api_key)):
    job_key = f"analyze_job:{job_id}"
    job_data = await redis_client.hgetall(job_key)
    if not job_data:
        raise HTTPException(status_code=404, detail="Job not found")

    status = job_data.get("status", "queued")
    error = job_data.get("error")
    result = None
    if status == "completed":
        score = job_data.get("aesthetic_score")
        tags = job_data.get("suggested_tags")
        result = {
            "aesthetic_score": float(score) if score else None,
            "suggested_tags": json.loads(tags) if tags else []
        }
    return {
        "job_id": job_id,
        "status": status,
        "result": result,
        "error": error
    }


@app.post("/upsert", response_model=UpsertResponse)
async def upsert(req: UpsertRequest, request: Request, api_key: str = Depends(verify_api_key)):
    try:
        indexing_service: IndexingService = request.app.state.indexing_service
        return await indexing_service.upsert_items(req.items)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/delete-record", response_model=DeleteResponse)
async def delete_record(req: DeleteRequest, request: Request, api_key: str = Depends(verify_api_key)):
    try:
        pinecone_service: PineconeService = request.app.state.pinecone_service
        cloudinary_public_id = req.cloudinary_public_id
        
        success = await asyncio.to_thread(
            pinecone_service.delete_vector,
            vector_id=cloudinary_public_id,
        )
        
        if success:
            return DeleteResponse(status="success", cloudinary_public_id=cloudinary_public_id)
        else:
            raise HTTPException(status_code=500, detail="Failed to delete from Pinecone")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/sim-search", response_model=SimSearchResponse)
async def similarity_search(req: SimSearchRequest, request: Request, api_key: str = Depends(verify_api_key)):
    """Retrieves similar images based on the provided query_text and/or cloudinary_public_id from Pinecone."""
    if req.query_text is None and req.cloudinary_public_id is None:
        raise HTTPException(status_code=400, detail="At least one of query_text or cloudinary_public_id must be provided")

    try:
        logger.info(f"Received sim search request: {req.model_dump()}")
        sim_search_service: SimSearchService = request.app.state.sim_search_service
        results = await sim_search_service.search(req)
        return results


    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    req: ChatRequest,
    request: Request,
    api_key: str = Depends(verify_api_key),
):
    """Handles chat messages by running the stateless agent loop."""
    try:
        agent_result = await request.app.state.agent_service.run(
            user_id=req.user_id,
            message=req.message,
            history=req.history or [],
            cloudinary_public_id=req.cloudinary_public_id,
        )
        return ChatResponse(reply=agent_result.reply, actions=agent_result.actions)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/nsfw-check", response_model=NSFWCheckResponse)
async def nsfw_check(req: NSFWCheckRequest, request: Request, api_key: str = Depends(verify_api_key)):
    """Checks if an image contains NSFW content and returns confidence score."""
    try:
        logger.info(f"Received NSFW check request for image: {req.cloudinary_public_id}")

        job_id = str(uuid.uuid4())
        job_key = f"nsfw_job:{job_id}"
        await redis_client.hset(
            job_key,
            mapping={
                "job_id": job_id,
                "cloudinary_public_id": req.cloudinary_public_id,
                "status": "queued",
            }
        )
        await redis_client.expire(job_key, 86400)

        # enqueue job to nsfw_queue list
        await redis_client.rpush("nsfw_queue", job_id)

        return {"job_id": job_id, "status": "queued"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Returns the health status of the service and loaded models."""
    status = await health_service.get_status()
    healthy_components = await health_service.get_healthy_components()
    
    return HealthResponse(
        status=status,
        models_loaded=healthy_components
    )
