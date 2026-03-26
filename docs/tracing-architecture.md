# Application Tracing Architecture

This document describes how the sample applications in this stack connect to Grafana Tempo for distributed tracing.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              Grafana Dashboard                                   │
│                     (Service Map, TraceQL, Metrics)                            │
└─────────────────────────────────────────────────────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              Tempo (Tracing Backend)                            │
│                    http://tempo.observability.svc:3200                          │
│                                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐        │
│  │ Distributor │─▶│  Ingester   │  │ Query Front  │  │   Querier     │        │
│  │ (OTLP :4318)│  │             │  │   :3200      │  │               │        │
│  └─────────────┘  └─────────────┘  └──────────────┘  └───────────────┘        │
│        │                                                                        │
│        ▼                                                                        │
│  ┌──────────────────────────────┐                                               │
│  │    Metrics Generator         │                                               │
│  │  - service-graphs            │───▶ Mimir (Prometheus)                        │
│  │  - span-metrics              │                                               │
│  │  - local-blocks              │                                               │
│  └──────────────────────────────┘                                               │
└─────────────────────────────────────────────────────────────────────────────────┘
                                         │
        ┌─────────────────────────────────┬────────────────────────────────┐
        ▼                                 ▼                                ▼
┌───────────────────┐         ┌───────────────────┐         ┌───────────────────────┐
│   Alloy (Agent)   │         │  Direct to Tempo  │         │ OTel Operator        │
│ :4317/:4318       │         │    :4318          │         │ (auto-instrument)    │
└───────────────────┘         └───────────────────┘         └───────────────────────┘
        │                         │                                │
        ▼                         ▼                                ▼
┌───────────────────┐         ┌───────────────────┐         ┌───────────────────────┐
│ Python App       │         │  OTel Python      │         │ Python App           │
│ (Manual SDK)     │         │  (Manual SDK)     │         │ (Operator injected)   │
└───────────────────┘         └───────────────────┘         └───────────────────────┘

┌───────────────────┐         ┌───────────────────┐
│ JavaScript App   │         │  JS App           │
│ (Manual SDK)     │         │  (NodeSDK)        │
└───────────────────┘         └───────────────────┘
```

## Data Flow

### 1. Application Layer Instrumentation

Each application uses OpenTelemetry (OTel) SDKs to:
- Create spans for each operation
- Add span attributes (service.name, span.kind, status_code, etc.)
- Export traces via OTLP protocol

### 2. Collection Layer

| Component | Port | Protocol | Description |
|-----------|------|----------|-------------|
| Alloy (otel agent) | 4317/4318 | gRPC/HTTP | Lightweight collector, buffers & batches |
| Tempo Distributor | 4317/4318 | gRPC/HTTP | Receives OTLP, forwards to ingesters |
| OTel Operator | N/A | N/A | Auto-injects OTel agent into pods |

### 3. Storage & Processing

- **Tempo Ingester**: Receives traces, writes to WAL
- **Metrics Generator**: Processes spans → Prometheus metrics
- **Service Graph**: Builds relationships from trace data

---

## Application Comparison

### 1. sample-traces-app (Python - Manual SDK)

**File:** `apps/sample-traces-app/app.py`

**Instrumentation:**
```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

provider = TracerProvider(resource=resource)
processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{otlp_endpoint}/v1/traces"))
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)
```

**Pros:**
- ✅ Full control over span creation and attributes
- ✅ Can add custom instrumentation for specific operations
- ✅ Works without Kubernetes operators
- ✅ Can export to any OTLP-compatible backend

**Cons:**
- ❌ Requires code changes for every new trace point
- ❌ Manual span management overhead
- ❌ Risk of forgetting to instrument critical paths

**Use Cases:**
- When you need fine-grained control over spans
- For legacy applications without OTel support
- When you need to instrument specific business logic

---

### 2. sample-operator-traces-app (Python - OTel Operator)

**File:** `apps/sample-operator-traces-app/k8s.yaml`

**Instrumentation:**
```yaml
annotations:
  instrumentation.opentelemetry.io/inject-python: "true"
```

**Configuration:**
```yaml
env:
  - name: OTEL_EXPORTER_OTLP_ENDPOINT
    value: "http://alloy.observability.svc:4318"
```

**Pros:**
- ✅ Zero-code instrumentation
- ✅ Automatic span capture for popular libraries (Flask, Django, psycopg2, redis)
- ✅ Single annotation enables auto-instrumentation
- ✅ No rebuild required to add tracing

**Cons:**
- ❌ Requires OTel Operator in cluster
- ❌ Limited customization without additional config
- ❌ Less control over span attributes

**Use Cases:**
- Microservices where you want quick observability
- When you can't modify application code
- For rapid onboarding of new services

---

### 3. sample-otel-traces-app (Python - Direct to Tempo)

**File:** `apps/sample-otel-traces-app/k8s.yaml`

**Instrumentation:**
```yaml
env:
  - name: OTEL_EXPORTER_OTLP_ENDPOINT
    value: "http://tempo.observability.svc:4318"
```

**Pros:**
- ✅ Simple setup - no middleware required
- ✅ Direct path reduces latency
- ✅ Works without Alloy collector

**Cons:**
- ❌ No buffering during Tempo outages
- ❌ No batch processing (higher network overhead)
- ❌ No sampling capabilities

**Use Cases:**
- Development/testing environments
- When you want minimal infrastructure
- Low-traffic applications

---

### 4. sample-javascript-traces-app (Node.js - NodeSDK)

**File:** `apps/sample-javascript-traces-app/app.js`

**Instrumentation:**
```javascript
const { NodeSDK } = require('@opentelemetry/sdk-node');
const { HttpInstrumentation } = require('@opentelemetry/instrumentation-http');
const { ExpressInstrumentation } = require('@opentelemetry/instrumentation-express');
const { RedisInstrumentation } = require('@opentelemetry/instrumentation-redis-4');
const { PgInstrumentation } = require('@opentelemetry/instrumentation-pg');

const sdk = new NodeSDK({
  resource,
  traceExporter: new OTLPTraceExporter({ url: `${otlpEndpoint}/v1/traces` }),
  instrumentations: [new HttpInstrumentation(), new ExpressInstrumentation(), ...],
});
sdk.start();
```

**Pros:**
- ✅ Auto-instrumentation for Express, Redis, PostgreSQL
- ✅ Rich instrumentation for Node.js ecosystem
- ✅ Works with popular ORMs and databases

**Cons:**
- ❌ Limited to Node.js runtime
- ❌ More resource-intensive than agent-based approaches

**Use Cases:**
- Node.js microservices with Express/Fastify
- Applications using Redis or PostgreSQL

---

## How to Connect Your App

### Option 1: Direct OTLP (Simplest)

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer("my-service")
# Create spans manually
with tracer.start_as_current_span("my-operation") as span:
    span.set_attribute("key", "value")
```

```yaml
env:
  - name: OTEL_EXPORTER_OTLP_ENDPOINT
    value: "http://alloy.observability.svc:4318"
```

### Option 2: OTel Operator

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
spec:
  template:
    metadata:
      annotations:
        instrumentation.opentelemetry.io/inject-python: "true"
```

### Option 3: Manual SDK + Alloy

```python
# In your app code
provider = TracerProvider(resource=Resource(attributes={SERVICE_NAME: "my-app"}))
processor = BatchSpanProcessor(OTLPSpanExporter(endpoint="http://alloy:4318/v1/traces"))
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)
```

---

## Service Map Connections

The following service connections are captured in the service graph:

| Client | Server | Database |
|--------|--------|----------|
| sample-traces-app (Python) | postgresql | PostgreSQL |
| sample-traces-app (Python) | redis | Redis |
| sample-javascript-traces-app (Node) | appdb | PostgreSQL |
| sample-javascript-traces-app (Node) | redis | Redis |

---

## Environment Variables Reference

| Variable | Description | Default |
|----------|-------------|---------|
| `OTEL_SERVICE_NAME` | Service identifier | app name |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OTLP receiver URL | http://alloy:4318 |
| `OTEL_EXPORTER_OTLP_PROTOCOL` | Protocol (grpc/http/protobuf) | http/protobuf |
| `OTEL_TRACES_EXPORTER` | Trace exporter | otlp |
| `OTEL_METRICS_EXPORTER` | Metrics exporter | none |

---

## References

- [OpenTelemetry Python SDK](https://opentelemetry.io/docs/instrumentation/python/)
- [OpenTelemetry JavaScript SDK](https://opentelemetry.io/docs/instrumentation/js/)
- [OTel Operator](https://github.com/open-telemetry/opentelemetry-operator)
- [Grafana Tempo Configuration](https://grafana.com/docs/tempo/latest/configuration/)