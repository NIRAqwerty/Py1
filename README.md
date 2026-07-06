# AI-Driven Telegram Channel Management System

A highly scalable, production-grade, asynchronous system designed to scrape content sources (e.g., Telegram channels), perform semantic filtering, deduplicate events using `pgvector` semantic similarity searches, rewrite articles with high factual accuracy, process/recreate clean image attachments, and auto-publish or route to Human Review based on confidence levels.

---

## Technical Architecture (Clean Architecture + DDD)

The codebase is built on **Domain-Driven Design (DDD)** and **Clean Architecture** patterns, isolating business rules from infrastructure details:

```
src/
├── domain/            # Pure Python business models and repository abstractions
│   ├── entities.py    # Article, Source, Publication, HumanReviewTask, User
│   └── repositories.py # Interfaces defining data retrieval contracts
├── application/       # Application logic and use-case orchestrators
│   └── interfaces/    # Orchestrator and plugin contracts
├── infrastructure/    # Framework-specific database mappings, external APIs, queue workers
│   ├── database/      # SQLAlchemy 2.0 ORM Models, Session maker, and Repositories
│   ├── ai/            # LLM Adapters (Gemini, Claude, OpenAI, Ollama) and AIOrchestrator
│   ├── checkers/      # Quality assurance checks (Spam, toxicity, duplicates, grammar)
│   ├── plugins/       # Content scrapers (Telegram Source plugin using Telethon)
│   ├── queue/         # Background async queue (ARQ configuration & job dispatcher)
│   ├── monitoring.py  # Prometheus exporter dashboard setup
│   └── security.py    # JWT, password hashing, and RBAC utilities
├── api/               # API Router and FastAPI controllers for Human Review Panel
└── worker.py          # Background worker entry point defining tasks
```

---

## Getting Started

### 1. Requirements
- Docker and Docker Compose
- Python 3.11+ (if running locally)

### 2. Environment Variables (.env)
Copy the environment variables template and configure your secrets:
```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/telegram_ai
REDIS_URL=redis://localhost:6379/0

# LLM APIs
GEMINI_API_KEY=your_gemini_api_key
OPENAI_API_KEY=your_openai_api_key
CLAUDE_API_KEY=your_claude_api_key

# Telegram Scraper (Telethon API credentials)
TELEGRAM_API_ID=123456
TELEGRAM_API_HASH=your_telegram_api_hash

# Telegram Publisher Bot
TELEGRAM_BOT_TOKEN=your_bot_token
```

### 3. Running via Docker Compose
Run the entire production stack (App API, Worker Queue, DB + pgvector, Redis, Prometheus, Grafana) with a single command:
```bash
docker-compose up --build
```
On startup:
- The database schema is fully updated via automatic migrations.
- Default authentication credentials are seeded if empty:
  - **Admin**: `admin` / `admin123`
  - **Operator**: `operator` / `operator123`

### 4. Running Tests
To run unit and integration tests:
```bash
pytest -v tests/
```

---

## Core Features & Workflows

1. **Scraping**: Active sources (defined in DB config) are fetched every `check_interval` seconds by the `fetch_sources_task` cron job.
2. **Quality Checkers**: Raw articles pass through independent checkers:
   - *Ad & Spam Detector*: Blocks promotions, coupon codes, casino/crypto referral links.
   - *Duplicate Detector*: Runs a `pgvector` HNSW index cosine distance check against existing post embeddings.
   - *Fact Checker*: Inspects for internal contradictions or hallucinations.
   - *Toxicity & NSFW Checker*: Identifies vulgar language or adult themes.
   - *Image Quality Checker*: Vision-checks photos for text overlays, low-res issues, or watermarks.
3. **Double-Pass Rewriting**: Passes raw text to an LLM to (1) extract dry facts, and (2) compile a polished Telegram post in a clean, modern, human voice.
4. **Image Pipeline**: Automatically illustrates text-only posts or recreates unique, logo-free illustrations for posts containing source images.
5. **Human Review Panel**: Articles scoring below confidence threshold (90%) are held as `REVIEW` in `human_review_tasks`. Operators can approve, reject, or edit drafts via the API. Approval triggers immediate publication.
