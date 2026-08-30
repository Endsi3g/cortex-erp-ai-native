from typing import Any, Dict, Optional

try:
    import httpx
except ImportError:
    httpx = None

from cortex_mcp.config import settings


class FrappeClient:
    """
    HTTP facade to the Cortex Frappe business API.

    SECURITY INVARIANT: the tenant Company is fixed to this MCP service
    account's configured `default_company` (one MCP deployment = one
    Cortex client = one Company, per the pilot isolation model). It is
    never accepted as a per-call argument from a tool caller/agent — an
    LLM tool argument (or an instruction hidden in an ingested document)
    must never be able to redirect a request to another tenant.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
    ):
        self.base_url = (base_url or settings.frappe_url).rstrip("/")
        self.api_key = api_key or settings.frappe_api_key
        self.api_secret = api_secret or settings.frappe_api_secret

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"token {self.api_key}:{self.api_secret}",
            "X-Company-ID": settings.default_company,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def call_method(
        self,
        method_path: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/api/method/{method_path}"
        headers = self._headers()

        if not httpx:
            return {"status": "offline_mode", "simulated": True}

        async with httpx.AsyncClient(timeout=settings.timeout_seconds) as client:
            try:
                if json_data is not None:
                    response = await client.post(url, json=json_data, headers=headers)
                else:
                    response = await client.get(url, params=params, headers=headers)

                if response.status_code == 200:
                    data = response.json()
                    return data.get("message") or data.get("data") or data
                else:
                    return {"status": "error", "code": response.status_code, "text": response.text}
            except Exception as e:
                return {"status": "offline_fallback", "error": str(e)}


client = FrappeClient()
