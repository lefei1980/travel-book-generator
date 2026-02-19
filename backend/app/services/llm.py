import os
import json
import re
import logging
from groq import Groq

logger = logging.getLogger(__name__)

MODEL = "llama-3.3-70b-versatile"

_client: Groq | None = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY environment variable not set")
        _client = Groq(api_key=api_key)
    return _client


CHAT_SYSTEM_PROMPT = """You are a friendly travel planning assistant. Help the user build a complete travel itinerary through natural conversation.

Your goal is to gather enough information to plan a day-by-day trip:
- Trip name and destination(s)
- Travel dates (start date, number of days)
- For each day: the hotel/accommodation (used as start and end location), attractions to visit, and restaurants for meals

Ask clarifying questions when information is missing. Keep responses concise and friendly.
Do NOT output JSON in this stage — respond only in natural conversational text.

When the plan feels reasonably complete, summarize it and let the user know they can click "Finalize Itinerary" to generate their travel guide."""

JSON_SYSTEM_PROMPT = """Extract the travel plan from this conversation and output it as a single JSON object.

Output ONLY the raw JSON. No explanations, no markdown, no code blocks — just the JSON object.

Required schema:
{
  "title": "Descriptive trip title",
  "start_date": "YYYY-MM-DD or null",
  "end_date": "YYYY-MM-DD or null",
  "days": [
    {
      "day_number": 1,
      "start_location": "Hotel or accommodation name",
      "end_location": "Hotel or accommodation name",
      "places": [
        {"name": "Place name", "place_type": "attraction", "city": "City name", "country": "Country name"}
      ]
    }
  ]
}

Rules:
- day_number starts at 1 and increments by 1
- place_type MUST be exactly one of: "attraction", "restaurant", "hotel" — nothing else
- Maximum 5 places per day
- start_location and end_location should be the hotel/accommodation for that night (can be the same value)
- Dates in YYYY-MM-DD format, or null if not mentioned
- If no hotel was mentioned for a day, use the destination city name as start_location and end_location
- city and country MUST be included for every place — use the destination city/country if unsure
- Use the official English name for city and country (e.g., "Paris", "France")"""


def chat_with_llm(messages: list[dict]) -> str:
    """Send conversation messages to Groq and return assistant reply."""
    client = _get_client()
    full_messages = [{"role": "system", "content": CHAT_SYSTEM_PROMPT}] + messages
    response = client.chat.completions.create(
        model=MODEL,
        messages=full_messages,
        temperature=0.7,
        max_tokens=1024,
    )
    return response.choices[0].message.content


def generate_itinerary_json(messages: list[dict]) -> dict:
    """Convert conversation history to a structured itinerary dict."""
    client = _get_client()
    full_messages = (
        [{"role": "system", "content": JSON_SYSTEM_PROMPT}]
        + messages
        + [{"role": "user", "content": "Output the complete itinerary as JSON now."}]
    )
    response = client.chat.completions.create(
        model=MODEL,
        messages=full_messages,
        temperature=0.1,
        max_tokens=2048,
        response_format={"type": "json_object"},
    )
    raw = response.choices[0].message.content
    logger.info(f"LLM JSON raw (first 300 chars): {raw[:300]}")
    return json.loads(_strip_markdown(raw))


def generate_name_variants(place: str, city: str, country: str) -> list[str]:
    """Ask LLM for alternative official names for a place when geocoding fails.
    Returns up to 3 alternative name strings to retry geocoding with."""
    client = _get_client()
    prompt = (
        f'Provide up to 3 alternative official or commonly used names for "{place}" in {city}, {country}. '
        f'Output a JSON array of strings only. Example: ["Alt Name 1", "Alt Name 2", "Alt Name 3"]. '
        f'If you are not sure, return an empty array [].'
    )
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=128,
        )
        raw = response.choices[0].message.content.strip()
        # Extract JSON array from response
        match = re.search(r'\[.*?\]', raw, re.DOTALL)
        if match:
            variants = json.loads(match.group(0))
            return [v for v in variants if isinstance(v, str) and v.strip()]
    except Exception as e:
        logger.warning(f"generate_name_variants failed for '{place}': {e}")
    return []


def _strip_markdown(text: str) -> str:
    """Remove markdown code fences from LLM output if present."""
    text = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        return match.group(1).strip()
    return text
