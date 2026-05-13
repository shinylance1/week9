from typing import Any

from pydantic import BaseModel, Field


class CustomerRiskContextRequest(BaseModel):
    customer_id: str | None = Field(default=None, description="Customer ID from CRM or core customer system")
    customer_name: str | None = Field(default=None, description="Customer name when customer_id is unavailable")
    question: str = Field(default="请给出该客户的风险营销建议", description="Original relationship-manager question")


class Citation(BaseModel):
    content: str
    score: float | None = None
    dataset_id: str | None = None
    document_id: str | None = None
    document_name: str | None = None
    page: int | None = None
    section: str | None = None
    location: str | None = None
    source_url: str | None = None


class CustomerRiskContextResponse(BaseModel):
    status: str
    message: str
    customer_profile: dict[str, Any] = Field(default_factory=dict)
    retrieval_queries: list[str] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    prompt_context: str = ""
