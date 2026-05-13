from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the customer-risk adapter service."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    service_name: str = "digital-customer-agent-adapter"
    customer_api_base_url: str = "http://customer-data-api:8080"
    customer_api_token: str = ""
    ragflow_base_url: str = "http://ragflow:9380"
    ragflow_api_key: str = ""
    ragflow_dataset_ids: str = ""
    retrieval_top_k: int = 8
    retrieval_similarity_threshold: float = 0.2
    request_timeout_seconds: float = 30.0

    @property
    def dataset_id_list(self) -> list[str]:
        return [item.strip() for item in self.ragflow_dataset_ids.split(",") if item.strip()]


settings = Settings()
