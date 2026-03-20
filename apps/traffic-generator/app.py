import os
import time
import random
import logging
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.trace import SpanKind

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

service_name = os.environ.get("OTEL_SERVICE_NAME", "traffic-generator")
otlp_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://alloy.observability.svc:4318")

JS_APP_URL = os.environ.get("JS_APP_URL", "http://sample-javascript-traces-app:8082")
PYTHON_APP_URL = os.environ.get("PYTHON_APP_URL", "http://sample-traces-app:8081")

resource = Resource(attributes={
    SERVICE_NAME: service_name
})

provider = TracerProvider(resource=resource)
provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{otlp_endpoint}/v1/traces")))
trace.set_tracer_provider(provider)

tracer = trace.get_tracer(service_name)

def call_js_app():
    endpoints = ["/", "/health", "/order", "/product", "/user"]
    endpoint = random.choice(endpoints)
    
    span = tracer.start_span(f"HTTP GET {endpoint}", kind=SpanKind.CLIENT)
    span.set_attribute("http.method", "GET")
    span.set_attribute("http.url", f"{JS_APP_URL}{endpoint}")
    span.set_attribute("http.target", endpoint)
    span.set_attribute("http.scheme", "http")
    span.set_attribute("net.peer.name", "sample-javascript-traces-app")
    span.set_attribute("net.peer.port", 8082)
    
    try:
        import requests
        response = requests.get(f"{JS_APP_URL}{endpoint}", timeout=5)
        span.set_attribute("http.status_code", response.status_code)
        span.set_status(trace.Status(trace.StatusCode.OK if response.status_code < 400 else trace.StatusCode.ERROR))
        return response.json() if response.status_code == 200 else None
    except Exception as e:
        span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
        logger.error(f"Error calling JS app: {e}")
        return None
    finally:
        span.end()

def call_python_app():
    endpoints = ["/health", "/order"]
    endpoint = random.choice(endpoints)
    
    span = tracer.start_span(f"HTTP GET {endpoint}", kind=SpanKind.CLIENT)
    span.set_attribute("http.method", "GET")
    span.set_attribute("http.url", f"{PYTHON_APP_URL}{endpoint}")
    span.set_attribute("http.target", endpoint)
    span.set_attribute("http.scheme", "http")
    span.set_attribute("net.peer.name", "sample-traces-app")
    span.set_attribute("net.peer.port", 8081)
    
    try:
        import requests
        response = requests.get(f"{PYTHON_APP_URL}{endpoint}", timeout=5)
        span.set_attribute("http.status_code", response.status_code)
        span.set_status(trace.Status(trace.StatusCode.OK if response.status_code < 400 else trace.StatusCode.ERROR))
        return response.json() if response.status_code == 200 else None
    except Exception as e:
        span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
        logger.error(f"Error calling Python app: {e}")
        return None
    finally:
        span.end()

def main():
    logger.info(f"Starting traffic generator")
    logger.info(f"JS App URL: {JS_APP_URL}")
    logger.info(f"Python App URL: {PYTHON_APP_URL}")
    logger.info(f"OTLP Endpoint: {otlp_endpoint}")
    
    while True:
        try:
            call_js_app()
            call_python_app()
            time.sleep(random.uniform(1, 3))
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
