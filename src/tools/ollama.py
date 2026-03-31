"""
Ollama API client — used for cheap/simple tasks and message classification.
"""
import logging
import httpx

log = logging.getLogger(__name__)


class OllamaClient:
    def __init__(self, base_url: str, default_model: str = "llama3.1:8b"):
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model

    async def generate(self, prompt: str, model: str | None = None) -> str:
        model = model or self.default_model
        url = f"{self.base_url}/api/generate"
        payload = {"model": model, "prompt": prompt, "stream": False}
        # Fast connect timeout (5s) so callers don't block when the LLM server is off.
        # Read timeout is generous (120s) because model inference can be slow.
        _timeout = httpx.Timeout(connect=5.0, read=120.0, write=10.0, pool=5.0)
        try:
            async with httpx.AsyncClient(timeout=_timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                return response.json()["response"]
        except Exception as e:
            log.warning("Ollama generate failed (%s): %s", type(e).__name__, e)
            raise

    async def is_available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(f"{self.base_url}/api/tags")
                return r.status_code == 200
        except Exception:
            return False
