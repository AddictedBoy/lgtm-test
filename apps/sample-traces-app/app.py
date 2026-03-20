from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.trace import SpanKind

import os
import time
import random
import logging
import json

from flask import Flask, jsonify, request
import psycopg2
import redis as redis_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

service_name = os.environ.get("OTEL_SERVICE_NAME", "sample-traces-app")
otlp_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://alloy.observability.svc:4318")

redis_host = os.environ.get("REDIS_HOST", "redis.observability.svc")
redis_port = int(os.environ.get("REDIS_PORT", "6379"))
postgres_host = os.environ.get("POSTGRES_HOST", "postgres.observability.svc")
postgres_port = int(os.environ.get("POSTGRES_PORT", "5432"))
postgres_user = os.environ.get("POSTGRES_USER", "postgres")
postgres_password = os.environ.get("POSTGRES_PASSWORD", "postgres")
postgres_db = os.environ.get("POSTGRES_DB", "orders")

resource = Resource(attributes={
    SERVICE_NAME: service_name
})

provider = TracerProvider(resource=resource)
processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{otlp_endpoint}/v1/traces"))
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)

tracer = trace.get_tracer(service_name)

redis = redis_client.Redis(host=redis_host, port=redis_port, decode_responses=True)

def get_db_connection():
    return psycopg2.connect(
        host=postgres_host,
        port=postgres_port,
        user=postgres_user,
        password=postgres_password,
        database=postgres_db
    )

@app.route("/health")
def health():
    return jsonify({"status": "ok"})

@app.route("/order")
def order():
    order_id = random.randint(1000, 9999)
    
    with tracer.start_as_current_span("order-handler", kind=SpanKind.SERVER) as server_span:
        server_span.set_attribute("http.method", "GET")
        server_span.set_attribute("http.route", "/order")
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            with tracer.start_as_current_span("db_query", kind=SpanKind.CLIENT) as db_span:
                db_span.set_attribute("db.system", "postgresql")
                db_span.set_attribute("db.statement", "SELECT count(*) FROM orders")
                db_span.set_attribute("net.peer.name", postgres_host)
                db_span.set_attribute("net.peer.port", postgres_port)
                cursor.execute("SELECT count(*) FROM orders")
                result = cursor.fetchone()
            
            with tracer.start_as_current_span("redis_set", kind=SpanKind.CLIENT) as redis_span:
                redis_span.set_attribute("db.system", "redis")
                redis_span.set_attribute("db.operation", "SET")
                redis_span.set_attribute("net.peer.name", redis_host)
                redis_span.set_attribute("net.peer.port", redis_port)
                redis.set(f"order:{order_id}", json.dumps({"status": "completed", "count": result[0] if result else 0}))
            
            with tracer.start_as_current_span("postgres_insert", kind=SpanKind.CLIENT) as insert_span:
                insert_span.set_attribute("db.system", "postgresql")
                insert_span.set_attribute("db.operation", "INSERT")
                insert_span.set_attribute("net.peer.name", postgres_host)
                insert_span.set_attribute("net.peer.port", postgres_port)
                cursor.execute(
                    "INSERT INTO orders (order_id, amount, status) VALUES (%s, %s, %s)",
                    (f"ORD-{order_id}", random.randint(100, 9999) + 0.99, "pending")
                )
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return jsonify({"orderId": f"ORD-{order_id}", "status": "completed"})
            
        except Exception as e:
            logger.error(f"Error processing order: {e}")
            return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8081))
    app.run(host="0.0.0.0", port=port)
