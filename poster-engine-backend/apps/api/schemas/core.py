from pydantic import BaseModel, Field

class BrandCreate(BaseModel):
    name: str
    industry: str = "beauty"
    colors: list[str] = Field(default_factory=lambda: ["black", "gold", "deep red"])
    fonts: list[str] = Field(default_factory=lambda: ["serif", "modern sans"])
    brand_voice: str = "luxury, premium, trustworthy"

class BrandOut(BrandCreate):
    id: str
    owner_user_id: str
    class Config:
        from_attributes = True

class ProjectCreate(BaseModel):
    brand_id: str
    product_name: str
    campaign_type: str = "luxury_beauty"
    target_customer: str = "women 18-35"
    offer: str = "Inbox chọn màu theo cá tính"

class ProjectOut(ProjectCreate):
    id: str
    owner_user_id: str
    status: str
    class Config:
        from_attributes = True

class VariantOut(BaseModel):
    id: str
    project_id: str
    variant_type: str
    prompt: str
    provider: str
    ctr_score: float
    attention_score: float
    luxury_score: float
    trust_score: float
    product_focus: float
    conversion_score: float
    final_score: float
    status: str
    class Config:
        from_attributes = True

class JobOut(BaseModel):
    id: str
    project_id: str | None = None
    job_type: str
    status: str
    provider: str
    input_json: dict
    output_json: dict
    error_message: str | None = None
    class Config:
        from_attributes = True


class BillingUsageOut(BaseModel):
    id: str
    owner_user_id: str
    brand_id: str | None = None
    project_id: str | None = None
    event_type: str
    units: int
    metadata_json: dict

    class Config:
        from_attributes = True


class DevTokenCreateRequest(BaseModel):
    user_id: str = "dev-user"
    email: str | None = None
    workspace_id: str | None = None
    expires_in_seconds: int = 3600


class DevTokenCreateResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in_seconds: int
