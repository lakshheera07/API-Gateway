# API Gateway

A robust API Gateway built with FastAPI featuring rate limiting, request logging, metrics collection, and middleware management.

## Features

- ✅ **Rate Limiting** - Sliding window rate limiter using Redis
- ✅ **Circuit Breaker** - Prevents cascading failures with automatic recovery
- ✅ **Exponential Backoff Retry** - Intelligent retry mechanism with exponential backoff
- ✅ **Request Logging** - Structured JSON logging with request context
- ✅ **Metrics** - Prometheus metrics for monitoring
- ✅ **Grafana Dashboard** - Real-time monitoring with detailed metrics and gauges
- ✅ **Request Context** - Request ID tracking across the system
- ✅ **Health Check** - Built-in health check endpoint

## Architecture

```mermaid
graph TB
    subgraph Gateway["API Gateway"]
        app["FastAPI App"]
        middleware["Middleware"]
        routes["Routes"]
    end
    
    subgraph Services["Services"]
        ctx["Request Context"]
        logging["Logging"]
        metrics["Metrics"]
        ratelimit["Rate Limiter"]
        breaker["Circuit Breaker"]
    end
    
    subgraph External["External"]
        redis["Redis"]
        downstream["Downstream Services"]
    end
    
    app --> middleware
    middleware --> ctx
    middleware --> logging
    middleware --> metrics
    middleware --> ratelimit
    middleware --> breaker
    ratelimit --> redis
    breaker --> redis
    app --> routes
    routes --> downstream
    breaker --> downstream
```

## Request Flow Diagram

```mermaid
flowchart TD
    A["Incoming Request"] --> B["Generate Request ID"]
    B --> C["Extract Client IP"]
    C --> D["Check Rate Limit"]
    D -->|Rate Limited| E["Return 429 Status"]
    E --> F["Log Rate Limit Error"]
    F --> Z1["End"]
    D -->|Not Limited| G["Check Circuit Breaker"]
    G -->|Circuit Open| H["Return 503 Status"]
    H --> I["Log Circuit Open"]
    I --> Z2["End"]
    G -->|Circuit Closed| J["Record Request Start"]
    J --> K["Process Request"]
    K --> L{"Exception?"}
    L -->|Yes| M["Log Exception"]
    M --> N["Record Failure"]
    N --> Z3["End"]
    L -->|No| O["Calculate Latency"]
    O --> P["Record Success"]
    P --> Q["Update Prometheus Metrics"]
    Q --> R["Add Response Headers"]
    R --> S["Log Request Success"]
    S --> T["Return Response"]
    T --> Z4["End"]
```

## Project Structure

```
apiGateway/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry point
│   ├── cache/
│   │   └── redis_client.py     # Redis connection management
│   ├── core/
│   │   ├── config.py           # Configuration settings
│   │   ├── logging.py          # Logging setup
│   │   ├── metrics.py          # Prometheus metrics
│   │   └── middleware.py       # Request middleware
│   ├── gateway/
│   │   └── rate_limiter.py     # Rate limiting logic
│   ├── observability/
│   ├── services/
│   └── utils/
├── tests/
│   ├── test_health.py
│   ├── test_metrics.py
│   └── test_rate_limiter.py
├── docker/
│   └── docker-compose.yml      # Docker composition
├── requirements.txt            # Python dependencies
└── Readme.md                   # This file
```

## Installation

### Prerequisites
- Python 3.10+
- Redis 7+
- Docker & Docker Compose (optional)

### Local Setup

1. **Clone the repository**
```bash
git clone https://github.com/lakshheera07/API-Gateway.git
cd apiGateway
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Start Redis** (if not using Docker)
```bash
redis-server
```

## Running the Project

### Local Development
```bash
python -m app.main
```
The API will be available at `http://127.0.0.1:8000`

### With Docker
```bash
docker-compose -f docker/docker-compose.yml up
```

## API Endpoints

### Health Check
```bash
curl http://127.0.0.1:8000/health
```

**Response:**
```json
{"status": "ok"}
```

### Metrics
```bash
curl http://127.0.0.1:8000/metrics
```

Returns Prometheus-formatted metrics.

## Configuration

Update settings in `app/core/config.py`:

```python
class Settings(BaseSettings):
    redis_host: str = "localhost"
    redis_port: int = 6379
    RATE_LIMIT_REQUESTS: int = 100          # Requests per window
    RATE_LIMIT_WINDOW_SEC: int = 60         # Time window in seconds
    CIRCUIT_FAILURE_THRESHOLD: int = 5      # Failures before circuit opens
    CIRCUIT_RECOVERY_TIMEOUT: int = 30      # Seconds before attempting recovery
```

## Circuit Breaker

The Circuit Breaker pattern prevents cascading failures by monitoring downstream service health:

### States
- **CLOSED** (Normal) - Requests flow normally, failures are counted
- **OPEN** (Failed) - Requests are rejected immediately, returns HTTP 503
- **HALF_OPEN** (Recovering) - Limited requests allowed to test service recovery

### Configuration
```python
CIRCUIT_FAILURE_THRESHOLD: int = 5      # Open circuit after 5 failures
CIRCUIT_RECOVERY_TIMEOUT: int = 30      # Wait 30 seconds before retry
```

### How It Works
1. Track failures for each service
2. When failures exceed threshold → Circuit opens
3. Reject all requests with HTTP 503 (Service Unavailable)
4. After timeout, allow one request to test recovery
5. If successful → Circuit closes, resume normal operation
6. If fails → Circuit stays open, retry after timeout

### Usage Example
```python
from app.gateway.circuit_breaker import CircuitBreaker

breaker = CircuitBreaker("downstream_service")

if breaker.is_open():
    raise HTTPException(status_code=503, detail="Circuit open")

try:
    response = call_downstream_service()
    breaker.record_success()
except Exception as e:
    breaker.record_failure()
    raise
```

### Testing Circuit Breaker
```bash
# Simulate failures to trigger circuit breaker
curl -X POST http://127.0.0.1:8000/simulate-failure

# Check circuit status
curl http://127.0.0.1:8000/health  # Should return 503 if circuit is open
```

## Exponential Backoff Retry

The API Gateway implements intelligent retry logic with exponential backoff to handle transient failures:

### How It Works
- **Base Delay**: Starts with 1 second
- **Multiplier**: Doubles on each retry (1s → 2s → 4s → 8s)
- **Max Retries**: Configurable (default: 3)
- **Jitter**: Optional random jitter to prevent thundering herd

### Configuration
```python
RETRY_MAX_ATTEMPTS: int = 3          # Maximum number of retries
RETRY_BASE_DELAY: float = 1.0        # Initial delay in seconds
RETRY_MAX_DELAY: float = 30.0        # Maximum delay in seconds
RETRY_EXPONENTIAL_BASE: float = 2.0  # Exponential multiplier
```

### Usage Example
```python
from app.gateway.retry import retry_request

try:
    response = await retry_request(
        "http://downstream-service/endpoint",
        method="GET",
        max_retries=3
    )
    return response.json()
except Exception as e:
    logger.error(f"Request failed after retries: {e}")
    raise
```

### Retry Flow
```
Attempt 1 (immediate)
    ↓ Failure
Wait 1s (2^0)
Attempt 2
    ↓ Failure
Wait 2s (2^1)
Attempt 3
    ↓ Failure
Wait 4s (2^2)
Attempt 4
    ↓ Success/Failure → Return
```

### Testing Exponential Backoff
```bash
# Enable failure simulation
curl -X POST http://127.0.0.1:8000/simulate-failure

# Make proxy request (will retry with backoff)
curl http://127.0.0.1:8000/proxy

# Disable failure simulation
curl -X POST http://127.0.0.1:8000/simulate-recovery
```

## Rate Limiting

The API Gateway implements a **sliding window rate limiter** using Redis:

- **Algorithm**: Sliding window with sorted sets
- **Storage**: Redis
- **Default Limit**: 100 requests per 60 seconds
- **Response**: HTTP 429 when limit exceeded

### How It Works
1. For each client IP, maintain a sorted set of request timestamps
2. Remove old timestamps outside the window
3. Check if current request count exceeds limit
4. Add current timestamp to the set

### Test Rate Limiting
```bash
# Bash
for i in {1..120}; do curl -s http://127.0.0.1:8000/health; done

# PowerShell
for ($i=1; $i -le 120; $i++) { Invoke-WebRequest -Uri http://127.0.0.1:8000/health }

# Windows CMD
for /L %i in (1,1,120) do curl -s http://127.0.0.1:8000/health
```

You should see 429 (Too Many Requests) responses after 100 requests.

## Testing

Run all tests:
```bash
pytest
```

Run specific tests:
```bash
pytest tests/test_health.py -v
pytest tests/test_rate_limiter.py -v
pytest tests/test_circuit_breaker.py -v
pytest tests/test_metrics.py -v
```

## Logging

All requests are logged with structured JSON output including:
- Request ID
- Timestamp
- HTTP method and endpoint
- Response status code
- Processing latency
- Request details

## Metrics

Prometheus metrics are collected for:
- `http_requests_total` - Total HTTP requests by method, endpoint, status
- `http_request_latency_ms` - Request latency in milliseconds with histograms

Access metrics at `/metrics` endpoint.

## Grafana Dashboard

A comprehensive Grafana dashboard is included for real-time monitoring of the API Gateway.

### Dashboard Features

**Endpoint Request Gauges (Top Row)**
- Visual gauges for each endpoint showing request count in the last 5 minutes
- Color-coded thresholds:
  - 🟢 Green: Normal traffic
  - 🟡 Yellow: Moderate traffic
  - 🔴 Red: High traffic/concerning levels

Endpoints monitored:
- `GET /health` - Health check endpoint
- `GET /metrics` - Prometheus metrics
- `GET /proxy` - Proxy/gateway endpoint
- `GET /downstream` - Mock downstream service
- `POST /simulate-failure` - Test failure injection
- `POST /simulate-recovery` - Test failure recovery

**Time Series Charts**

1. **Request Rate by Endpoint** (per second)
   - Shows throughput for each endpoint over time
   - Helps identify traffic patterns and spikes

2. **P95 Latency by Endpoint** (milliseconds)
   - 95th percentile latency for each endpoint
   - Identifies performance issues

3. **Error Rate by Endpoint** (per second)
   - Separates 4xx and 5xx errors
   - Tracks error trends

4. **Circuit Breaker State Changes**
   - Monitors circuit breaker transitions
   - Identifies when services are failing

### Accessing the Dashboard

1. **Start the services**:
```bash
docker-compose -f docker/docker-compose.yml up
```

2. **Open Grafana**:
   - URL: `http://localhost:3000`
   - Default credentials: `admin` / `admin`

3. **View the dashboard**:
   - Name: "API Gateway Metrics Dashboard"
   - Auto-refreshes every 5 seconds
   - Data window: Last 1 hour

### Dashboard Configuration

The dashboard is defined in `app/observability/grafanaDashboard.json`:
- **Refresh Rate**: 5 seconds (configurable)
- **Time Range**: Last 1 hour
- **Data Source**: Prometheus
- **Visualization Types**: Gauges, Time Series, Stats

### Interpreting the Dashboard

**Green Gauges**: 
- Traffic is normal and within expected thresholds
- System is operating optimally

**Yellow Gauges**: 
- Elevated traffic or concerning metrics
- May indicate increased load or potential issues

**Red Gauges**: 
- High traffic or error rates
- Investigate immediately for service degradation

**Rising Latency Lines**: 
- Performance degradation detected
- Check downstream services or increase resources

**Error Rate Spikes**: 
- Multiple failures occurring
- Circuit breaker may open soon

### Prometheus Queries

Common queries for custom monitoring:

```promql
# Total requests per endpoint (5 minutes)
increase(http_requests_total[5m])

# Request rate per second
rate(http_requests_total[1m])

# P95 latency
histogram_quantile(0.95, rate(http_request_latency_ms_bucket[5m]))

# Error rate (4xx and 5xx)
rate(http_requests_total{status_code=~"[45].."}[1m])

# Circuit breaker state changes
increase(circuit_breaker_state_changes_total[5m])
```

## Error Handling

- **429 Too Many Requests** - Rate limit exceeded
- **500 Internal Server Error** - Unhandled exceptions with logging
- **422 Unprocessable Entity** - Validation errors

## Contributing

1. Create a feature branch: `git checkout -b feature/your-feature`
2. Commit changes: `git commit -am 'Add feature'`
3. Push to branch: `git push origin feature/your-feature`
4. Submit a pull request


## Contact

For issues and questions, please create a GitHub issue at [API-Gateway Issues](https://github.com/lakshheera07/API-Gateway/issues)

---

**Last Updated**: February 5, 2026
**Features**: Rate Limiting, Circuit Breaker, Exponential Backoff, Prometheus Metrics, Grafana Dashboard
