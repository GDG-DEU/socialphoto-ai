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


class SimSearchRequest(BaseModel):
    query_text: Optional[str] = None
    image_url: Optional[HttpUrl] = None
    top_k: int = 5


class SimSearchResponse(BaseModel):
    results: list[dict]