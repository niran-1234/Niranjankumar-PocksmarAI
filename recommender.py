from urllib.parse import quote_plus


PLATFORM_SEARCH = {
    "Amazon": "https://www.amazon.in/s?k={q}",
    "Flipkart": "https://www.flipkart.com/search?q={q}",
    "IKEA": "https://www.ikea.com/in/en/search/?q={q}",
    "Swiggy": "https://www.swiggy.com/search?query={q}",
    "Zomato": "https://www.zomato.com/search?q={q}",
    "OYO": "https://www.oyorooms.com/search?q={q}",
}


def search_url(platform: str, query: str) -> str:
    template = PLATFORM_SEARCH.get(platform, "https://www.google.com/search?q={q}")
    return template.format(q=quote_plus(query))


def home_fallback(data: dict) -> dict:
    budget = data["budget"]
    rooms = data["rooms"]
    room_count = max(1, len(rooms))
    categories = [
        ("Lighting", "LED ceiling light", max(700, budget // (room_count * 14)), "Amazon"),
        ("Furniture", "Compact accent table", max(1200, budget // (room_count * 8)), "IKEA"),
        ("Decor", "Wall art set", max(600, budget // (room_count * 16)), "Flipkart"),
        ("Comfort", "Cushion set", max(500, budget // (room_count * 18)), "Amazon"),
    ]
    items = []
    for category, name, price, platform in categories:
        items.append({
            "name": name,
            "category": category,
            "estimated_price": int(price),
            "platform": platform,
            "search_url": search_url(platform, name),
            "reason": f"Budget-conscious {data['style']} option suitable for {', '.join(rooms)}.",
            "quantity": 1,
        })
    total = sum(x["estimated_price"] for x in items)
    return {
        "planner": "home",
        "title": "Home Interior Budget Plan",
        "budget": budget,
        "estimated_total": total,
        "remaining_budget": max(0, budget - total),
        "summary": f"A practical {data['style']} starter plan for {', '.join(rooms)}.",
        "budget_breakdown": {"Lighting": int(budget * .20), "Furniture": int(budget * .45), "Decor": int(budget * .20), "Comfort": int(budget * .15)},
        "recommendations": items,
    }


def party_fallback(data: dict) -> dict:
    budget = data["budget"]
    items = [
        ("Catering", f"{data['event_type']} food package", int(budget * .48), "Swiggy"),
        ("Catering", "Alternative restaurant package", int(budget * .08), "Zomato"),
        ("Decoration", "Theme decoration package", int(budget * .18), "Amazon"),
        ("Entertainment", "Basic party sound/decor accessories", int(budget * .12), "Flipkart"),
        ("Venue", f"Event venue near {data['city'] or 'your location'}", int(budget * .10), "OYO"),
    ]
    recs = [{
        "name": name, "category": category, "estimated_price": price, "platform": platform,
        "search_url": search_url(platform, name), "reason": f"Fits the planned {data['guests']}-guest {data['event_type']} budget.",
        "quantity": 1
    } for category, name, price, platform in items]
    total = sum(x["estimated_price"] for x in recs)
    return {
        "planner": "party", "title": "Party Budget Plan", "budget": budget,
        "estimated_total": total, "remaining_budget": max(0, budget-total),
        "summary": f"Starter allocation for {data['guests']} guests.",
        "budget_breakdown": {"Catering": int(budget*.56), "Decoration": int(budget*.18), "Entertainment": int(budget*.12), "Venue": int(budget*.10), "Buffer": int(budget*.04)},
        "recommendations": recs,
    }


def jewelry_fallback(data: dict) -> dict:
    budget = data["budget"]
    items = [
        ("Earrings", "Statement earrings", int(budget*.25), "Amazon"),
        ("Necklace", "Minimal matching necklace", int(budget*.35), "Flipkart"),
        ("Bracelet", "Elegant bracelet", int(budget*.20), "Amazon"),
        ("Set", "Occasion jewelry set", int(budget*.20), "Flipkart"),
    ]
    recs = [{
        "name": name, "category": category, "estimated_price": price, "platform": platform,
        "search_url": search_url(platform, name), "reason": f"Suggested for a {data['occasion']} occasion and {data['style']} style.",
        "quantity": 1
    } for category, name, price, platform in items]
    total = sum(x["estimated_price"] for x in recs)
    return {
        "planner": "jewelry", "title": "Jewelry Budget Plan", "budget": budget,
        "estimated_total": total, "remaining_budget": max(0, budget-total),
        "summary": "Style-oriented jewelry starter options. Uploading an outfit image can improve color/style matching when Gemini is enabled.",
        "budget_breakdown": {"Necklace": int(budget*.35), "Earrings": int(budget*.25), "Bracelet": int(budget*.20), "Set": int(budget*.20)},
        "recommendations": recs,
    }
