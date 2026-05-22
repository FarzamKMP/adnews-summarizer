import logging

from modules.ai import gemini_client
from modules.ai.prompt_templates import LINKEDIN_ARTICLE_GENERATION

logger = logging.getLogger(__name__)


def generate_linkedin_article(
    keywords: list[str],
    summaries_with_meta: list[dict],
    analysis: str,
) -> str:
    """
    Generate a publish-ready LinkedIn article.

    summaries_with_meta: list of {title, summary, url, source}
    """
    if not summaries_with_meta:
        return "No news articles found for the given keywords."

    summaries_text = "\n\n".join(
        f"• {item['title']}\n  {item['summary']}"
        for item in summaries_with_meta
    )
    sources_text = "\n".join(
        f"- {item['title']} ({item['source']}): {item['url']}"
        for item in summaries_with_meta
    )

    try:
        prompt = LINKEDIN_ARTICLE_GENERATION.format(
            keywords=", ".join(keywords),
            summaries=summaries_text,
            analysis=analysis,
            sources=sources_text,
        )
        return gemini_client.generate(prompt)
    except Exception as e:
        logger.error(f"LinkedIn article generation failed: {e}")
        raise
