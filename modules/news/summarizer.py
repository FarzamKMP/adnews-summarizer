import logging
import re

from modules.ai import gemini_client
from modules.ai.prompt_templates import NEWS_SUMMARIZATION, MULTI_NEWS_SYNTHESIS

logger = logging.getLogger(__name__)


def summarize_article(text: str) -> str:
    """Summarise a single article using Gemini, with a text-based fallback."""
    text = text.strip()
    if not text:
        return ""
    try:
        prompt = NEWS_SUMMARIZATION.format(text=text[:4000])
        return gemini_client.generate(prompt)
    except Exception as e:
        logger.warning(f"Gemini summarization failed: {e}")
        sentences = re.split(r"(?<=[.!?])\s+", text)
        return " ".join(sentences[:3])[:800]


def synthesize_news(summaries_with_titles: list[dict]) -> str:
    """
    Given a list of {title, summary, url} dicts, return a trend/insight analysis.
    """
    if not summaries_with_titles:
        return ""
    formatted = "\n\n".join(
        f"[{i+1}] {item['title']}\n{item['summary']}"
        for i, item in enumerate(summaries_with_titles)
    )
    try:
        prompt = MULTI_NEWS_SYNTHESIS.format(
            count=len(summaries_with_titles),
            summaries=formatted,
        )
        return gemini_client.generate(prompt)
    except Exception as e:
        logger.warning(f"Synthesis failed: {e}")
        return "Analysis unavailable."
