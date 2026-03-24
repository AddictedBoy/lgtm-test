const { NodeSDK } = require('@opentelemetry/sdk-node');
const { Resource } = require('@opentelemetry/resources');
const { OTLPTraceExporter } = require('@opentelemetry/exporter-trace-otlp-http');
const { HttpInstrumentation } = require('@opentelemetry/instrumentation-http');
const { ExpressInstrumentation } = require('@opentelemetry/instrumentation-express');
const { RedisInstrumentation } = require('@opentelemetry/instrumentation-redis-4');
const { PgInstrumentation } = require('@opentelemetry/instrumentation-pg');
const { SemanticResourceAttributes } = require('@opentelemetry/semantic-conventions');

const serviceName = process.env.OTEL_SERVICE_NAME || 'sample-javascript-traces-app';
const otlpEndpoint = process.env.OTEL_EXPORTER_OTLP_ENDPOINT || 'http://alloy.observability.svc:4318';

console.log('=== Starting JS App ===');
console.log('Service:', serviceName);
console.log('OTLP Endpoint:', otlpEndpoint);
console.log('Node version:', process.version);

const resource = new Resource({
  [SemanticResourceAttributes.SERVICE_NAME]: serviceName,
});

const sdk = new NodeSDK({
  resource,
  traceExporter: new OTLPTraceExporter({
    url: `${otlpEndpoint}/v1/traces`,
  }),
  instrumentations: [
    new HttpInstrumentation({
      ignoreIncomingRequestHook: (req) => {
        return req.url === '/health';
      },
    }),
    new ExpressInstrumentation(),
    new RedisInstrumentation(),
    new PgInstrumentation(),
  ],
});

sdk.start();

console.log('SDK started with auto-instrumentation');

const express = require('express');
const { createClient } = require('redis');
const { Pool } = require('pg');
const app = express();

const port = process.env.PORT || 8082;
const REDIS_HOST = process.env.REDIS_HOST || 'redis.observability.svc';
const POSTGRES_HOST = process.env.POSTGRES_HOST || 'postgres.observability.svc';

console.log('Redis:', REDIS_HOST, 6379);
console.log('Postgres:', POSTGRES_HOST, 5432);

const redisClient = createClient({
  socket: {
    host: REDIS_HOST,
    port: 6379,
    connectTimeout: 5000,
  }
});

redisClient.on('error', (err) => console.log('Redis Client Error', err.message));
redisClient.on('connect', () => console.log('Redis connected'));

redisClient.connect().catch(console.error);

const pgPool = new Pool({
  host: POSTGRES_HOST,
  port: 5432,
  user: 'appuser',
  password: 'apppassword',
  database: 'appdb',
});

pgPool.on('error', (err) => console.log('Postgres Client Error', err.message));
pgPool.query('SELECT 1').then(() => console.log('Postgres connected')).catch(console.error);

app.get('/', (req, res) => {
  res.json({ message: 'Hello from JavaScript app!' });
});

app.get('/health', (req, res) => {
  res.json({ status: 'ok' });
});

app.get('/order', async (req, res) => {
  try {
    await redisClient.get('order_count');
  } catch (err) {
    console.log('Redis error:', err.message);
  }
  try {
    await pgPool.query('SELECT count(*) FROM orders');
  } catch (err) {
    console.log('Postgres error:', err.message);
  }
  res.json({ orderId: `ORD-${Math.floor(Math.random() * 10000)}`, status: 'completed' });
});

app.get('/product', async (req, res) => {
  try {
    await redisClient.get('product_cache');
  } catch (err) {
    console.log('Redis error:', err.message);
  }
  try {
    await pgPool.query('SELECT 1');
  } catch (err) {
    console.log('Postgres error:', err.message);
  }
  res.json({ id: Math.floor(Math.random() * 100), name: 'Sample Product', price: 99.99 });
});

app.get('/user', async (req, res) => {
  try {
    await redisClient.get('user_session');
  } catch (err) {
    console.log('Redis error:', err.message);
  }
  res.json({ id: Math.floor(Math.random() * 1000), name: 'Test User' });
});

app.get('/error', (req, res) => {
  res.status(500).json({ error: 'Something went wrong!' });
});

app.listen(port, '0.0.0.0', () => {
  console.log(`Server running on port ${port}`);
});
