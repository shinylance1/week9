from typing import Any

from fastapi import FastAPI, HTTPException

from .config import settings
from .customer_client import fetch_customer_profile
from .models import CustomerRiskContextRequest, CustomerRiskContextResponse
from .ragflow_client import build_retrieval_queries, retrieve_from_ragflow

app = FastAPI(title=settings.service_name)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.post("/api/v1/customer-risk-context", response_model=CustomerRiskContextResponse)
async def customer_risk_context(request: CustomerRiskContextRequest) -> CustomerRiskContextResponse:
    if not request.customer_id and not request.customer_name:
        raise HTTPException(status_code=400, detail="customer_id or customer_name is required")

    customer_profile = await fetch_customer_profile(request.customer_id, request.customer_name)
    basic_info: dict[str, Any] = customer_profile.get("basic_info", {})
    industry_code = basic_info.get("industry_code")
    industry_name = basic_info.get("industry_name")

    if not industry_code or not industry_name:
        return CustomerRiskContextResponse(
            status="missing_industry",
            message="客户数据 API 未返回行业编码或行业名称，无法生成行业化风控营销建议。",
            customer_profile=customer_profile,
        )

    queries = build_retrieval_queries(customer_profile, request.question)
    citations = await retrieve_from_ragflow(queries)

    if not citations:
        return CustomerRiskContextResponse(
            status="no_evidence",
            message="RAGFlow 未检索到足够知识库依据，请补充行业策略、风控政策或营销规则后再生成建议。",
            customer_profile=customer_profile,
            retrieval_queries=queries,
        )

    prompt_context = build_prompt_context(customer_profile, citations)
    return CustomerRiskContextResponse(
        status="ok",
        message="已生成客户数据与知识库引用上下文。",
        customer_profile=customer_profile,
        retrieval_queries=queries,
        citations=citations,
        prompt_context=prompt_context,
    )


def build_prompt_context(customer_profile: dict[str, Any], citations: list[Any]) -> str:
    citation_lines = []
    for index, citation in enumerate(citations, start=1):
        location = citation.location or citation.section or (f"第{citation.page}页" if citation.page else "未知位置")
        citation_lines.append(
            f"[{index}] 文档={citation.document_name or '未知文档'}; 位置={location}; 分数={citation.score}; 内容={citation.content}"
        )

    return "\n".join(
        [
            "你是数字客户智能体。客户行业必须以客户数据 API 返回字段为准，不得自行识别行业。",
            "请基于客户数据和以下引用依据，输出客户风险营销建议、禁止动作、客户经理行动清单和合规话术。",
            f"客户数据：{customer_profile}",
            "知识库引用：",
            *citation_lines,
        ]
    )
