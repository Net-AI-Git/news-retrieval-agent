---
name: create-applicative-health-check-monitoring
description: Add the standardized monitoring stack (`/monitor/applicative-health-check`, `/monitor/redis-queues-check`) + Megi submission package to a microservice from scratch.
---

# /create-applicative-health-check-monitoring

Argument: the microservice directory to add monitoring to (e.g. `<microservice-name>`). If omitted, ask which microservice.

## Canonical Reference (mirror exactly)

If the workspace already contains one or more microservices that implement this monitoring stack, they are the **canonical reference** — every new microservice MUST replicate their `routes/monitor.py`, `services/healthcheck_service.py`, `schemas/monitor.py`, and `repositories/*.is_healthy*` shape line-for-line. Read any existing implementation before writing anything; if none exists in the workspace yet, build the shapes exactly as specified in the sections below.

Every `OpenSearchRepository.log_event(...)` call site (STARTING / FINISHED / ERROR, content payload, level) MUST appear at the **exact same position** in the new code as it does in the reference files. The `process` field is auto-detected from the calling function name — DO NOT pass `process=` manually.

## Goal

Add an applicative health-check API + a Redis-queue depth API + a Megi submission package that:
- exposes two `GET` endpoints under `/monitor`,
- runs every per-component check in parallel inside `HealthCheckService.run_health_check`,
- runs the Redis-queue depth lookups inside `RedisRepository.get_queue_statuses` (Redis logic stays in the Redis repository — it is **not** a health check),
- returns the existing `ServiceStatus` / `RedisQueueStatus` Pydantic shape,
- surfaces every failure both in OpenSearch **and** inside `/applicative-health-check` (`description=[repr(err)]`),
- never crashes the process — every probe + entry-point owns its own `try/except`,
- produces a ready-to-submit Megi package under `<microservice>/monitoring/` (README.md, megi_form_values.md, alerts_specification.md, opensearch_queries.md, generate_excel.py + xlsx).

## Allowed Probe Categories (closed list — DO NOT add new ones)

The applicative health-check is **strictly limited** to these five categories. The HTTP 200 of `/applicative-health-check` itself is the "Service availability" signal — no separate probe.

1. **DB connectivity** — `OracleRepository.is_healthy*` (one method per DB connection).
2. **Service availability** — implicit, satisfied by the endpoint returning HTTP 200.
3. **Azure LLM connectivity** — `services/azure_healthcheck_service.is_healthy` (Azure OpenAI GPT or Audio).
4. **CRM connectivity** — `CrmRepository.is_healthy`.
5. **Redis connectivity** — `RedisRepository.is_healthy`.

Anything else (file storage, Kafka, S3, third-party REST, etc.) is **out of scope** for this command. Do NOT add probes for it.

## File Layout (created by this command)

For a microservice rooted at `<service>/<service_pkg>/`:

```
<service_pkg>/
├── routes/
│   └── monitor.py                              ← FastAPI router (NEW)
├── schemas/
│   └── monitor.py                              ← `ServiceStatus` + `RedisQueueStatus` Pydantic models (NEW)
├── services/
│   ├── healthcheck_service.py                  ← single run_health_check (NEW)
│   └── azure_healthcheck_service.py            ← only if the service talks to Azure OpenAI (NEW, optional)
└── repositories/
    ├── redis_repository.py                     ← add `is_healthy(...)` + `get_queue_statuses(flow_id)` (imports `RedisQueueStatus` from `schemas/monitor.py`)
    ├── oracle_repository.py                    ← add `is_healthy*(...)` per DB connection
    └── crm_repository.py                       ← add `is_healthy(...)` (only if CRM is used)
```

Wire the router in `<service_pkg>/routes/api.py`:
```python
from ..routes import ping, monitor
api_router.include_router(monitor.router)
```

## Return Contract (strict — copy verbatim)

- Every probe (Oracle, Redis, CRM, Azure, file storage) → `(is_healthy: bool, error_message: str)`
- Success → `error_message=""`. Failure → `error_message=repr(err)`, `is_healthy=False`.

`RedisQueueStatus` only carries `service_name` + `queue_depth` — Redis-queue depth is **not** a health probe and has no `is_ok` / `description`.

## Procedure

### 1. Build the probes (one per dependency)

Each probe lives next to its dependency (Oracle in `oracle_repository.py`, Redis in `redis_repository.py`, CRM in `crm_repository.py`, Azure OpenAI in `services/azure_healthcheck_service.py`). Only the categories listed in **Allowed Probe Categories** above are in scope.

Canonical shape — copy and adapt only the body inside `try`:
```python
@staticmethod
def is_healthy(flow_id):
    OpenSearchRepository.log_event(status="STARTING", content={...}, flow_id=flow_id, level="INFO")
    is_healthy = False
    error_message = ""
    try:
        <probe logic>
        is_healthy = <derived bool>
    except Exception as err:
        error_message = repr(err)
        OpenSearchRepository.log_event(status="ERROR", content={"error": error_message, ...}, flow_id=flow_id, level="ERROR")
    OpenSearchRepository.log_event(status="FINISHED", content={..., "is_healthy": is_healthy}, flow_id=flow_id, level="INFO")
    return is_healthy, error_message
```

Probe-specific rules:
- **Oracle** (per DB connection — e.g. `is_healthy_<db_name>`): `row_count = connection.execute(text("SELECT COUNT(*) FROM <main_table>")).scalar()` then `is_healthy = row_count > 0`. Never `SELECT 1 FROM DUAL`.
- **Redis** (`RedisRepository.is_healthy(queue_id, flow_id)`): inside `try` call `RedisRepository.r.llen(f"queue:{queue_id}")` as the connectivity probe (discard return value). Returns `is_healthy, error_message` — same shape as every other probe.
- **CRM**: `POST <CRM_URL>` with `json={}` and `timeout=HEALTH_CHECK_TIMEOUT_SECONDS`; treat `status_code >= 500` as failure.
- **Azure OpenAI**: probe lives in `services/azure_healthcheck_service.py` (NOT in a repository). Either a `GET /openai/models?api-version=...` against the endpoint, or a `chat.completions.create` with a one-token prompt — match the existing client wiring.

The probe MUST NOT `raise`. It absorbs every exception.

### 2. Define the Pydantic models (`schemas/monitor.py`)

Both monitoring DTOs live in `<service_pkg>/schemas/monitor.py` — never inside repositories or services. Verbatim:

```python
from typing import Optional

from pydantic import BaseModel


class ServiceStatus(BaseModel):
    service_name: str
    is_ok: Optional[bool] = None
    description: Optional[list[str]] = None


class RedisQueueStatus(BaseModel):
    service_name: str
    queue_depth: Optional[int] = None
```

### 3. Build the Redis-queue orchestrator (inside `redis_repository.py`)

`get_queue_statuses` lives in `repositories/redis_repository.py` — Redis-queue depth is a Redis concern, not a health-check concern. The model is **imported** from `schemas/monitor.py`.

```python
from <service_pkg>.schemas.monitor import RedisQueueStatus


class RedisRepository:
    # ... existing fields + is_healthy(...) ...

    @staticmethod
    def get_queue_statuses(flow_id):
        OpenSearchRepository.log_event(status="STARTING", content={}, flow_id=flow_id, level="INFO")
        queue_statuses = []
        try:
            <queue>_depth = RedisRepository.r.llen(f"queue:{<QUEUE_CONST>}")
            # repeat per queue if more than one
            queue_statuses = [RedisQueueStatus(service_name="Redis Queue (<QUEUE_CONST_NAME>)", queue_depth=<queue>_depth), ...]
        except Exception as err:
            OpenSearchRepository.log_event(status="ERROR", content={"error": repr(err)}, flow_id=flow_id, level="ERROR")
        OpenSearchRepository.log_event(status="FINISHED", content={"results_count": len(queue_statuses)}, flow_id=flow_id, level="INFO")
        return queue_statuses
```

Queue constants come from the microservice's own source of truth — `conts.py` if defined there, otherwise from `redis_repository.py` itself (e.g. `REDIS_QUEUE = os.getenv("REDIS_QUEUE")` at module scope when no `conts.py` entry exists). Do NOT duplicate the env lookup in services.

### 4. Build `services/healthcheck_service.py`

`ServiceStatus` is **imported** from `schemas/monitor.py` — no model is defined in this file.

```python
from concurrent.futures import ThreadPoolExecutor

from dotenv import load_dotenv

from <service_pkg>.conts import <QUEUE_CONST>  # only when consumed inside run_health_check
from <service_pkg>.repositories.<dep>_repository import <Dep>Repository
from <service_pkg>.repositories.redis_repository import RedisRepository
from <service_pkg>.repositories.opensearch_repository import OpenSearchRepository
from <service_pkg>.schemas.monitor import ServiceStatus
from <service_pkg>.services import azure_healthcheck_service  # only when Azure is in scope

load_dotenv()


class HealthCheckService:

    @staticmethod
    def run_health_check(flow_id):
        OpenSearchRepository.log_event(status="STARTING", content={}, flow_id=flow_id, level="INFO")
        services_status = []
        try:
            with ThreadPoolExecutor(max_workers=5) as executor:
                <dep1>_future = executor.submit(<Dep1>Repository.is_healthy, flow_id)
                <dep2>_future = executor.submit(<Dep2>Repository.is_healthy, flow_id)
                redis_future = executor.submit(RedisRepository.is_healthy, <QUEUE_CONST>, flow_id)
                <dep1>_ok, <dep1>_err = <dep1>_future.result()
                <dep2>_ok, <dep2>_err = <dep2>_future.result()
                redis_ok, redis_err = redis_future.result()
            services_status = [ServiceStatus(service_name="<label1>", is_ok=<dep1>_ok, description=[<dep1>_err] if <dep1>_err else []), ServiceStatus(service_name="<label2>", is_ok=<dep2>_ok, description=[<dep2>_err] if <dep2>_err else []), ServiceStatus(service_name="Redis", is_ok=redis_ok, description=[redis_err] if redis_err else [])]
        except Exception as err:
            OpenSearchRepository.log_event(status="ERROR", content={"error": repr(err)}, flow_id=flow_id, level="ERROR")
        OpenSearchRepository.log_event(status="FINISHED", content={"results_count": len(services_status)}, flow_id=flow_id, level="INFO")
        return services_status
```

Rules:
- Single `run_health_check` method — no `test_<dependency>` helper functions, no `run_redis_queues_check` method.
- `ThreadPoolExecutor` runs every probe in parallel; results are unpacked inline.
- Redis future returns 2 values — unpack `is_healthy_bool, error_message` (same shape as every other probe). Queue depths are exposed by `/redis-queues-check` separately.
- The `services_status` list is built in **one statement** on a single line.

### 5. Build `routes/monitor.py`

Verbatim shape (only the imports change per microservice):
```python
from uuid import uuid4

from fastapi import APIRouter

from <service_pkg>.repositories.redis_repository import RedisRepository
from <service_pkg>.repositories.opensearch_repository import OpenSearchRepository
from <service_pkg>.schemas.monitor import RedisQueueStatus, ServiceStatus
from <service_pkg>.services.healthcheck_service import HealthCheckService

router = APIRouter(prefix="/monitor", tags=["monitor"])


@router.get("/applicative-health-check", response_model=list[ServiceStatus])
def applicative_health_check():
    flow_id = str(uuid4())
    OpenSearchRepository.log_event(status="STARTING", content={}, flow_id=flow_id, level="INFO")
    results = HealthCheckService.run_health_check(flow_id)
    OpenSearchRepository.log_event(status="FINISHED", content={"results_count": len(results)}, flow_id=flow_id, level="INFO")
    return results


@router.get("/redis-queues-check", response_model=list[RedisQueueStatus])
def redis_queues_check():
    flow_id = str(uuid4())
    OpenSearchRepository.log_event(status="STARTING", content={}, flow_id=flow_id, level="INFO")
    results = RedisRepository.get_queue_statuses(flow_id)
    OpenSearchRepository.log_event(status="FINISHED", content={"results_count": len(results)}, flow_id=flow_id, level="INFO")
    return results
```

Notes:
- `ServiceStatus` and `RedisQueueStatus` are both imported **from `schemas/monitor.py`** — never from `redis_repository` or `healthcheck_service`.
- `/redis-queues-check` calls `RedisRepository.get_queue_statuses(flow_id)` directly — `HealthCheckService` is not involved.

### 6. Wire the router

In `<service_pkg>/routes/api.py` add `monitor` to the imports and register `api_router.include_router(monitor.router)` next to `ping`.

### 7. Verify

- `python -m py_compile` on every file touched → exit 0.
- Boot the service. Hit:
  - `GET http://127.0.0.1:<port>/api/monitor/applicative-health-check`
  - `GET http://127.0.0.1:<port>/api/monitor/redis-queues-check`
- Expected JSON (success):
  - `/applicative-health-check`: every entry `is_ok=true`, `description=[]`.
  - `/redis-queues-check`: every entry `{ "service_name": "Redis Queue (<QUEUE_CONST_NAME>)", "queue_depth": <int> }` — no `is_ok`, no `description`.
- Expected JSON (forced failure):
  - `/applicative-health-check`: `is_ok=false`, `description=["<repr-of-err>"]`.
  - `/redis-queues-check`: returns `[]` (the OpenSearch ERROR log carries `repr(err)`).

### 8. Build the Megi submission package (`<microservice>/monitoring/`)

Templates live in this skill directory — copy each one verbatim into the new microservice's `monitoring/` folder, then substitute placeholders with the values gathered from the user.

Files to copy:
- [`README.md`](README.md) → `<microservice>/monitoring/README.md`
- [`megi_form_values.md`](megi_form_values.md) → `<microservice>/monitoring/megi_form_values.md`
- [`alerts_specification.md`](alerts_specification.md) → `<microservice>/monitoring/alerts_specification.md`
- [`opensearch_queries.md`](opensearch_queries.md) → `<microservice>/monitoring/opensearch_queries.md`
- [`generate_excel.py`](generate_excel.py) → `<microservice>/monitoring/generate_excel.py`

Placeholders to substitute (ask the user for any unknown value — do NOT guess):

| Placeholder | Meaning | Source |
|---|---|---|
| `<PROJECT_DISPLAY_NAME>` | Hebrew/English project name (e.g. `<project display name>`) | Ask user |
| `<microservice_slug>` | Repo directory name (e.g. `<microservice-name>`) | Command argument |
| `<N>` | Number of microservices in the project | Ask user |
| `<ALERT_NAME>` | `<ORG>_<PROJECT>_<SERVICE>_HEALTH` shape | Ask user |
| `<comma-separated dependency labels>` | The same `service_name` labels emitted by `HealthCheckService.run_health_check` | Step 4 output |
| `<REDIS_QUEUE_CONST_NAMES>` | The Redis queue constant name(s) wired in Step 3 | Step 3 output |
| `<PRODUCTION_URL_BASE>` | OpenShift route base URL | Ask user |
| `<OPENSHIFT_PROJECT>` / `<OPENSHIFT_APP>` | OpenShift project + app names | Ask user |
| `<OPENSEARCH_LOG_INDEX_PATTERN>` / `<OTEL_SERVICE_NAME>` | OpenSearch log index pattern + OpenTelemetry service name | Ask user |
| `<TEAM_NAME>` / `<CONTACT_NAME>` / `<CONTACT_EMAIL>` / `<CONTACT_PHONE>` / `<NOTIFICATION_GROUP>` / `<NOC_CONTACT_EMAIL>` | Owning team + on-call contact metadata | Ask user |

After substitution, run `python <microservice>/monitoring/generate_excel.py` from the microservice root to produce `<microservice_slug>_alerts.xlsx`. Confirm the script exits 0 and the xlsx file appears next to it.

## Hard Prohibitions

- Do NOT add new fields to `ServiceStatus` / `RedisQueueStatus` — the API contract is frozen (`RedisQueueStatus` is `service_name` + `queue_depth` **only**).
- Do NOT define `ServiceStatus` or `RedisQueueStatus` anywhere except `<service_pkg>/schemas/monitor.py` — repositories and services **import** them.
- Do NOT put any Redis-queue listing logic inside `services/healthcheck_service.py` — Redis lives in `repositories/redis_repository.py`.
- Do NOT re-introduce a `run_redis_queues_check` method or per-helper `test_<dependency>` functions in `HealthCheckService`.
- Do NOT introduce per-helper `try/except` inside `run_health_check` or `get_queue_statuses` — each has exactly one top-level `try/except`.
- Do NOT make probes `raise` — they always return.
- Do NOT relocate `azure_healthcheck_service.py` into `repositories/`. Azure OpenAI probe stays under `services/`.
- Do NOT change CRM (`POST {}`) or Azure (`"HI"` / `models?api-version=...`) probe payloads when adapting an existing service.
- Do NOT add probes outside the five allowed categories (DB / service-availability / Azure LLM / CRM / Redis). File storage, Kafka, S3, generic REST, etc. are explicitly out of scope.
- Do NOT add type hints, docstrings, or comments to the new code.
- Do NOT reposition, rename, or omit any `OpenSearchRepository.log_event(...)` call in the new code — each STARTING / FINISHED / ERROR call MUST appear at the same site as in the canonical reference files.
- Do NOT rewrite the Megi templates in this skill directory — copy them verbatim, only substitute the listed placeholders.
- Do NOT regenerate xlsx files by hand — always run [`generate_excel.py`](generate_excel.py).

## When to Ask Instead of Acting

- The microservice's "main table" per Oracle DB connection is unclear — there must be one obvious `<schema>.<table>` to `COUNT(*)` against per DB.
- The microservice has a dependency outside the five allowed categories (e.g. Kafka, S3, file storage, third-party REST) — by default, do NOT add a probe for it. Confirm with the user before deviating.
- The microservice has zero Redis queues — `redis-queues-check` should still exist but `RedisRepository.get_queue_statuses` returns `[]`. Confirm with the user.
- The Redis queue env var has no constant in `conts.py` — confirm whether to add it there or read it from `redis_repository.py` module scope (the producer pattern: `REDIS_QUEUE = os.getenv("REDIS_QUEUE")` at the top of `redis_repository.py`).
- Any Megi-package placeholder is unknown (`<PRODUCTION_URL_BASE>`, `<OPENSHIFT_PROJECT>`, `<OPENSHIFT_APP>`, `<OPENSEARCH_LOG_INDEX_PATTERN>`, `<OTEL_SERVICE_NAME>`, `<ALERT_NAME>`, `<CONTACT_*>`, `<NOTIFICATION_GROUP>`, `<NOC_CONTACT_EMAIL>`, etc.) — ask the user; do NOT guess or copy values from another existing project.

Ask one focused question, then stop.
