from reportlab.lib.pagesizes import letter
from reportlab.lib.colors import HexColor
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER
import os

output_path = r"C:\Users\jigga\OneDrive\Desktop\janovum company planing\Jaden_Gonzalez_Resume.pdf"

doc = SimpleDocTemplate(output_path, pagesize=letter,
    topMargin=0.5*inch, bottomMargin=0.5*inch,
    leftMargin=0.65*inch, rightMargin=0.65*inch)

orange = HexColor("#ff6b35")
dark = HexColor("#1a1a1a")
grey = HexColor("#555555")

name_s = ParagraphStyle("Name", fontSize=24, fontName="Helvetica-Bold", textColor=dark, alignment=TA_CENTER, spaceAfter=8)
contact_s = ParagraphStyle("Contact", fontSize=10, fontName="Helvetica", textColor=grey, alignment=TA_CENTER, spaceAfter=10)
section_s = ParagraphStyle("Section", fontSize=12, fontName="Helvetica-Bold", textColor=orange, spaceBefore=12, spaceAfter=4)
role_s = ParagraphStyle("Role", fontSize=11, fontName="Helvetica-Bold", textColor=dark, spaceAfter=1)
sub_s = ParagraphStyle("Sub", fontSize=9, fontName="Helvetica-Oblique", textColor=grey, spaceAfter=4)
body_s = ParagraphStyle("Body", fontSize=9.5, fontName="Helvetica", textColor=HexColor("#333333"), spaceAfter=2, leading=13, leftIndent=10)
skill_s = ParagraphStyle("Skill", fontSize=9.5, fontName="Helvetica", textColor=HexColor("#333333"), spaceAfter=1, leading=13, leftIndent=10)
intro_s = ParagraphStyle("Intro", fontSize=10, fontName="Helvetica", textColor=HexColor("#333333"), spaceAfter=8, leading=14)

story = []

story.append(Paragraph("JADEN GONZALEZ", name_s))
story.append(Paragraph("Hialeah, FL  |  305-998-8807  |  janovumllc@gmail.com  |  janovum.com/hire", contact_s))
story.append(HRFlowable(width="100%", thickness=1, color=orange))

story.append(Paragraph("ABOUT ME", section_s))
story.append(Paragraph(
    "Self-taught AI automation engineer and founder of Janovum LLC. The name comes from Janus, the Roman god of "
    "doorways and new beginnings, and Novum, meaning new creation \u2014 a doorway to new creation. I built a full-stack "
    "AI agent platform from scratch \u2014 202 tools, 56 agent roles, 28 core systems, multi-tenant SaaS, and a live "
    "voice AI pipeline \u2014 all deployed to production. No degree, no team, just relentless focus and execution. "
    "I have ADHD, which means when I lock in on something, I go all the way \u2014 hyperfocused until it\u2019s shipped. "
    "I think about everything in terms of ROI \u2014 if I\u2019m building something, it has to be the cheapest, fastest, "
    "most efficient way to get the job done. I believe anything is possible with time and the right person building it.",
    intro_s))

story.append(Paragraph("EXPERIENCE", section_s))
story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor("#dddddd")))

story.append(Paragraph("Founder &amp; Lead Engineer \u2014 Janovum LLC", role_s))
story.append(Paragraph("Miami, FL  |  2026 \u2013 Present", sub_s))
story.append(Paragraph("\u2022 Built a complete AI automation platform from scratch \u2014 202 integrated tools across 52 categories", body_s))
story.append(Paragraph("\u2022 Developed 56 pre-built AI agent roles (receptionist, sales, content writer, HR, legal, real estate, + 50 more)", body_s))
story.append(Paragraph("\u2022 Engineered 28 core systems: heartbeat monitoring, cost tracking, guardrails, model failover, tracing, approvals, event bus, sandbox, agent registry, marketplace", body_s))
story.append(Paragraph("\u2022 Built a live AI voice receptionist \u2014 Twilio + Deepgram STT + Groq/Cerebras LLM + Cartesia TTS, answering real calls 24/7 at $0.023/minute", body_s))
story.append(Paragraph("\u2022 Optimized costs aggressively \u2014 researched and integrated the cheapest API for every capability, built automatic failover, achieved 95%+ cost reduction vs. competitors", body_s))
story.append(Paragraph("\u2022 Designed multi-tenant SaaS \u2014 user accounts, per-user data isolation, session auth, process management, auto-provisioning", body_s))
story.append(Paragraph("\u2022 Built per-client cost tracking and budget management \u2014 daily spend caps, call limits, per-API-call cost attribution", body_s))
story.append(Paragraph("\u2022 Deployed full production stack on Linux VPS \u2014 Flask, nginx, systemd, SSL/TLS, DNS \u2014 $7/mo total infra cost", body_s))
story.append(Paragraph("\u2022 Designed scalable revenue model \u2014 $1,000 setup + $500/mo recurring with near-zero marginal cost per client", body_s))
story.append(Spacer(1, 5))

story.append(Paragraph("Sales Representative \u2014 AT&amp;T", role_s))
story.append(Paragraph("Miami, FL  |  2026", sub_s))
story.append(Paragraph("\u2022 Sold wireless plans, devices, and services directly to customers in a fast-paced retail environment", body_s))
story.append(Paragraph("\u2022 Learned consultative selling, objection handling, and how to communicate technical products to non-technical people", body_s))
story.append(Paragraph("\u2022 Left to pursue AI automation full-time \u2014 recognized a bigger opportunity in building technology", body_s))
story.append(Spacer(1, 5))

story.append(Paragraph("Independent Day Trader", role_s))
story.append(Paragraph("2024 \u2013 2025", sub_s))
story.append(Paragraph("\u2022 Actively traded stocks and crypto markets starting at age 16", body_s))
story.append(Paragraph("\u2022 Built discipline around risk management, capital allocation, and knowing when to cut losses", body_s))
story.append(Paragraph("\u2022 Learned to think in terms of ROI on every decision \u2014 a mindset I apply to every tool and API I choose", body_s))
story.append(Paragraph("\u2022 Transitioned to long-term holding after the market dried up \u2014 shifted full focus to building with AI", body_s))

story.append(Paragraph("EDUCATION", section_s))
story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor("#dddddd")))
story.append(Paragraph("Horeb Christian School \u2014 High School Diploma", role_s))
story.append(Paragraph("Hialeah, FL", sub_s))

story.append(Paragraph("TECHNICAL SKILLS", section_s))
story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor("#dddddd")))
story.append(Paragraph("<b>Languages:</b>  Python, JavaScript, HTML/CSS, SQL, Bash", skill_s))
story.append(Paragraph("<b>Backend:</b>  Flask, FastAPI, REST API design, WebSocket servers, multi-tenancy, process management", skill_s))
story.append(Paragraph("<b>AI / LLM:</b>  Groq, Claude API, Cerebras, OpenAI \u2014 prompt engineering, agent orchestration, multi-agent systems, model failover", skill_s))
story.append(Paragraph("<b>Voice AI:</b>  Twilio (voice + SMS), Deepgram (STT), Cartesia (TTS), Pipecat (agent framework)", skill_s))
story.append(Paragraph("<b>Infrastructure:</b>  Linux VPS (Vultr), nginx, systemd, SSL/Let\u2019s Encrypt, DNS, Git/GitHub", skill_s))
story.append(Paragraph("<b>Automation:</b>  Selenium, browser automation, web scraping, email (SMTP/IMAP), webhook management", skill_s))
story.append(Paragraph("<b>Integrations:</b>  Twilio, Discord, Telegram, Slack, WhatsApp, OAuth, CRM, invoicing, appointments", skill_s))
story.append(Paragraph("<b>Tools:</b>  Claude Code, VS Code, Chrome DevTools, Postman, Pillow, ReportLab", skill_s))

story.append(Paragraph("BUSINESS &amp; FINANCIAL SKILLS", section_s))
story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor("#dddddd")))
story.append(Paragraph("<b>Cost Optimization:</b>  Evaluate and compare API providers by cost-per-call, build failover to maximize uptime while minimizing spend", skill_s))
story.append(Paragraph("<b>ROI-Driven Development:</b>  Every tool and integration decision based on return on investment \u2014 cheapest path to the best result", skill_s))
story.append(Paragraph("<b>Budget Management:</b>  Built per-client spend tracking, daily caps, and cost attribution \u2014 know exactly where every dollar goes", skill_s))
story.append(Paragraph("<b>Capital Allocation:</b>  Trading background taught disciplined resource allocation \u2014 invest where the return is highest, cut what doesn\u2019t perform", skill_s))
story.append(Paragraph("<b>Revenue Strategy:</b>  Designed high-margin pricing ($1K setup + $500/mo) with near-zero marginal cost per new client", skill_s))
story.append(Paragraph("<b>Sales &amp; Communication:</b>  AT&amp;T sales experience \u2014 consultative selling, objection handling, explaining tech to non-technical clients", skill_s))

story.append(Paragraph("LIVE PORTFOLIO", section_s))
story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor("#dddddd")))
story.append(Paragraph("<b>Full breakdown:</b>  janovum.com/hire", skill_s))
story.append(Paragraph("<b>Explore the platform:</b>  janovum.com/toolkit/guest", skill_s))
story.append(Paragraph("<b>Call the AI receptionist:</b>  +1 (833) 958-9975", skill_s))
story.append(Paragraph("<b>Company website:</b>  janovum.com", skill_s))

doc.build(story)
print(f"Resume created: {output_path}")
print(f"Size: {os.path.getsize(output_path)} bytes")
