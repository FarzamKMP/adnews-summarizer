"""
Gemini client — Vertex AI via service account JSON, or AI Studio via API key.
"""
import logging
import os
from typing import Optional

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

_client: Optional[genai.Client] = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        project = os.getenv("GOOGLE_CLOUD_PROJECT", "")
        location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
        creds_file = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
        api_key = os.getenv("GEMINI_API_KEY", "")

        if project:
            # Vertex AI — credentials loaded automatically from GOOGLE_APPLICATION_CREDENTIALS
            if creds_file:
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_file
            _client = genai.Client(vertexai=True, project=project, location=location)
            logger.info(f"Gemini: Vertex AI (project={project})")
        elif api_key:
            _client = genai.Client(api_key=api_key)
            logger.info("Gemini: AI Studio API key")
        else:
            raise EnvironmentError(
                "Set GOOGLE_CLOUD_PROJECT (Vertex AI) or GEMINI_API_KEY (AI Studio) in .env"
            )
    return _client


def generate(prompt: str, model_name: Optional[str] = None) -> str:
    client = _get_client()
    model = model_name or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    config = types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_budget=0)
    )
    response = client.models.generate_content(model=model, contents=prompt, config=config)
    return response.text.strip()


def embed(text: str) -> list[float]:
    client = _get_client()
    model = os.getenv("GEMINI_EMBEDDING_MODEL", "text-embedding-005")
    result = client.models.embed_content(model=model, contents=text)
    return result.embeddings[0].values


def embed_query(text: str) -> list[float]:
    return embed(text)
