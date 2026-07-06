from fastapi import FastAPI
from prometheus_client import Counter, Gauge, make_asgi_app
from src.config import settings

# Prometheus Metrics Definitions
SOURCES_TRACKED = Gauge("sources_tracked_total", "Number of active tracked content sources")
POSTS_FETCHED = Counter("posts_fetched_total", "Total posts fetched from scrapers")
ADS_FILTERED = Counter("ads_filtered_total", "Total posts filtered as advertisement or spam")
DUPLICATES_BLOCKED = Counter("duplicates_blocked_total", "Total semantic duplicates blocked")
POSTS_PUBLISHED = Counter("posts_published_total", "Total posts successfully published")
AI_ERRORS = Counter("ai_errors_total", "Total LLM API call errors", ["provider", "method"])
AI_COST_ESTIMATE = Counter("ai_cost_estimate_usd", "Estimated cumulative cost of LLM calls in USD", ["provider"])
QUEUE_SIZE = Gauge("queue_size", "Current background queue length")

def track_ai_cost(provider: str, prompt: str, response: str) -> None:
    """
    Roughly estimates input and output token counts and calculates cumulative costs.
    """
    input_tokens = len(prompt.split()) * 1.3
    output_tokens = len(response.split()) * 1.3
    
    cost = 0.0
    if provider == "gemini":
        cost = (input_tokens * 1.25 + output_tokens * 5.0) / 1_000_000
    elif provider == "openai":
        cost = (input_tokens * 5.0 + output_tokens * 15.0) / 1_000_000
    elif provider == "claude":
        cost = (input_tokens * 3.0 + output_tokens * 15.0) / 1_000_000
        
    AI_COST_ESTIMATE.labels(provider=provider).inc(cost)

def setup_monitoring(app: FastAPI) -> None:
    # Mount Prometheus ASGI application directly onto /metrics
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)
