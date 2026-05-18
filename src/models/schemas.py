from pydantic import BaseModel, Field
from typing import Literal, Optional

class AnalyzeRequest(BaseModel):
    post_id: str
    cloudinary_public_id: str
    language: Optional[str] = "en"


class AestheticMetrics(BaseModel):
    overall_score: float = Field(ge=0.0, le=10.0)
    technical_quality: float = Field(ge=0.0, le=1.0)
    lighting_score: float = Field(ge=0.0, le=1.0)
    composition_score: float = Field(ge=0.0, le=1.0)

class CompositionDetails(BaseModel):
    rule_of_thirds: float = Field(ge=0.0, le=1.0)
    symmetry: float = Field(ge=0.0, le=1.0)
    depth_of_field: str = Field(description="1-2 words")
    balance: str = Field(description="1-2 words")

class VisualCharacteristics(BaseModel):
    contrast: float = Field(ge=0.0, le=1.0)
    saturation: float = Field(ge=0.0, le=1.0)
    sharpness: float = Field(ge=0.0, le=1.0)
    exposure: str = Field(description="1-2 words")

class Metrics(BaseModel):
    aesthetic: AestheticMetrics
    composition_details: CompositionDetails
    visual_characteristics: VisualCharacteristics

class ColorProfile(BaseModel):
    dominant_colors: list[str] = Field(description="max 3 HEX")
    color_harmony: str = Field(description="1-2 words")
    vibrancy: float = Field(ge=0.0, le=1.0)

class SemanticAnalysis(BaseModel):
    tags: list[str] = Field(description="1-3 tags, lowercase, no #")
    scene_type: str = Field(description="1-3 words")
    mood: str = Field(description="1-2 words")

class AIFeedback(BaseModel):
    short_critique: str = Field(description="1 short sentence") 
    improvement_tips: list[str] = Field(description="0-3 tips, only focus on photographic technique/lighting/composition/editing")

class AnalyzeResult(BaseModel):
    metrics: Metrics
    color_profile: ColorProfile
    semantic_analysis: SemanticAnalysis
    ai_feedback: AIFeedback


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
    status: Literal["queued", "completed", "failed"]
    nsfw_score: Optional[float] = None
    error: Optional[str] = None