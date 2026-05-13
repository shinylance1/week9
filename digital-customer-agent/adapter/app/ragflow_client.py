from typing import Any

import httpx

from .config import settings
from .models import Citation


def build_retrieval_queries(customer_profile: dict[str, Any], question: str) -> list[str]:
    basic_info = customer_profile.get("basic_info", {})
    quant_profile = customer_profile.get("quant_profile", {})
    industry_name = basic_info.get("industry_name", "")
    industry_tags = " ".join(basic_info.get("industry_tags", []))
    risk_level = quant_profile.get("risk_level", "")
    risk_tags = " ".join(customer_profile.get("risk_tags", []))
    marketing_tags = " ".join(customer_profile.get("marketing_tags", []))

    return [
        f"{industry_name} {industry_tags} 行业特征 行业周期 授信策略 风险特征 营销策略 {question}".strip(),
        f"{industry_name} {risk_level} {risk_tags} 风控政策 授信准入 司法风险 征信风险 担保风险".strip(),
        f"{industry_name} {marketing_tags} {risk_level} 营销产品 结算 票据 供应链金融 现金管理 合规话术".strip(),
    ]


def _normalize_chunk(chunk: dict[str, Any]) -> Citation:
    metadata = chunk.get("metadata") or {}
    return Citation(
        content=str(chunk.get("content") or chunk.get("text") or ""),
        score=chunk.get("similarity") or chunk.get("score"),
        dataset_id=chunk.get("dataset_id") or metadata.get("dataset_id"),
        document_id=chunk.get("document_id") or metadata.get("document_id"),
        document_name=chunk.get("document_name") or metadata.get("document_name") or metadata.get("name"),
        page=chunk.get("page") or metadata.get("page"),
        section=chunk.get("section") or metadata.get("section"),
        location=chunk.get("location") or metadata.get("location"),
        source_url=chunk.get("url") or metadata.get("source_url"),
    )


async def retrieve_from_ragflow(queries: list[str]) -> list[Citation]:
    if not settings.ragflow_api_key:
        return []

    headers = {"Authorization": f"Bearer {settings.ragflow_api_key}"}
    citations: list[Citation] = []

    async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
        for query in queries:
            payload: dict[str, Any] = {
                "question": query,
                "top_k": settings.retrieval_top_k,
                "similarity_threshold": settings.retrieval_similarity_threshold,
            }
            if settings.dataset_id_list:
                payload["dataset_ids"] = settings.dataset_id_list

            response = await client.post(
                f"{settings.ragflow_base_url.rstrip('/')}/api/v1/retrieval",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            body = response.json()
            data = body.get("data", body)
            chunks = data.get("chunks") if isinstance(data, dict) else data
            if isinstance(chunks, list):
                citations.extend(_normalize_chunk(chunk) for chunk in chunks if isinstance(chunk, dict))

    deduped: list[Citation] = []
    seen: set[tuple[str | None, str]] = set()
    for citation in citations:
        key = (citation.document_id, citation.content[:120])
        if citation.content and key not in seen:
            deduped.append(citation)
            seen.add(key)

    return deduped[: settings.retrieval_top_k]
