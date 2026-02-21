from pydantic import BaseModel, HttpUrl
from typing import Literal, Optional

class AnalyzeRequest(BaseModel):
    post_id: str
    image_url: HttpUrl


class AnalyzeJobResponse(BaseModel):
    job_id: str
    status: Literal["queued"]


class AnalyzeJobStatusResponse(BaseModel):
    job_id: str
    status: Literal["queued", "processing", "completed", "failed"]
    result: Optional[dict] = None
    error: Optional[str] = None

# -------------------------------------------------------------------

class UpsertItem(BaseModel):
    post_id: str
    image_url: HttpUrl

class UpsertRequest(BaseModel):
    items: list[UpsertItem]


class UpsertResponse(BaseModel):
    status: Literal["success", "failed"]
    count: int

# -------------------------------------------------------------------

class DeleteRequest(BaseModel):
    post_id: str


class DeleteResponse(BaseModel):
    status: Literal["success", "failed"]
    vector_id: str

# -------------------------------------------------------------------

class SimSearchRequest(BaseModel):
    query_text: Optional[str] = None
    image_url: Optional[HttpUrl] = None
    top_k: int = 5


class SimSearchResponse(BaseModel):
    results: list[dict]

# -------------------------------------------------------------------

class ChatRequest(BaseModel):
    user_id: str
    message: str
    history: Optional[list[dict]] = None


class Action(BaseModel):
    type: str  # e.g., "search_images", "analyze_photo"
    parameters: dict


class ChatResponse(BaseModel):
    reply: str
    actions: Optional[list[Action]] = None

# -------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: str
    models_loaded: list[str]

# -------------------------------------------------------------------

class NSFWCheckRequest(BaseModel):
    image_url: HttpUrl


class NSFWCheckResponse(BaseModel):
    conf_score: float