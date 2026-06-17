import os
os.environ["GOOGLE_API_USE_CLIENT_CERTIFICATE"] = "false"
os.environ["GOOGLE_API_USE_MTLS"] = "never"

from functools import lru_cache

try:
    from pydantic_settings import BaseSettings
except Exception:  # pragma: no cover
    from pydantic import BaseSettings  # type: ignore


class Settings(BaseSettings):
    USE_BQ: bool = False
    GOOGLE_CLOUD_PROJECT: str = "raves-altostrat"
    GCP_REGION: str = "us-central1"
    BQ_LOCATION: str = "us-central1"
    BQ_CONNECTION: str = "us-central1.vertex_conn"
    BQ_DATASET: str = "FSI_POV"
    GCS_BUCKET: str = "fsi_pov"
    GEMINI_MODEL: str = "gemini-2.5-flash"
    EMBEDDING_MODEL: str = "text-embedding-005"
    # BigQuery Conversational Analytics (Gemini Data Analytics) data agent
    CA_AGENT_ID: str = "agent_a61c018d-fc8f-45b1-ad42-2f70f83cd597"
    CA_LOCATION: str = "us"
    BANK_LOGO_PATH: str = ""
    # Google Cloud Data Engineering Agent (real A2A agent operating on a Dataform workspace)
    USE_DE_AGENT: bool = True
    DE_AGENT_LOCATION: str = "us-central1"
    DATAFORM_REPO: str = "fsi_pov_pipeline"
    DATAFORM_WORKSPACE: str = "dev"
    PORT: int = 8080

    class Config:
        env_file = ".env"
        extra = "ignore"

    @property
    def ds(self) -> str:
        return f"`{self.GOOGLE_CLOUD_PROJECT}.{self.BQ_DATASET}`"

    def t(self, name: str) -> str:
        return f"`{self.GOOGLE_CLOUD_PROJECT}.{self.BQ_DATASET}.{name}`"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
