from pydantic import BaseModel
from typing import Literal, Optional

class AnalyzeRequest(BaseModel):
    post_id: str
    cloudinary_public_id: str


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
    cloudinary_public_id: str

class UpsertRequest(BaseModel):
    items: list[UpsertItem]


class UpsertResponse(BaseModel):
    status: Literal["success", "failed"]
    count: int

# -------------------------------------------------------------------

class DeleteRequest(BaseModel):
    cloudinary_public_id: str


class DeleteResponse(BaseModel):
    status: Literal["success", "failed"]
    cloudinary_public_id: str

# -------------------------------------------------------------------

class SimSearchRequest(BaseModel):
    query_text: Optional[str] = None
    cloudinary_public_id: Optional[str] = None
    top_k: int = 5
    w: float = 0.5


class SimSearchResponse(BaseModel):
    results: list[dict]

# -------------------------------------------------------------------

class ChatRequest(BaseModel):
    user_id: str
    message: str
    history: Optional[list[dict]] = None
    cloudinary_public_id: Optional[str] = None


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
    cloudinary_public_id: str


class NSFWCheckResponse(BaseModel):
    job_id: str
    status: Literal["queued"]