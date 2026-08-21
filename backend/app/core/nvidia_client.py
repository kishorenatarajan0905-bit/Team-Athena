import structlog
from openai import AsyncOpenAI
from app.core.config import settings
from typing import List, Optional, Dict, Any
import json

logger = structlog.get_logger()


class NVIDIAClient:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.nvidia_api_key,
            base_url=settings.nvidia_base_url,
        )
        self.chat_model = settings.nvidia_chat_model
        self.embed_model = settings.nvidia_embed_model

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None,
        tool_choice: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        stream: bool = False,
    ):
        """Call NVIDIA Nemotron chat completion API."""
        try:
            kwargs = {
                "model": self.chat_model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": stream,
            }
            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = tool_choice or "auto"

            response = await self.client.chat.completions.create(**kwargs)
            return response
        except Exception as e:
            logger.error("chat_completion_failed", error=str(e))
            raise

    async def embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using NVIDIA embedding model."""
        try:
            response = await self.client.embeddings.create(
                model=self.embed_model,
                input=texts,
            )
            return [data.embedding for data in response.data]
        except Exception as e:
            logger.error("embeddings_failed", error=str(e), count=len(texts))
            raise

    async def embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        embeddings = await self.embeddings([text])
        return embeddings[0]


nvidia_client = NVIDIAClient()