"""AI-powered report analysis using Venice.ai (OpenAI-compatible API)."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

import httpx

from commontrust_bot.config import settings

logger = logging.getLogger(__name__)

VENICE_API_URL = "https://api.venice.ai/api/v1/chat/completions"

SYSTEM_PROMPT = (
    "You are a trust and safety analyst for a peer-to-peer trading community on Telegram. "
    "Your job is to evaluate scam reports submitted by community members. "
    "Be fair and evidence-based. Consider the reporter's and reported user's track records. "
    "Deal-linked reports carry more weight than open reports. "
    "Respond with JSON only — no markdown fences, no explanation outside the JSON."
)

ANALYSIS_TEMPLATE = """\
Analyze this scam report from a P2P trading community.

REPORTER:
- Display name: {reporter_name}
- Verified deals: {reporter_deals}
- Average rating: {reporter_rating}

REPORTED USER:
- Display name: {reported_name}
- Verified deals: {reported_deals}
- Average rating: {reported_rating}
- Prior reports against them: {prior_reports}

{deal_context}

REPORT DESCRIPTION:
{description}

{forwarded_section}

EVIDENCE FILES: {photo_count} screenshot(s) attached (admin will review visuals)

Respond with this exact JSON structure:
{{
  "severity": <1-10 integer, 10 = clear scam with strong evidence>,
  "summary": "<2-3 sentence summary>",
  "recommendation": "<ban|warn|dismiss>",
  "reasoning": "<detailed explanation>",
  "red_flags": ["<flag1>", "<flag2>"]
}}"""


@dataclass
class AIReviewResult:
    severity: int = 5
    summary: str = ""
    recommendation: str = "warn"
    reasoning: str = ""
    red_flags: list[str] = field(default_factory=list)
    model_used: str = ""


async def analyze_report(
    *,
    description: str,
    reporter_name: str = "Unknown",
    reporter_deals: int = 0,
    reporter_rating: float = 0.0,
    reported_name: str = "Unknown",
    reported_deals: int = 0,
    reported_rating: float = 0.0,
    prior_reports: int = 0,
    deal_description: str | None = None,
    forwarded_messages: list[dict] | None = None,
    photo_count: int = 0,
) -> AIReviewResult:
    """Run AI analysis on a report via Venice.ai. Returns a result even if the call fails."""
    if not settings.venice_api_key:
        return AIReviewResult(
            summary="AI analysis unavailable (no VENICE_API_KEY configured).",
            model_used="none",
        )

    prompt = _build_prompt(
        description=description,
        reporter_name=reporter_name,
        reporter_deals=reporter_deals,
        reporter_rating=reporter_rating,
        reported_name=reported_name,
        reported_deals=reported_deals,
        reported_rating=reported_rating,
        prior_reports=prior_reports,
        deal_description=deal_description,
        forwarded_messages=forwarded_messages,
        photo_count=photo_count,
    )

    model = settings.ai_model or "llama-3.3-70b"
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                VENICE_API_URL,
                headers={
                    "Authorization": f"Bearer {settings.venice_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.1,
                },
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            return _parse_response(content, model)
    except Exception as e:
        logger.error("Venice.ai report analysis failed: %s", e)
        return AIReviewResult(
            summary=f"AI analysis failed: {e}",
            model_used=model,
        )


def _build_prompt(
    *,
    description: str,
    reporter_name: str,
    reporter_deals: int,
    reporter_rating: float,
    reported_name: str,
    reported_deals: int,
    reported_rating: float,
    prior_reports: int,
    deal_description: str | None,
    forwarded_messages: list[dict] | None,
    photo_count: int,
) -> str:
    deal_context = ""
    if deal_description:
        deal_context = f"LINKED DEAL (higher weight):\n- Description: {deal_description}"
    else:
        deal_context = "TYPE: Open report (no linked deal)"

    forwarded_section = ""
    if forwarded_messages:
        lines = [f"FORWARDED MESSAGES ({len(forwarded_messages)}):"]
        for i, msg in enumerate(forwarded_messages, 1):
            lines.append(f"  [{i}] From: {msg.get('from_name', 'Unknown')}")
            lines.append(f"      Date: {msg.get('date', 'Unknown')}")
            lines.append(f"      Text: {msg.get('text', '(no text)')}")
        forwarded_section = "\n".join(lines)
    else:
        forwarded_section = "FORWARDED MESSAGES: None"

    return ANALYSIS_TEMPLATE.format(
        reporter_name=reporter_name,
        reporter_deals=reporter_deals,
        reporter_rating=f"{reporter_rating:.1f}",
        reported_name=reported_name,
        reported_deals=reported_deals,
        reported_rating=f"{reported_rating:.1f}",
        prior_reports=prior_reports,
        deal_context=deal_context,
        description=description,
        forwarded_section=forwarded_section,
        photo_count=photo_count,
    )


def _parse_response(text: str, model: str) -> AIReviewResult:
    """Parse AI JSON response with fallback for markdown-fenced output."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        cleaned = "\n".join(lines).strip()
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning("AI returned unparseable response: %s", text[:200])
        return AIReviewResult(
            summary=f"AI response could not be parsed. Raw: {text[:300]}",
            model_used=model,
        )
    return AIReviewResult(
        severity=int(data.get("severity", 5)),
        summary=str(data.get("summary", "")),
        recommendation=str(data.get("recommendation", "warn")),
        reasoning=str(data.get("reasoning", "")),
        red_flags=list(data.get("red_flags", [])),
        model_used=model,
    )
