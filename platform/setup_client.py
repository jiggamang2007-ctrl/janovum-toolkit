#!/usr/bin/env python3
"""
Janovum Toolkit — Client Setup Wizard
Run: python setup_client.py

One-command setup for any new client. Asks simple questions,
configures everything, and starts the server. No coding needed.
"""

import os
import sys
import json

PLATFORM_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(PLATFORM_DIR, "config.json")
MARKETPLACE_DIR = os.path.join(PLATFORM_DIR, "marketplace")

# ── All available modules ──
ALL_MODULES = {
    "ai_receptionist":    {"name": "AI Receptionist",         "icon": "📞", "free": True,  "desc": "Virtual front desk — greets, books, answers FAQs"},
    "lead_hunter":        {"name": "Lead Hunter",             "icon": "🎯", "free": True,  "desc": "Find business leads from web sources"},
    "email_campaign":     {"name": "Email Campaign Bot",      "icon": "📧", "free": True,  "desc": "Cold email outreach with follow-ups"},
    "content_writer":     {"name": "Content Writer",          "icon": "✍️",  "free": False, "desc": "AI blog posts, articles, marketing copy"},
    "web_monitor":        {"name": "Web Monitor",             "icon": "🌐", "free": True,  "desc": "Monitor websites for changes"},
    "task_scheduler":     {"name": "Task Scheduler",          "icon": "⏰", "free": True,  "desc": "Schedule recurring tasks"},
    "re_lead_scraper":    {"name": "RE Lead Scraper",         "icon": "🔍", "free": True,  "desc": "Real estate lead finder"},
    "re_auto_responder":  {"name": "RE Auto-Responder",       "icon": "💬", "free": False, "desc": "AI replies to real estate inquiries"},
    "re_market_analyzer": {"name": "RE Market Analyzer",      "icon": "📊", "free": False, "desc": "Real estate market analysis"},
    "re_social_poster":   {"name": "RE Social Poster",        "icon": "📱", "free": True,  "desc": "Auto-post listings to social media"},
    "discord_assistant":  {"name": "Discord Assistant",        "icon": "🤖", "free": False, "desc": "AI Discord chatbot"},
    "customer_support":   {"name": "Customer Support",        "icon": "🎧", "free": True,  "desc": "Auto-handle support tickets"},
    "appointment_scheduler": {"name": "Appointment Scheduler","icon": "📅", "free": True,  "desc": "Book and manage appointments"},
    "property_manager":   {"name": "Property Manager",        "icon": "🏢", "free": False, "desc": "Tenant comms, maintenance, rent tracking"},
    "restaurant_manager": {"name": "Restaurant Manager",      "icon": "🍽️",  "free": True,  "desc": "Reservations, menu, reviews"},
    "sales_outreach":     {"name": "Sales Outreach",          "icon": "💰", "free": True,  "desc": "Automated sales pipeline"},
    "social_media_manager": {"name": "Social Media Manager",  "icon": "📲", "free": True,  "desc": "Content scheduling and posting"},
    "hr_onboarding":      {"name": "HR Onboarding",           "icon": "👥", "free": False, "desc": "Employee onboarding automation"},
}

# ── Quick-setup presets ──
PRESETS = {
    "1": {
        "name": "Barbershop / Salon",
        "modules": ["ai_receptionist", "appointment_scheduler"],
        "business_type": "barbershop",
    },
    "2": {
        "name": "Dental / Medical Office",
        "modules": ["ai_receptionist", "appointment_scheduler", "customer_support"],
        "business_type": "medical office",
    },
    "3": {
        "name": "Real Estate Agency",
        "modules": ["ai_receptionist", "re_lead_scraper", "re_auto_responder", "re_market_analyzer", "re_social_poster", "email_campaign"],
        "business_type": "real estate agency",
    },
    "4": {
        "name": "Restaurant / Food Service",
        "modules": ["ai_receptionist", "restaurant_manager"],
        "business_type": "restaurant",
    },
    "5": {
        "name": "Law Firm / Professional Services",
        "modules": ["ai_receptionist", "appointment_scheduler", "email_campaign", "content_writer"],
        "business_type": "law firm",
    },
    "6": {
        "name": "E-Commerce / Online Store",
        "modules": ["customer_support", "email_campaign", "social_media_manager", "content_writer"],
        "business_type": "e-commerce store",
    },
    "7": {
        "name": "Marketing Agency",
        "modules": ["lead_hunter", "email_campaign", "content_writer", "social_media_manager", "web_monitor"],
        "business_type": "marketing agency",
    },
    "8": {
        "name": "Property Management",
        "modules": ["ai_receptionist", "property_manager", "task_scheduler"],
        "business_type": "property management company",
    },
    "9": {
        "name": "Custom (pick your own modules)",
        "modules": [],
        "business_type": "",
    },
}


def clear():
    os.system("cls" if sys.platform == "win32" else "clear")


def banner():
    print()
    print("=" * 56)
    print("   JANOVUM TOOLKIT — CLIENT SETUP WIZARD")
    print("=" * 56)
    print()


def ask(prompt, default="", required=True):
    """Ask a question with optional default."""
    suffix = f" [{default}]" if default else ""
    while True:
        answer = input(f"  {prompt}{suffix}: ").strip()
        if not answer and default:
            return default
        if answer:
            return answer
        if not required:
            return ""
        print("    ^ This field is required.")


def ask_yn(prompt, default="y"):
    """Ask yes/no question."""
    suffix = "[Y/n]" if default == "y" else "[y/N]"
    answer = input(f"  {prompt} {suffix}: ").strip().lower()
    if not answer:
        return default == "y"
    return answer in ("y", "yes")


def choose_preset():
    """Let user pick a business preset."""
    print("  What type of business is this for?\n")
    for key, preset in PRESETS.items():
        mods = ", ".join(ALL_MODULES[m]["icon"] + " " + ALL_MODULES[m]["name"] for m in preset["modules"]) if preset["modules"] else "You choose"
        print(f"    {key}. {preset['name']}")
        if preset["modules"]:
            print(f"       Includes: {mods}")
        print()

    while True:
        choice = input("  Pick a number (1-9): ").strip()
        if choice in PRESETS:
            return PRESETS[choice]
        print("    ^ Pick 1-9")


def choose_custom_modules():
    """Let user pick individual modules."""
    print("\n  Available Modules:\n")
    keys = list(ALL_MODULES.keys())
    for i, key in enumerate(keys):
        mod = ALL_MODULES[key]
        cost = "FREE" if mod["free"] else "Needs API key"
        print(f"    {i+1:2}. {mod['icon']}  {mod['name']:28s} ({cost})")
        print(f"        {mod['desc']}")

    print()
    print("  Enter module numbers separated by commas (e.g., 1,3,5)")
    picks = input("  Your picks: ").strip()
    chosen = []
    for p in picks.split(","):
        p = p.strip()
        if p.isdigit() and 1 <= int(p) <= len(keys):
            chosen.append(keys[int(p) - 1])
    return chosen


def collect_business_basics():
    """Collect core business info — used by ALL modules."""
    print("\n  --- Business Details ---\n")
    print("  This info is shared across all enabled modules.\n")
    info = {}
    info["business_name"] = ask("Business name (e.g. Tony's Barbershop)")
    info["business_type"] = ask("Type of business (e.g. barbershop, dental, law firm)")
    info["business_description"] = ask("Short description of the business (1-2 sentences)")
    info["business_hours"] = ask("Business hours (e.g. Mon-Fri 9am-7pm, Sat 8am-5pm)")
    info["business_address"] = ask("Business address")
    info["business_phone"] = ask("Business phone")
    info["business_email"] = ask("Business email")
    info["owner_notification_email"] = ask("Owner email (for notifications)")
    info["owner_notification_phone"] = ask("Owner phone (for urgent alerts)", required=False)
    info["language"] = ask("Language(s)", default="English")
    info["personality"] = ask("AI personality/vibe for this business", default="friendly and professional")
    return info


# ── Per-module setup questions ──
# Each module asks ONLY what's specific to it. Business basics are already collected.

MODULE_SETUP = {

    "ai_receptionist": {
        "title": "AI Receptionist",
        "questions": [
            ("services_offered",      "Services offered (comma-separated)",                                    True),
            ("service_prices",        "Prices for each service (comma-separated, same order)",                  False),
            ("booking_link",          "Online booking link (or leave blank)",                                   False),
            ("staff_names",           "Staff members (e.g. Tony (barber), Lisa (front desk))",                  False),
            ("special_instructions",  "Special instructions or FAQs to handle?",                               False),
            ("after_hours_message",   "After-hours auto-reply message",                                        True),
            ("greeting_style",        "How should the receptionist greet? (e.g. 'Hey!' or 'Good morning, thank you for calling...')", False),
        ],
        "defaults": {
            "after_hours_message": "Thanks for reaching out! We're currently closed but will get back to you first thing when we open.",
            "greeting_style": "Hey there! Thanks for reaching out to {business_name}! How can I help you today?",
        }
    },

    "lead_hunter": {
        "title": "Lead Hunter",
        "questions": [
            ("target_industry",       "What industry are you targeting? (e.g. restaurants, HVAC, dentists)",    True),
            ("target_location",       "Target location/area (e.g. Miami FL, Dallas TX metro)",                  True),
            ("ideal_customer",        "Describe your ideal customer in 1 sentence",                             True),
            ("lead_sources",          "Preferred lead sources (Google Maps, directories, LinkedIn, all)",        False),
            ("min_lead_score",        "Minimum lead quality score to keep (1-100)",                              False),
        ],
        "defaults": {
            "lead_sources": "all",
            "min_lead_score": "50",
        }
    },

    "email_campaign": {
        "title": "Email Campaign Bot",
        "questions": [
            ("sender_name",           "Sender name on emails (e.g. Tony from Tony's Barbershop)",              True),
            ("sender_email",          "Email address to send from",                                             True),
            ("email_signature",       "Email signature (name, title, phone)",                                   True),
            ("campaign_goal",         "What's the goal? (e.g. get bookings, sell service, follow up leads)",    True),
            ("follow_up_days",        "Days to wait before follow-up (e.g. 3)",                                 False),
            ("max_emails_per_day",    "Max emails per day (recommend 30-50)",                                   False),
            ("gmail_app_password",    "Gmail app password for sending (or leave blank to set later)",           False),
        ],
        "defaults": {
            "follow_up_days": "3",
            "max_emails_per_day": "40",
        }
    },

    "content_writer": {
        "title": "Content Writer",
        "questions": [
            ("content_topics",        "Main topics to write about (comma-separated)",                           True),
            ("target_audience",       "Who is the audience? (e.g. homeowners in Miami, small business owners)", True),
            ("writing_tone",          "Writing tone (e.g. casual, professional, educational, persuasive)",      True),
            ("content_types",         "Content types needed (blog posts, social captions, emails, all)",         False),
            ("seo_keywords",          "Important SEO keywords (comma-separated, or leave blank)",                False),
            ("brand_voice_notes",     "Any brand voice rules? (e.g. never say 'cheap', always say 'affordable')", False),
        ],
        "defaults": {
            "content_types": "all",
            "writing_tone": "professional but approachable",
        }
    },

    "web_monitor": {
        "title": "Web Monitor",
        "questions": [
            ("urls_to_monitor",       "URLs to monitor (comma-separated)",                                      True),
            ("check_frequency",       "How often to check (e.g. every 15min, hourly, daily)",                   True),
            ("what_to_watch",         "What to watch for (price changes, new content, any change)",             True),
            ("alert_method",          "Alert via (email, sms, both)",                                           False),
        ],
        "defaults": {
            "check_frequency": "hourly",
            "alert_method": "email",
        }
    },

    "re_lead_scraper": {
        "title": "Real Estate Lead Scraper",
        "questions": [
            ("target_markets",        "Target markets/cities (comma-separated)",                                 True),
            ("property_types",        "Property types (residential, commercial, land, all)",                     True),
            ("price_range",           "Price range (e.g. 200000-500000)",                                       False),
            ("search_radius_miles",   "Search radius in miles",                                                  False),
            ("scrape_frequency",      "How often to scrape (daily, weekly)",                                     False),
        ],
        "defaults": {
            "property_types": "residential",
            "search_radius_miles": "25",
            "scrape_frequency": "daily",
        }
    },

    "re_auto_responder": {
        "title": "Real Estate Auto-Responder",
        "questions": [
            ("agent_name",            "Real estate agent name",                                                  True),
            ("agent_license",         "License number (for compliance)",                                         False),
            ("response_style",        "Response style (warm and personal, fast and efficient, consultative)",    True),
            ("auto_send_threshold",   "Auto-send if AI confidence above (1-100, e.g. 90)",                      False),
            ("specialties",           "Specialties to highlight (e.g. luxury homes, first-time buyers)",         False),
        ],
        "defaults": {
            "response_style": "warm and personal",
            "auto_send_threshold": "90",
        }
    },

    "re_market_analyzer": {
        "title": "Real Estate Market Analyzer",
        "questions": [
            ("analysis_markets",      "Markets to analyze (comma-separated cities/zip codes)",                   True),
            ("report_frequency",      "Report frequency (weekly, monthly)",                                      True),
            ("focus_metrics",         "Key metrics to focus on (prices, inventory, DOM, all)",                    False),
            ("competitor_agents",     "Competitor agents/brokerages to track (or leave blank)",                   False),
        ],
        "defaults": {
            "report_frequency": "weekly",
            "focus_metrics": "all",
        }
    },

    "re_social_poster": {
        "title": "Real Estate Social Poster",
        "questions": [
            ("platforms",             "Platforms to post on (Instagram, Facebook, Twitter, all)",                 True),
            ("posting_frequency",     "How often to post (daily, 3x/week, weekly)",                              True),
            ("hashtags",              "Default hashtags (comma-separated)",                                       False),
            ("brand_colors",          "Brand colors for graphics (e.g. navy blue and gold)",                     False),
            ("include_contact_info",  "Include phone/email on posts? (yes/no)",                                  False),
        ],
        "defaults": {
            "platforms": "all",
            "posting_frequency": "3x/week",
            "include_contact_info": "yes",
        }
    },

    "customer_support": {
        "title": "Customer Support",
        "questions": [
            ("support_email",         "Support email address",                                                   True),
            ("common_issues",         "Most common customer issues (comma-separated)",                            True),
            ("escalation_email",      "Escalation email (for issues AI can't solve)",                             True),
            ("response_time_target",  "Target response time (e.g. under 5 minutes)",                              False),
            ("refund_policy",         "Refund/return policy summary",                                             False),
            ("knowledge_base_notes",  "Any important policies or info the AI should know?",                       False),
        ],
        "defaults": {
            "response_time_target": "under 5 minutes",
        }
    },

    "appointment_scheduler": {
        "title": "Appointment Scheduler",
        "questions": [
            ("appointment_types",     "Types of appointments (comma-separated)",                                  True),
            ("appointment_duration",  "Default appointment duration (e.g. 30min, 1hr)",                           True),
            ("available_days",        "Available days (e.g. Mon-Fri, Mon-Sat)",                                   True),
            ("available_hours",       "Available hours (e.g. 9am-5pm)",                                           True),
            ("buffer_between",        "Buffer time between appointments (e.g. 15min)",                             False),
            ("max_daily_appointments","Max appointments per day",                                                  False),
            ("booking_link",          "External booking link (Calendly, etc.) or leave blank",                     False),
        ],
        "defaults": {
            "buffer_between": "15min",
            "max_daily_appointments": "20",
        }
    },

    "social_media_manager": {
        "title": "Social Media Manager",
        "questions": [
            ("platforms",             "Platforms to manage (Instagram, Facebook, Twitter, LinkedIn, TikTok)",     True),
            ("posting_schedule",      "Posting schedule (e.g. daily at 10am, 3x/week)",                           True),
            ("content_themes",        "Content themes/pillars (e.g. tips, behind-scenes, promotions, testimonials)", True),
            ("brand_voice",           "Brand voice on social (casual, professional, funny, inspirational)",        True),
            ("hashtag_strategy",      "Default hashtags (comma-separated)",                                        False),
        ],
        "defaults": {
            "posting_schedule": "daily at 10am",
            "brand_voice": "casual and engaging",
        }
    },

    "sales_outreach": {
        "title": "Sales Outreach",
        "questions": [
            ("product_service",       "What are you selling? (1-2 sentences)",                                    True),
            ("target_customer",       "Who is your ideal customer?",                                               True),
            ("unique_selling_point",  "What makes you different? (your pitch)",                                    True),
            ("outreach_channels",     "Outreach channels (email, LinkedIn, cold call, all)",                       False),
            ("follow_up_sequence",    "Follow-up sequence (e.g. 3 emails over 10 days)",                           False),
            ("meeting_link",          "Calendar/meeting booking link",                                              False),
        ],
        "defaults": {
            "outreach_channels": "email",
            "follow_up_sequence": "3 emails over 10 days",
        }
    },

    "property_manager": {
        "title": "Property Manager",
        "questions": [
            ("portfolio_size",        "Total number of units managed",                                             True),
            ("property_types",        "Property types (residential, commercial, mixed)",                            True),
            ("rent_due_day",          "Rent due day of month (e.g. 1)",                                             True),
            ("late_fee_grace_days",   "Late fee grace period (days after due date)",                                 True),
            ("late_fee_amount",       "Late fee amount ($)",                                                         True),
            ("emergency_phone",       "Emergency maintenance phone",                                                 True),
            ("preferred_vendors",     "Preferred maintenance vendors (comma-separated)",                             False),
            ("lease_renewal_days",    "Lease renewal notice period (days before expiry)",                             False),
            ("maintenance_budget",    "Annual maintenance budget per unit ($)",                                       False),
        ],
        "defaults": {
            "rent_due_day": "1",
            "late_fee_grace_days": "5",
            "late_fee_amount": "50",
            "lease_renewal_days": "60",
            "maintenance_budget": "1500",
        }
    },

    "restaurant_manager": {
        "title": "Restaurant Manager",
        "questions": [
            ("cuisine_type",          "Cuisine type (e.g. Italian, Mexican, American, Sushi)",                     True),
            ("seating_capacity",      "Total seating capacity",                                                     True),
            ("reservation_system",    "Reservation system (OpenTable link, phone only, walk-in only)",              True),
            ("menu_highlights",       "Menu highlights / signature dishes",                                         True),
            ("dietary_options",       "Dietary options available (vegan, gluten-free, halal, etc.)",                 False),
            ("delivery_platforms",    "Delivery platforms (UberEats, DoorDash, in-house, none)",                     False),
            ("happy_hour",            "Happy hour details (or leave blank)",                                         False),
        ],
        "defaults": {
            "delivery_platforms": "none",
        }
    },

    "hr_onboarding": {
        "title": "HR Onboarding",
        "questions": [
            ("company_size",          "Company size (number of employees)",                                         True),
            ("departments",           "Departments (comma-separated)",                                               True),
            ("onboarding_steps",      "Onboarding steps new hires go through (comma-separated)",                     True),
            ("hr_contact_email",      "HR contact email",                                                            True),
            ("required_documents",    "Required documents from new hires (comma-separated)",                          True),
            ("benefits_summary",      "Brief benefits summary",                                                       False),
            ("probation_period",      "Probation period (e.g. 90 days)",                                              False),
        ],
        "defaults": {
            "probation_period": "90 days",
        }
    },

    "discord_assistant": {
        "title": "Discord Assistant",
        "questions": [
            ("server_name",           "Discord server name",                                                         True),
            ("bot_name",              "Bot display name",                                                             True),
            ("bot_role",              "What should the bot do? (answer questions, moderate, entertain, all)",         True),
            ("monitored_channels",    "Channels to monitor (comma-separated, or 'all')",                              True),
            ("bot_personality",       "Bot personality (helpful, funny, strict, chill)",                               False),
            ("discord_token",         "Discord bot token (or set later in config)",                                    False),
        ],
        "defaults": {
            "monitored_channels": "all",
            "bot_personality": "helpful and friendly",
        }
    },

    "task_scheduler": {
        "title": "Task Scheduler",
        "questions": [
            ("default_tasks",         "Any tasks to pre-schedule? (e.g. 'send report every Monday 9am')",          False),
            ("timezone",              "Business timezone (e.g. America/New_York, America/Chicago)",                  True),
        ],
        "defaults": {
            "timezone": "America/New_York",
        }
    },
}


def collect_module_config(module_id, business_info):
    """Collect config for a specific module."""
    setup = MODULE_SETUP.get(module_id)
    if not setup:
        return {}

    print(f"\n  --- {setup['title']} Setup ---\n")
    defaults = setup.get("defaults", {})
    config = {}

    for key, prompt, required in setup["questions"]:
        default = defaults.get(key, "")
        # Replace {business_name} in defaults
        if "{business_name}" in str(default):
            default = default.replace("{business_name}", business_info.get("business_name", ""))
        config[key] = ask(prompt, default=default, required=required)

    return config


def build_config(modules, business_info, module_configs, needs_api):
    """Build the final config.json with per-module configs."""
    modules_dict = {}
    for mod_id in ALL_MODULES:
        modules_dict[mod_id] = mod_id in modules

    # Determine LLM mode
    if needs_api:
        llm_provider = "claude"
        model = "claude-sonnet-4-20250514"
    else:
        llm_provider = "pollinations"
        model = "openai"  # Pollinations model name

    config = {
        # Business-wide info (shared by all modules)
        "business_name": business_info.get("business_name", ""),
        "business_type": business_info.get("business_type", ""),
        "business_description": business_info.get("business_description", ""),
        "business_hours": business_info.get("business_hours", ""),
        "business_address": business_info.get("business_address", ""),
        "business_phone": business_info.get("business_phone", ""),
        "business_email": business_info.get("business_email", ""),
        "owner_email": business_info.get("owner_notification_email", ""),
        "owner_phone": business_info.get("owner_notification_phone", ""),
        "language": business_info.get("language", "English"),
        "personality": business_info.get("personality", "friendly and professional"),

        # System config
        "api_key": "",
        "llm_provider": llm_provider,
        "model": model,
        "max_monthly_spend_per_client": 300,
        "server_port": 5050,
        "modules_enabled": modules_dict,

        # Per-module configs — each module gets its own section
        "module_configs": module_configs,
    }

    return config


def check_needs_api(modules):
    """Check if any enabled module requires a paid API."""
    for mod_id in modules:
        if mod_id in ALL_MODULES and not ALL_MODULES[mod_id]["free"]:
            return True
    return False


def print_summary(config, modules):
    """Print setup summary."""
    print("\n" + "=" * 56)
    print("   SETUP COMPLETE")
    print("=" * 56)

    biz = config.get("business_name", "Client")
    print(f"\n  Business: {biz}")
    print(f"  LLM:      {config['llm_provider'].upper()}" + (" (FREE - no API key needed!)" if config["llm_provider"] == "pollinations" else " (API key required)"))
    print(f"\n  Modules Enabled:")
    for mod_id in modules:
        mod = ALL_MODULES.get(mod_id, {})
        cost = "FREE" if mod.get("free") else "API"
        print(f"    {mod.get('icon', '?')}  {mod.get('name', mod_id):28s} [{cost}]")

    needs_api = config["llm_provider"] == "claude"
    print(f"\n  Estimated Monthly Cost:")
    print(f"    VPS:     $6-10/mo")
    if needs_api:
        print(f"    API:     ~$5-50/mo (depends on usage)")
    else:
        print(f"    API:     $0/mo (free models)")
    print(f"    Total:   {'$6-60/mo' if needs_api else '$6-10/mo'}")
    print()


def main():
    clear()
    banner()

    # Step 1: Choose preset
    preset = choose_preset()
    modules = preset["modules"]

    # Step 2: Custom module selection if needed
    if not modules:
        modules = choose_custom_modules()
        if not modules:
            print("\n  No modules selected. Exiting.")
            return

    print(f"\n  Modules selected: {len(modules)}")
    for m in modules:
        mod = ALL_MODULES.get(m, {})
        print(f"    {mod.get('icon', '?')}  {mod.get('name', m)}")

    # Step 3: Collect business basics (shared by all modules)
    business_info = collect_business_basics()

    # Step 4: Collect per-module config
    # Each enabled module asks its own specific questions
    module_configs = {}
    for mod_id in modules:
        if mod_id in MODULE_SETUP:
            print(f"\n  Next: configuring {ALL_MODULES[mod_id]['icon']}  {ALL_MODULES[mod_id]['name']}...")
            module_configs[mod_id] = collect_module_config(mod_id, business_info)
        else:
            module_configs[mod_id] = {}  # No extra config needed

    # Step 5: Check if API key needed
    needs_api = check_needs_api(modules)
    api_key = ""

    if needs_api:
        print(f"\n  Some modules need Claude API for advanced AI:")
        for m in modules:
            if m in ALL_MODULES and not ALL_MODULES[m]["free"]:
                print(f"    - {ALL_MODULES[m]['name']}")
        print()
        if ask_yn("Do you have an Anthropic API key?"):
            api_key = ask("Paste your API key")
        else:
            print("  No worries! You can add it later in config.json.")
            print("  Free modules will still work without it.")
    else:
        print("\n  All selected modules run on FREE models.")
        print("  No API key needed!\n")

    # Step 6: Build and save config
    config = build_config(modules, business_info, module_configs, needs_api)
    if api_key:
        config["api_key"] = api_key

    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)

    print(f"\n  Config saved to: {CONFIG_FILE}")

    # Step 7: Summary
    print_summary(config, modules)

    # Step 8: Offer to start
    print("=" * 56)
    print("   NEXT STEPS")
    print("=" * 56)
    print()
    print("  Start the server:")
    print("    python server_v5.py")
    print()
    print("  Or with Docker:")
    print("    docker compose up -d")
    print()
    print("  Dashboard will be at:")
    print("    http://localhost:5050")
    print()
    print("  To re-configure later, just run:")
    print("    python setup_client.py")
    print()
    print("  Or edit config.json directly.")
    print()
    print("=" * 56)

    if ask_yn("\n  Start the server now?"):
        python = sys.executable
        os.system(f'"{python}" "{os.path.join(PLATFORM_DIR, "server_v5.py")}"')


if __name__ == "__main__":
    main()
