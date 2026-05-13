from typing import Any

import httpx

from .config import settings


async def fetch_customer_profile(customer_id: str | None, customer_name: str | None) -> dict[str, Any]:
    headers = {}
    if settings.customer_api_token:
        headers["Authorization"] = f"Bearer {settings.customer_api_token}"

    params = {}
    if customer_id:
        params["customer_id"] = customer_id
    if customer_name:
        params["customer_name"] = customer_name

    async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
        response = await client.get(
            f"{settings.customer_api_base_url.rstrip('/')}/api/v1/customer/profile",
            headers=headers,
            params=params,
        )
        response.raise_for_status()
        return response.json()
