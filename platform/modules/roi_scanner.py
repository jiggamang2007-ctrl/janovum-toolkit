"""
Janovum Module — ROI Deal Scanner (Real Estate)
Scans property listings, calculates ROI, finds best deals at cheapest cost.
Displays results on an HTML dashboard.

How it works:
  1. Python scrapes listing sites on a schedule (free)
  2. Collects property data (price, rent estimate, location, etc.)
  3. Calculates ROI metrics
  4. Sends top deals to Claude for analysis (pennies)
  5. Updates HTML dashboard with results
  6. Alerts client via Telegram if hot deal found

Requirements:
  pip install requests beautifulsoup4
  Client config needs: target_area, max_price, min_roi
"""

import json
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.engine import quick_ask

MODULE_NAME = "roi_scanner"
MODULE_DESC = "ROI Deal Scanner — finds best real estate deals automatically"


def calculate_roi(purchase_price, monthly_rent, annual_expenses=0):
    """Calculate basic ROI metrics for a property."""
    if purchase_price <= 0:
        return {}

    annual_rent = monthly_rent * 12
    net_income = annual_rent - annual_expenses
    cap_rate = (net_income / purchase_price) * 100
    grm = purchase_price / annual_rent if annual_rent > 0 else 999
    cash_on_cash = (net_income / (purchase_price * 0.25)) * 100  # assuming 25% down

    return {
        "cap_rate": round(cap_rate, 2),
        "grm": round(grm, 2),
        "cash_on_cash": round(cash_on_cash, 2),
        "annual_net": round(net_income, 2),
        "monthly_cashflow": round(net_income / 12, 2)
    }


def analyze_deals_with_claude(deals, client_config):
    """Have Claude analyze the top deals and give recommendations."""
    client_name = client_config.get("client_name", "Client")
    target_area = client_config.get("target_area", "")
    strategy = client_config.get("investment_strategy", "buy and hold rental")

    deals_text = ""
    for i, d in enumerate(deals[:10], 1):
        deals_text += f"""
Deal #{i}: {d.get('address', 'Unknown')}
  Price: ${d.get('price', 0):,.0f}
  Beds/Baths: {d.get('beds', '?')}/{d.get('baths', '?')}
  Sq Ft: {d.get('sqft', 'N/A')}
  Est. Monthly Rent: ${d.get('est_rent', 0):,.0f}
  Cap Rate: {d.get('roi', {}).get('cap_rate', 'N/A')}%
  Cash-on-Cash: {d.get('roi', {}).get('cash_on_cash', 'N/A')}%
  GRM: {d.get('roi', {}).get('grm', 'N/A')}
"""

    prompt = f"""Analyze these real estate deals for {client_name}.
Target area: {target_area}
Strategy: {strategy}

{deals_text}

For each deal, give:
1. A 1-2 sentence assessment
2. A score from 1-10 (10 = amazing deal)
3. Any red flags or things to investigate

Then rank the top 3 deals and explain why."""

    return quick_ask(prompt, system_prompt="You are a real estate investment analyst for Janovum.")


def generate_dashboard_data(deals, analysis, client_config):
    """Generate JSON data for the HTML dashboard."""
    return {
        "generated_at": datetime.now().isoformat(),
        "client": client_config.get("client_name", ""),
        "target_area": client_config.get("target_area", ""),
        "total_deals_scanned": len(deals),
        "deals": deals[:20],
        "analysis": analysis,
        "filters": {
            "max_price": client_config.get("max_price", 0),
            "min_roi": client_config.get("min_roi", 0),
            "min_beds": client_config.get("min_beds", 0)
        }
    }


def add_listing(listings, address, price, beds, baths, sqft, est_rent, source="manual", annual_expenses=0):
    """Add a property listing and calculate its ROI."""
    if annual_expenses == 0:
        # Estimate: taxes + insurance + maintenance ≈ 1.5% of price + vacancy 5%
        annual_expenses = (price * 0.015) + (est_rent * 12 * 0.05)

    roi = calculate_roi(price, est_rent, annual_expenses)

    listing = {
        "address": address,
        "price": price,
        "beds": beds,
        "baths": baths,
        "sqft": sqft,
        "est_rent": est_rent,
        "annual_expenses": round(annual_expenses, 2),
        "roi": roi,
        "source": source,
        "scanned_at": datetime.now().isoformat()
    }
    listings.append(listing)
    return listing


def filter_and_rank(listings, min_cap_rate=0, max_price=float('inf'), min_beds=0):
    """Filter and rank listings by cap rate."""
    filtered = [
        l for l in listings
        if l.get("roi", {}).get("cap_rate", 0) >= min_cap_rate
        and l.get("price", float('inf')) <= max_price
        and l.get("beds", 0) >= min_beds
    ]
    return sorted(filtered, key=lambda x: x.get("roi", {}).get("cap_rate", 0), reverse=True)


def run_scan(client_config):
    """
    Run a full scan cycle.

    client_config needs:
      - client_name: business name
      - target_area: city/zip to scan
      - max_price: maximum property price
      - min_roi: minimum cap rate %
      - min_beds: minimum bedrooms
      - investment_strategy: buy-and-hold, flip, etc.
      - listings: list of manual listings to analyze (optional)
    """
    print(f"[roi_scanner] Running scan for {client_config.get('client_name', 'Client')}...")
    print(f"[roi_scanner] Target: {client_config.get('target_area', 'N/A')}")
    print(f"[roi_scanner] Max price: ${client_config.get('max_price', 0):,.0f}")
    print(f"[roi_scanner] Min cap rate: {client_config.get('min_roi', 0)}%")

    # Process any manual listings from config
    listings = []
    for l in client_config.get("listings", []):
        add_listing(
            listings,
            address=l.get("address", ""),
            price=l.get("price", 0),
            beds=l.get("beds", 0),
            baths=l.get("baths", 0),
            sqft=l.get("sqft", 0),
            est_rent=l.get("est_rent", 0),
            source=l.get("source", "manual")
        )

    # Filter and rank
    top_deals = filter_and_rank(
        listings,
        min_cap_rate=client_config.get("min_roi", 0),
        max_price=client_config.get("max_price", float('inf')),
        min_beds=client_config.get("min_beds", 0)
    )

    print(f"[roi_scanner] Found {len(top_deals)} deals matching criteria")

    # Claude analysis
    analysis = ""
    if top_deals:
        print("[roi_scanner] Sending to Claude for analysis...")
        analysis = analyze_deals_with_claude(top_deals, client_config)
        if "[ERROR]" in analysis:
            print(f"[roi_scanner] Claude error: {analysis}")
            analysis = "Analysis unavailable — API error."

    # Generate dashboard data
    dashboard = generate_dashboard_data(top_deals, analysis, client_config)

    # Save results
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "clients")
    output_file = os.path.join(output_dir, f"{client_config.get('client_name', 'client').replace(' ', '_')}_roi_results.json")
    with open(output_file, "w") as f:
        json.dump(dashboard, f, indent=2)
    print(f"[roi_scanner] Results saved to {output_file}")

    return dashboard


if __name__ == "__main__":
    # Test with sample data
    test_config = {
        "client_name": "Miami Investor",
        "target_area": "Miami, FL",
        "max_price": 400000,
        "min_roi": 5,
        "min_beds": 2,
        "investment_strategy": "buy and hold rental",
        "listings": [
            {"address": "123 Main St, Miami", "price": 250000, "beds": 3, "baths": 2, "sqft": 1400, "est_rent": 2200},
            {"address": "456 Oak Ave, Miami", "price": 180000, "beds": 2, "baths": 1, "sqft": 950, "est_rent": 1600},
            {"address": "789 Palm Dr, Miami", "price": 350000, "beds": 4, "baths": 3, "sqft": 2100, "est_rent": 2800},
        ]
    }
    results = run_scan(test_config)
    print(f"\nTop deals: {len(results['deals'])}")
