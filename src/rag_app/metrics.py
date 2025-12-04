# src/rag_app/metrics.py
from prometheus_client import Counter, Histogram, Gauge

# Labels: model_id, endpoint (e.g., generate), status (success/fail)
LLM_LATENCY_SECONDS = Histogram(
    "llm_request_latency_seconds",
    "Latency of LLM requests in seconds",
    ["model_id", "endpoint", "status"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 30)
)

LLM_REQUESTS_TOTAL = Counter(
    "llm_requests_total",
    "Total number of LLM requests",
    ["model_id", "endpoint", "status"]
)

LLM_TOKENS_TOTAL = Counter(
    "llm_tokens_total",
    "Total tokens sent/received to/from LLM",
    ["model_id", "direction"]  # direction: prompt | completion | total
)

LLM_COST_TOTAL = Counter(
    "llm_cost_total_usd",
    "Estimated cost of LLM usage in USD",
    ["model_id", "cost_model"]  # cost_model: per_token or custom
)

# keep a gauge of last latency & last request duration for quick single-value panels
LLM_LAST_LATENCY = Gauge(
    "llm_last_latency_seconds",
    "Last observed LLM request latency in seconds",
    ["model_id", "endpoint", "status"]
)
