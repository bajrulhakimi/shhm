import time

from fastapi import Request
from prometheus_client import Counter, Histogram
from starlette.middleware.base import BaseHTTPMiddleware

HTTP_REQUESTS = Counter(
    "stockbot_http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)
HTTP_LATENCY = Histogram(
    "stockbot_http_request_duration_seconds",
    "HTTP request duration",
    ["method", "path"],
)
AI_PROVIDER_REQUESTS = Counter(
    "stockbot_ai_provider_requests_total",
    "AI provider request outcomes",
    ["provider", "status"],
)
STOCK_DATA_REQUESTS = Counter(
    "stockbot_stock_data_requests_total",
    "Stock data request outcomes",
    ["status"],
)
SCAN_JOBS = Counter(
    "stockbot_scan_jobs_total",
    "Scan job outcomes",
    ["status"],
)


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        started = time.monotonic()
        response = await call_next(request)
        path = request.scope.get("route").path if request.scope.get("route") else request.url.path
        HTTP_REQUESTS.labels(request.method, path, response.status_code).inc()
        HTTP_LATENCY.labels(request.method, path).observe(time.monotonic() - started)
        return response
