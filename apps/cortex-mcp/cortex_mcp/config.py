import os

try:
    from pydantic import BaseModel, Field
except ImportError:
    class BaseModel:
        def __init__(self, **data):
            for k, v in data.items():
                setattr(self, k, v)

    def Field(*args, default=None, default_factory=None, **kwargs):
        if default_factory is not None:
            return default_factory()
        return default


class Settings(BaseModel):
    frappe_url: str = os.getenv("FRAPPE_URL", os.getenv("CORTEX_API_BASE_URL", "http://localhost:8000"))
    frappe_api_key: str = os.getenv("FRAPPE_API_KEY", "dev_api_key_123")
    frappe_api_secret: str = os.getenv("FRAPPE_API_SECRET", "dev_api_secret_456")
    default_company: str = os.getenv("CORTEX_COMPANY", "CineRental Montreal")
    mcp_port: int = int(os.getenv("PORT", "3100"))
    timeout_seconds: float = 15.0


settings = Settings()
