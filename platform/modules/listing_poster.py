"""
Janovum Module — Listing Auto-Poster (Real Estate)
Client sends a Telegram message like "List 123 Main St for $150k, 3 bed 2 bath"
and it automatically creates a formatted website listing.

How it works:
  1. Client sends Telegram message with property details
  2. Python bot catches it (free)
  3. Sends to Claude to parse details and format listing (pennies)
  4. Python generates the HTML listing page
  5. Sends confirmation back to client
  6. Done

Requirements:
  Works with telegram_bot module for input
  Client config needs: output_dir for listings, client branding info
"""

import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.engine import quick_ask

MODULE_NAME = "listing_poster"
MODULE_DESC = "Listing Auto-Poster — Telegram message to website listing instantly"


def parse_listing_message(message, client_config):
    """
    Use Claude to parse a natural language listing message into structured data.
    e.g., "List 123 Main St for $150k, 3 bed 2 bath, new kitchen"
    """
    prompt = f"""Parse this real estate listing message into structured data.

Message: "{message}"

Return ONLY valid JSON with these fields:
{{
  "address": "full address",
  "price": 150000,
  "beds": 3,
  "baths": 2,
  "sqft": 0,
  "description": "any extra details mentioned",
  "features": ["feature1", "feature2"]
}}

If a field isn't mentioned, use 0 for numbers and "" for strings.
For price, convert shorthand (150k = 150000, 1.2m = 1200000).
Return ONLY the JSON, nothing else."""

    result = quick_ask(prompt)

    if "[ERROR]" in result:
        return {"error": result}

    try:
        # Try to extract JSON from response
        text = result.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text.strip())
    except json.JSONDecodeError:
        return {"error": f"Couldn't parse listing data. Claude said: {result[:200]}"}


def generate_listing_description(listing_data, client_config):
    """Use Claude to write a professional listing description."""
    client_name = client_config.get("client_name", "")

    prompt = f"""Write a professional real estate listing description for {client_name}.

Property: {listing_data.get('address', '')}
Price: ${listing_data.get('price', 0):,.0f}
Beds: {listing_data.get('beds', 0)} | Baths: {listing_data.get('baths', 0)}
Sq Ft: {listing_data.get('sqft', 'N/A')}
Details: {listing_data.get('description', '')}
Features: {', '.join(listing_data.get('features', []))}

Write 2-3 paragraphs. Professional, enticing, accurate. Don't exaggerate.
End with a call to action to schedule a showing."""

    return quick_ask(prompt, system_prompt=f"You are a real estate copywriter for {client_name}.")


def create_listing_html(listing_data, description, client_config):
    """Generate an HTML listing page."""
    client_name = client_config.get("client_name", "")
    client_phone = client_config.get("phone", "")
    client_email = client_config.get("email", "")
    price = listing_data.get("price", 0)
    address = listing_data.get("address", "Property")
    beds = listing_data.get("beds", 0)
    baths = listing_data.get("baths", 0)
    sqft = listing_data.get("sqft", 0)
    features = listing_data.get("features", [])

    features_html = "".join(f"<li>{f}</li>" for f in features) if features else ""
    sqft_display = f"{sqft:,}" if sqft else "N/A"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{address} — ${price:,.0f} | {client_name}</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: 'Segoe UI', sans-serif; background: #0a0a0a; color: #e0e0e0; }}
  .header {{ background: #111; padding: 16px 24px; border-bottom: 1px solid #222; }}
  .header h3 {{ background: linear-gradient(135deg, #ff6b35, #f7c948); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
  .listing {{ max-width: 800px; margin: 30px auto; padding: 0 20px; }}
  .price {{ font-size: 2.2em; font-weight: 700; color: #00c853; margin-bottom: 4px; }}
  .address {{ font-size: 1.3em; color: #ccc; margin-bottom: 16px; }}
  .stats {{ display: flex; gap: 20px; margin-bottom: 24px; flex-wrap: wrap; }}
  .stat {{ background: #141414; border: 1px solid #222; border-radius: 8px; padding: 12px 20px; text-align: center; }}
  .stat-num {{ font-size: 1.4em; font-weight: 700; color: #f7c948; }}
  .stat-label {{ font-size: 0.8em; color: #888; }}
  .desc {{ line-height: 1.8; color: #bbb; margin-bottom: 24px; white-space: pre-line; }}
  .features {{ margin-bottom: 24px; }}
  .features h3 {{ color: #f7c948; margin-bottom: 10px; }}
  .features li {{ margin-left: 20px; margin-bottom: 6px; color: #aaa; }}
  .contact {{ background: #141414; border: 1px solid #222; border-radius: 10px; padding: 20px; text-align: center; }}
  .contact h3 {{ color: #f7c948; margin-bottom: 8px; }}
  .contact p {{ color: #888; }}
  .contact a {{ color: #29b6f6; text-decoration: none; }}
  .footer {{ text-align: center; padding: 20px; color: #333; font-size: 0.8em; margin-top: 40px; }}
</style>
</head>
<body>
<div class="header"><h3>{client_name}</h3></div>
<div class="listing">
  <div class="price">${price:,.0f}</div>
  <div class="address">{address}</div>

  <div class="stats">
    <div class="stat"><div class="stat-num">{beds}</div><div class="stat-label">Bedrooms</div></div>
    <div class="stat"><div class="stat-num">{baths}</div><div class="stat-label">Bathrooms</div></div>
    <div class="stat"><div class="stat-num">{sqft_display}</div><div class="stat-label">Sq Ft</div></div>
  </div>

  <div class="desc">{description}</div>

  {"<div class='features'><h3>Features</h3><ul>" + features_html + "</ul></div>" if features_html else ""}

  <div class="contact">
    <h3>Schedule a Showing</h3>
    <p>{client_name}</p>
    {"<p>" + client_phone + "</p>" if client_phone else ""}
    {"<p><a href='mailto:" + client_email + "'>" + client_email + "</a></p>" if client_email else ""}
  </div>
</div>
<div class="footer">Listed by {client_name} | Powered by Janovum | {datetime.now().strftime('%B %d, %Y')}</div>
</body>
</html>"""
    return html


def create_listing(message, client_config):
    """
    Full pipeline: parse message → generate description → create HTML listing.

    Returns dict with listing data and file path.
    """
    print(f"[listing_poster] Processing: {message}")

    # Step 1: Parse the message
    listing_data = parse_listing_message(message, client_config)
    if "error" in listing_data:
        return listing_data

    print(f"[listing_poster] Parsed: {listing_data.get('address', 'Unknown')} — ${listing_data.get('price', 0):,.0f}")

    # Step 2: Generate description
    description = generate_listing_description(listing_data, client_config)
    if "[ERROR]" in description:
        return {"error": description}

    # Step 3: Create HTML
    html = create_listing_html(listing_data, description, client_config)

    # Step 4: Save the file
    output_dir = client_config.get("listings_dir", os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "clients", "listings"
    ))
    os.makedirs(output_dir, exist_ok=True)

    safe_address = listing_data.get("address", "listing").replace(" ", "_").replace(",", "")[:50]
    filename = f"{safe_address}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    filepath = os.path.join(output_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[listing_poster] Listing created: {filepath}")

    return {
        "listing_data": listing_data,
        "description": description[:200] + "...",
        "file": filepath,
        "filename": filename
    }


if __name__ == "__main__":
    test_config = {
        "client_name": "Miami Realty Group",
        "phone": "(786) 555-1234",
        "email": "info@miamirealty.com"
    }
    result = create_listing("List 123 Main St Miami for $275k, 3 bed 2 bath, updated kitchen, pool", test_config)
    print(json.dumps(result, indent=2, default=str))
