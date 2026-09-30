import json
from typing import Any
from app.config import get_settings
from app.services.recommender import home_fallback, party_fallback, jewelry_fallback

settings = get_settings()


class GeminiService:
    def __init__(self):
        self.enabled = bool(settings.gemini_api_key.strip())
        self.client = None
        self.types = None
        if self.enabled:
            from google import genai
            from google.genai import types
            self.client = genai.Client(api_key=settings.gemini_api_key)
            self.types = types

    def _schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "planner": {"type": "string"},
                "title": {"type": "string"},
                "budget": {"type": "integer"},
                "estimated_total": {"type": "integer"},
                "remaining_budget": {"type": "integer"},
                "summary": {"type": "string"},
                "budget_breakdown": {"type": "object", "additionalProperties": {"type": "integer"}},
                "recommendations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "category": {"type": "string"},
                            "estimated_price": {"type": "integer"},
                            "platform": {"type": "string"},
                            "search_url": {"type": "string"},
                            "reason": {"type": "string"},
                            "quantity": {"type": "integer"},
                        },
                        "required": ["name", "category", "estimated_price", "platform", "search_url", "reason", "quantity"],
                    },
                },
            },
            "required": ["planner", "title", "budget", "estimated_total", "remaining_budget", "summary", "budget_breakdown", "recommendations"],
        }

    def _prompt(self, planner: str, data: dict, image_note: str = "") -> str:
        return f"""
You are PocketSmart AI, a careful budget planning assistant.
Planner: {planner}
User data:
{json.dumps(data, ensure_ascii=False, indent=2)}
{image_note}

Return ONLY valid JSON matching the supplied schema.
Rules:
1. Never exceed the user's total budget in estimated_total.
2. Prices are estimates, not verified live prices.
3. Recommend practical categories and explain each choice briefly.
4. Use only platform names from Amazon, Flipkart, IKEA, Swiggy, Zomato, OYO when relevant.
5. search_url must be a normal public search URL for the named platform; do not invent a specific product listing URL.
6. Do not claim that you queried a retailer API.
7. For jewelry, use the outfit image only for broad color/style coordination.
"""

    def generate(self, planner: str, data: dict, image_bytes: bytes | None = None, mime_type: str | None = None) -> tuple[dict, bool]:
        if not self.enabled:
            return self._fallback(planner, data), False

        contents: list[Any] = [self._prompt(planner, data, "An outfit image is attached." if image_bytes else "")]
        if image_bytes and mime_type:
            contents.append(self.types.Part.from_bytes(data=image_bytes, mime_type=mime_type))

        try:
            response = self.client.models.generate_content(
                model=settings.gemini_model,
                contents=contents,
                config=self.types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=self._schema(),
                    temperature=0.4,
                    max_output_tokens=3000,
                ),
            )
            raw = response.text
            result = json.loads(raw)
            result = self._normalize(result, data)
            return result, True
        except Exception:
            return self._fallback(planner, data), False

    def _fallback(self, planner: str, data: dict) -> dict:
        if planner == "home":
            return home_fallback(data)
        if planner == "party":
            return party_fallback(data)
        return jewelry_fallback(data)

    def _normalize(self, result: dict, data: dict) -> dict:
        budget = int(data["budget"])
        recs = []
        total = 0
        for item in result.get("recommendations", []):
            price = max(0, int(item.get("estimated_price", 0)))
            qty = max(1, int(item.get("quantity", 1)))
            line_total = price * qty
            if total + line_total > budget:
                continue
            item["estimated_price"] = price
            item["quantity"] = qty
            recs.append(item)
            total += line_total
        result["budget"] = budget
        result["estimated_total"] = total
        result["remaining_budget"] = max(0, budget - total)
        result["recommendations"] = recs
        return result
