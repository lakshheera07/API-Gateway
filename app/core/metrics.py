from prometheus_client import Counter, Histogram


REQUEST_COUNT = Counter(
    'http_requests_total', 'Total HTTP Requests',
    ['method', 'endpoint', 'http_status'],

)

REQUEST_LATENCY = Histogram(
    "http_request_latency_ms",
    "HTTP Request Latency in milliseconds",
    ['method', 'endpoint'],
    buckets=(5, 10, 25, 50, 100, 250, 500, 1000),
)
