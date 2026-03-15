# Janovum AI Agent Toolkit — Free APIs & Open-Source Tools Research
**Compiled: March 13, 2026**

The goal: provide every capability an AI agent needs at ZERO or near-zero cost.

---

## 1. IMAGE GENERATION

| Tool | Cost | Limits | Integration |
|------|------|--------|-------------|
| **Pollinations.ai** | 100% Free | No limits, no API key | `https://image.pollinations.ai/prompt/{prompt}?width=512&height=512&nologo=true` — just a URL call |
| **Stable Diffusion (local)** | Free (self-hosted) | Limited by your GPU | `pip install diffusers torch` — run SDXL, SD 1.5, etc. locally |
| **Pixazo Free API** | Free | No signup needed | Public endpoint, text-to-image |
| **Cloudflare Workers AI** | Free (10K req/day) | 10,000 inferences/day | Stable Diffusion XL via Cloudflare API |
| **Hugging Face Inference API** | Free tier | Rate-limited | POST to `https://api-inference.huggingface.co/models/{model}` |

**Best pick:** Pollinations.ai for zero-friction, Cloudflare Workers AI for higher quality at scale.

---

## 2. TEXT-TO-SPEECH (TTS)

| Tool | Cost | Limits | Integration |
|------|------|--------|-------------|
| **edge-tts** | 100% Free | Unlimited, no API key | `pip install edge-tts` — uses Microsoft Edge's TTS service. 400+ voices, 100+ languages |
| **Piper TTS** | Free (local) | Unlimited offline | Fast neural TTS optimized for edge devices. `pip install piper-tts` |
| **Kokoro TTS** | Free (Apache 2.0) | Unlimited local | 82M params, quality rivals large models. Commercial use OK |
| **Coqui TTS / XTTS-v2** | Free (non-commercial) | Unlimited local | Voice cloning from 6-second clip, 17 languages. `pip install coqui-tts` |
| **Bark (Suno)** | Free (local) | Unlimited | Expressive TTS with non-speech sounds (laughter, sighing). `pip install suno-bark` |

**Best pick:** edge-tts for cloud-quality with zero setup. Piper for offline. Kokoro for commercial use.

---

## 3. SPEECH-TO-TEXT (STT)

| Tool | Cost | Limits | Integration |
|------|------|--------|-------------|
| **OpenAI Whisper (local)** | Free | Unlimited (your hardware) | `pip install openai-whisper` — runs fully offline. Models: tiny to large-v3 |
| **faster-whisper** | Free | Unlimited local | 4x faster than Whisper using CTranslate2. `pip install faster-whisper` |
| **Whisper.cpp** | Free | Unlimited local | C++ port, runs on CPU efficiently. Great for edge devices |
| **OpenWhispr** | Free | Desktop app | Open source desktop app for Windows/Mac/Linux |
| **Groq Whisper API** | Free tier | Part of Groq's 1K req/day | Fastest cloud Whisper inference |

**Best pick:** faster-whisper for local use. Groq for cloud API speed.

---

## 4. LLM / CHAT

| Tool | Cost | Limits | Integration |
|------|------|--------|-------------|
| **Google AI Studio (Gemini)** | Free | Generous free tier, rate-limited | `pip install google-generativeai` — Gemini 2.5 Pro/Flash |
| **Groq** | Free tier | 1,000 req/day, 6,000 tokens/min | OpenAI-compatible API. Llama, Mistral, Gemma at insane speed |
| **Cloudflare Workers AI** | Free | 10,000 inferences/day | Llama, Mistral, and more via `@cf/meta/llama-3.1-8b-instruct` |
| **Together.ai** | $25 free credit | Credit-based | Open-source models: Llama, Mixtral, CodeLlama |
| **Ollama (local)** | 100% Free | Unlimited (your hardware) | `ollama run llama3.1` — REST API on localhost:11434, OpenAI-compatible |
| **OpenRouter** | Free models available | Some models free, others paid | Aggregator — routes to cheapest provider. OpenAI-compatible |
| **HuggingFace Inference** | Free tier | Rate-limited | Thousands of models available |
| **Pollinations.ai** | Free | Text generation too | `https://text.pollinations.ai/` endpoint |

**Best pick:** Google AI Studio for best free quality. Groq for speed. Ollama for privacy/offline.

---

## 5. WEB SEARCH

| Tool | Cost | Limits | Integration |
|------|------|--------|-------------|
| **SearXNG (self-hosted)** | 100% Free | Unlimited | Metasearch engine aggregating 247+ sources. JSON API. Docker: `docker run searxng/searxng` |
| **DuckDuckGo Instant Answer** | Free | Rate-limited | `pip install duckduckgo-search` — no API key needed |
| **Brave Search API** | Free tier | 2,000 queries/month free | API key required. Independent index, privacy-focused |
| **Serper** | Free tier | 2,500 searches free | Google SERP results. REST API |
| **Google News RSS** | Free | Unlimited | Parse RSS feeds from `news.google.com/rss` — no API key |
| **Tavily** | Free tier | 1,000 searches/month | Purpose-built for AI agents. Returns clean, structured results |

**Best pick:** SearXNG for unlimited free. DuckDuckGo for quick no-setup. Brave for quality.

---

## 6. EMAIL

| Tool | Cost | Limits | Integration |
|------|------|--------|-------------|
| **Gmail SMTP/IMAP** | Free | 500 emails/day (App Password) | `smtplib` + `imaplib` in Python. SMTP: `smtp.gmail.com:587`, IMAP: `imap.gmail.com:993` |
| **Resend** | Free tier | 100 emails/day, 3,000/month | REST API, great developer experience |
| **Mailgun** | Free tier | 100 emails/day for first 3 months | REST API + SMTP relay |
| **SendGrid** | Free tier | 100 emails/day forever | REST API, comprehensive analytics |

**Best pick:** Gmail with App Password for simplicity. Resend for a proper API.

---

## 7. SMS / MESSAGING

| Tool | Cost | Limits | Integration |
|------|------|--------|-------------|
| **Textbelt** | Free | 1 text/day (key=textbelt) | `curl http://textbelt.com/text --data-urlencode phone=... --data-urlencode message=... -d key=textbelt` |
| **textbee.dev** | Free | Uses your Android phone as gateway | Turn your phone into an SMS gateway. Open source |
| **Discord Webhooks** | Free | Unlimited | POST JSON to webhook URL. Best free messaging for bots |
| **Telegram Bot API** | Free | Unlimited | `pip install python-telegram-bot` — full bot platform, no cost |
| **Twilio** | $15 free credit | Credit-based trial | Industry standard. REST API |
| **Email-to-SMS gateways** | Free | Carrier-dependent | Send email to `{number}@carrier-gateway.com` (e.g., `@vtext.com` for Verizon) |

**Best pick:** Telegram Bot for unlimited free messaging. Email-to-SMS for free texts. Discord for team notifications.

---

## 8. IMAGE RECOGNITION / VISION

| Tool | Cost | Limits | Integration |
|------|------|--------|-------------|
| **CLIP (OpenAI)** | Free (local) | Unlimited | `pip install clip-interrogator` — classify images with natural language |
| **BLIP / BLIP-2** | Free (local) | Unlimited | Image captioning + VQA. `pip install transformers` |
| **Google Cloud Vision** | Free tier | 1,000 units/month | Label, text, face detection. REST API |
| **Moondream** | Free (local) | Unlimited | Tiny vision-language model (1.6B params). Runs on CPU |
| **LLaVA** | Free (local) | Unlimited | Vision + language model. Run via Ollama: `ollama run llava` |
| **Tesseract OCR** | Free | Unlimited | `pip install pytesseract` — text extraction from images |
| **Google Gemini Vision** | Free tier | Via AI Studio free tier | Multimodal — send images + text to Gemini |

**Best pick:** Moondream/LLaVA via Ollama for local vision. Gemini for cloud quality.

---

## 9. DOCUMENT PROCESSING

| Tool | Cost | Limits | Integration |
|------|------|--------|-------------|
| **Tesseract OCR** | Free | Unlimited | 100+ languages. `pip install pytesseract` |
| **OCRmyPDF** | Free | Unlimited | Adds OCR text layer to scanned PDFs. `pip install ocrmypdf` |
| **PyPDF2 / PyMuPDF** | Free | Unlimited | PDF text extraction, splitting, merging. `pip install pymupdf` |
| **pdfplumber** | Free | Unlimited | Extract tables and text from PDFs. `pip install pdfplumber` |
| **python-docx** | Free | Unlimited | Read/write Word documents. `pip install python-docx` |
| **Unstructured** | Free (local) | Unlimited | Universal doc parser (PDF, DOCX, HTML, etc.). `pip install unstructured` |
| **OCR.space API** | Free | 500 req/day | Cloud OCR, no install needed. REST API |
| **Marker** | Free | Unlimited | Converts PDF to Markdown with high accuracy. `pip install marker-pdf` |

**Best pick:** PyMuPDF + Tesseract for a complete pipeline. Marker for PDF-to-Markdown.

---

## 10. CODE EXECUTION (SANDBOXED)

| Tool | Cost | Limits | Integration |
|------|------|--------|-------------|
| **Judge0** | Free (self-hosted) | Unlimited | 60+ languages. REST API. `docker-compose up` |
| **Judge0 CE (cloud)** | Free | Public API available | `POST https://ce.judge0.com/submissions` |
| **Piston** | Free (self-hosted) | Unlimited | Docker + Isolate sandbox. Requires auth for cloud API (2026) |
| **Python exec()** | Free | Your own process | Sandboxed via `RestrictedPython` or `subprocess` with limits |
| **Pyodide / WebAssembly** | Free | Browser-based | Python in WASM. No server needed |
| **E2B** | Free tier | 100 sandbox hours/month | Cloud sandboxed code execution for AI agents |

**Best pick:** Judge0 CE for cloud API. E2B for AI agent integration. Self-hosted Judge0 for unlimited.

---

## 11. TRANSLATION

| Tool | Cost | Limits | Integration |
|------|------|--------|-------------|
| **LibreTranslate** | Free (self-hosted) | Unlimited | `pip install libretranslate` then `libretranslate --host 0.0.0.0`. REST API |
| **Argos Translate** | Free | Unlimited local | Python library: `pip install argostranslate`. Offline, open source |
| **Google Translate (unofficial)** | Free | Rate-limited, may break | `pip install googletrans==4.0.0-rc1` — unofficial, no API key |
| **deep-translator** | Free | Wraps multiple services | `pip install deep-translator` — Google, MyMemory, Linguee, etc. |
| **MyMemory API** | Free | 5,000 chars/day (anonymous) | REST API, no key needed: `https://api.mymemory.translated.net/get?q=...&langpair=en|es` |

**Best pick:** LibreTranslate self-hosted for unlimited. MyMemory API for quick integration.

---

## 12. WEATHER, NEWS, FINANCE

### Weather
| Tool | Cost | Limits | Integration |
|------|------|--------|-------------|
| **Open-Meteo** | 100% Free | No API key, unlimited non-commercial | `https://api.open-meteo.com/v1/forecast?latitude=...&longitude=...` |
| **OpenWeatherMap** | Free tier | 1,000 calls/day | API key required. Current weather + 5-day forecast |
| **wttr.in** | Free | No API key | `curl wttr.in/CityName?format=j1` — JSON weather |

### News
| Tool | Cost | Limits | Integration |
|------|------|--------|-------------|
| **GNews API** | Free tier | 100 req/day | `https://gnews.io/api/v4/top-headlines?token=...` |
| **NewsAPI.org** | Free (dev only) | 100 req/day | `https://newsapi.org/v2/everything?q=...&apiKey=...` |
| **Google News RSS** | Free | Unlimited | Parse RSS from `https://news.google.com/rss` |
| **MediaStack** | Free tier | 500 req/month | REST API, 7000+ sources, 50+ countries |

### Finance
| Tool | Cost | Limits | Integration |
|------|------|--------|-------------|
| **Alpha Vantage** | Free | 25 req/day | Stock prices, forex, crypto. `https://www.alphavantage.co/query?...` |
| **Yahoo Finance (yfinance)** | Free | Unofficial, may break | `pip install yfinance` — Python library, comprehensive data |
| **CoinGecko API** | Free | 30 calls/min | Crypto prices. `https://api.coingecko.com/api/v3/...` |
| **Polygon.io** | Free tier | 5 API calls/min | Stocks, options, forex. Delayed data on free tier |

**Best picks:** Open-Meteo (weather), Google News RSS (news), yfinance (finance).

---

## 13. VECTOR DATABASE / EMBEDDINGS

### Embedding Models (all free, run locally)
| Model | Dims | Notes |
|-------|------|-------|
| **all-MiniLM-L6-v2** | 384 | Fast, lightweight. `sentence-transformers` |
| **nomic-embed-text** | 768 | Best open-source. Apache 2.0. Run via Ollama |
| **mxbai-embed-large** | 1024 | High quality. Run via Ollama |
| **Jina Embeddings v3** | 1024 | 1M free tokens via API. 8192 token context |
| **BGE-large** | 1024 | BAAI. Strong multilingual support |

### Vector Databases
| Tool | Cost | Limits | Integration |
|------|------|--------|-------------|
| **ChromaDB** | Free | Unlimited local | `pip install chromadb` — in-memory or persistent. Dead simple API |
| **Qdrant** | Free (local) + Free cloud tier | 1GB free on Qdrant Cloud | `pip install qdrant-client`. Docker or cloud |
| **FAISS (Meta)** | Free | Unlimited local | `pip install faiss-cpu` — blazing fast similarity search |
| **LanceDB** | Free | Unlimited local | Serverless, embedded. `pip install lancedb` |
| **SQLite-VSS** | Free | Unlimited local | Vector search extension for SQLite |

**Best pick:** ChromaDB for simplicity. FAISS for performance. nomic-embed-text via Ollama for embeddings.

---

## 14. FILE STORAGE

| Tool | Cost | Free Tier | Integration |
|------|------|-----------|-------------|
| **Cloudflare R2** | Free | 10GB storage, 0 egress fees, 1M Class A ops/mo | S3-compatible API. Best free storage deal |
| **Backblaze B2** | Free | 10GB storage, 1GB/day egress | S3-compatible. Free egress via Cloudflare CDN |
| **Supabase Storage** | Free | 1GB storage, 1GB/day bandwidth | REST API + Row-Level Security |
| **GitHub (raw files)** | Free | Unlimited public repos | Store files in repos, serve via raw.githubusercontent.com |
| **Local filesystem** | Free | Your disk | For self-hosted setups, just use disk |

**Best pick:** Cloudflare R2 for zero-egress cloud storage. Local filesystem for self-hosted.

---

## 15. AUTOMATION / SCHEDULING

| Tool | Cost | Limits | Integration |
|------|------|--------|-------------|
| **cron-job.org** | 100% Free | Unlimited cron jobs | REST API to manage jobs. Call any URL on schedule |
| **Cronhooks** | Free | Schedule webhooks | REST API for one-time or recurring webhook calls |
| **GitHub Actions** | Free | 2,000 min/month (free plan) | YAML workflows. Run Python, Docker, anything on schedule |
| **Python APScheduler** | Free | Unlimited local | `pip install apscheduler` — in-process scheduler |
| **Celery + Redis** | Free (self-hosted) | Unlimited | Task queue with scheduling. `pip install celery redis` |
| **Cronicle** | Free | Self-hosted | Web-based job scheduler with UI. Node.js |
| **OS crontab** | Free | Unlimited | `crontab -e` on Linux. Task Scheduler on Windows |

**Best pick:** cron-job.org for cloud free. APScheduler for in-app. GitHub Actions for CI/CD-style.

---

## COMPLETE ZERO-COST STACK SUMMARY

For a fully operational AI agent platform at $0/month (self-hosted):

```
Image Gen:     Pollinations.ai (cloud) or Stable Diffusion (local)
TTS:           edge-tts (cloud, free) or Piper (local)
STT:           faster-whisper (local) or Groq free tier (cloud)
LLM:           Google AI Studio + Groq + Ollama local
Search:        SearXNG (self-hosted) or DuckDuckGo
Email:         Gmail SMTP/IMAP
Messaging:     Telegram Bot API + Discord Webhooks
Vision:        LLaVA via Ollama or Moondream (local)
Documents:     PyMuPDF + Tesseract + Marker
Code Exec:     Judge0 (self-hosted or CE API)
Translation:   LibreTranslate (self-hosted)
Weather:       Open-Meteo
News:          Google News RSS
Finance:       yfinance
Embeddings:    nomic-embed-text via Ollama + ChromaDB
Storage:       Cloudflare R2 (10GB free)
Scheduling:    cron-job.org + APScheduler
```

**Total monthly cost: $0** (assuming you have a machine to run local models)

For cloud-only (no GPU), replace local models with free API tiers:
- LLM: Google AI Studio + Groq + Cloudflare Workers AI
- Vision: Gemini via AI Studio
- STT: Groq Whisper API
- Embeddings: Jina (1M free tokens) or Nomic (1M free tokens)

---

## KEY PYTHON PACKAGES TO INSTALL

```bash
# Core AI
pip install openai ollama google-generativeai groq

# Image
pip install diffusers torch pillow requests

# Audio
pip install edge-tts faster-whisper piper-tts

# Search & Web
pip install duckduckgo-search beautifulsoup4 requests

# Documents
pip install pymupdf pytesseract ocrmypdf pdfplumber python-docx marker-pdf

# Translation
pip install libretranslate argostranslate deep-translator

# Embeddings & Vector DB
pip install sentence-transformers chromadb faiss-cpu

# Data APIs
pip install yfinance

# Automation
pip install apscheduler celery

# Communication
pip install python-telegram-bot discord.py

# Utilities
pip install aiohttp httpx python-dotenv
```
