# benchmark_tasks.py — NexusSwarm Benchmark Tasks
# Defines 50 distinct tasks for benchmarking the code-generation capabilities

BENCHMARK_TASKS = [
    {
        "name": "FastAPI CRUD",
        "title": "Create a FastAPI Task Manager API",
        "description": "Implement a Task Management backend in FastAPI. Include endpoints to create, read, update, and delete tasks. Use SQLAlchemy with an SQLite database. Tasks should have a title, description, completed status, and created_at timestamp."
    },
    {
        "name": "User Auth JWT",
        "title": "FastAPI User Authentication with JWT",
        "description": "Create a secure user registration and login system in FastAPI. Use bcrypt for password hashing and pyjwt for issuing JSON Web Tokens. Guard a protected endpoint /users/me with JWT authentication."
    },
    {
        "name": "Redis Cache API",
        "title": "FastAPI API with Redis Caching",
        "description": "Implement an API endpoint /products/{id} that fetches details from a database and uses Redis to cache the response. If the cache hits, return immediately. If it misses, fetch from DB and populate the cache."
    },
    {
        "name": "SQL Injection Hardening",
        "title": "Secure SQL Query Implementation",
        "description": "Given a search input, implement a secure SQL query search endpoint in Python using parameterized queries to prevent SQL injection vulnerabilities. Do not use string formatting or concatenation."
    },
    {
        "name": "Stripe Hook Handler",
        "title": "Stripe Webhook Event Handler",
        "description": "Implement a FastAPI webhook handler endpoint for Stripe events. Verify the Stripe signature signature header using the stripe SDK. Handle the invoice.payment_succeeded event by updating user billing status."
    },
    {
        "name": "SendGrid Emailer",
        "title": "SendGrid Email Notification Service",
        "description": "Create a background worker service in Python that listens to a message queue and sends registration confirmation emails using the SendGrid API. Handle connection timeouts and retries."
    },
    {
        "name": "Pagination API",
        "title": "API Endpoint with Pagination",
        "description": "Design an endpoint /posts that supports cursor-based pagination. Accept limit and starting_after query parameters, and return a list of items along with a next_cursor value."
    },
    {
        "name": "File Upload S3",
        "title": "Secure File Upload to AWS S3",
        "description": "Create a FastAPI endpoint /upload that accepts an image file, validates that it is a JPEG or PNG under 5MB, and uploads it to an AWS S3 bucket with a unique, secure file path. Return the S3 URL."
    },
    {
        "name": "Docker Multi-stage",
        "title": "Optimize Python Dockerfile",
        "description": "Write a multi-stage Dockerfile for a FastAPI application. Ensure the final image is minimal, does not run as root, and does not contain build-time dependencies or compilers."
    },
    {
        "name": "GitHub CI Pipeline",
        "title": "GitHub Actions Workflow for Pytest",
        "description": "Create a GitHub Actions workflow that triggers on pull requests to the main branch. It should set up Python 3.11, install dependencies, run lint checks (ruff), and run tests using pytest with coverage."
    },
    {
        "name": "PostgreSQL Rate Limiter",
        "title": "Token Bucket Rate Limiter",
        "description": "Implement a custom token-bucket rate limiter middleware in FastAPI using Redis to track client IP requests. Allow 10 requests per minute with a burst size of 20."
    },
    {
        "name": "React Search Bar",
        "title": "React Instant Search Component",
        "description": "Develop a React component for a real-time product search bar. Fetch results from an API using debounce (300ms) to limit API requests, and display matching results in a dropdown list."
    },
    {
        "name": "MongoDB Aggregator",
        "title": "MongoDB Order Stats Aggregation",
        "description": "Write a PyMongo aggregation pipeline to calculate monthly sales stats: total revenue, average order value, and total orders count. Filter out canceled orders."
    },
    {
        "name": "gRPC Service Python",
        "title": "Implement gRPC User Service",
        "description": "Define a protobuf service for retrieving user profiles. Implement the corresponding gRPC server in Python using grpcio. Handle the GetUserProfile request and return user data."
    },
    {
        "name": "WebSocket Chat Server",
        "title": "FastAPI WebSocket Chat Server",
        "description": "Create a simple WebSocket chat server in FastAPI. Allow multiple clients to connect, send messages, and broadcast those messages to all other connected clients in real time."
    },
    {
        "name": "GraphQL API Graphene",
        "title": "FastAPI GraphQL endpoint using Graphene",
        "description": "Set up a GraphQL API endpoint in FastAPI using Graphene. Create a Query type to resolve a list of books and a Mutation type to add a new book to the database."
    },
    {
        "name": "JSON Schema Validator",
        "title": "API Request JSON Schema Validation",
        "description": "Create a Python utility function to validate incoming JSON payloads against a predefined JSON Schema. Return descriptive error messages detailing which fields failed validation."
    },
    {
        "name": "CORS Middleware Config",
        "title": "Secure CORS Configuration",
        "description": "Configure FastAPI CORS middleware to allow credentials and requests only from a specified list of trusted subdomains. Do not use wildcard origin policies (*)."
    },
    {
        "name": "Prometheus Metrics API",
        "title": "FastAPI Prometheus Instrumentation",
        "description": "Instrument a FastAPI application with Prometheus metrics. Track HTTP request counts, latency histograms grouped by path and method, and expose a /metrics endpoint."
    },
    {
        "name": "Celery Task Queue",
        "title": "Asynchronous Video Transcoding Tasks",
        "description": "Configure a Celery task queue using RabbitMQ as the broker. Implement an asynchronous task to transcode an uploaded video file to a different resolution, updating status in DB."
    },
    {
        "name": "Data Encryption AES",
        "title": "Encrypt PII Database Columns",
        "description": "Implement a Python class to encrypt and decrypt sensitive fields (like SSN) before saving them to database. Use AES-GCM (256-bit) encryption via the cryptography library."
    },
    {
        "name": "OAuth2 Discord Login",
        "title": "Discord OAuth2 Authorization Flow",
        "description": "Implement the complete authorization code grant flow for logging in users via Discord. Handle the redirect URL, code exchange for access token, and fetch user details."
    },
    {
        "name": "PDF Invoice Generator",
        "title": "FastAPI PDF Invoice Endpoint",
        "description": "Create an endpoint /invoices/{id}/pdf that fetches invoice details and dynamically generates a PDF file using ReportLab. Stream the PDF back to the user with correct headers."
    },
    {
        "name": "Markdown Parser API",
        "title": "API Markdown to Clean HTML",
        "description": "Implement an endpoint that accepts a markdown string, parses it to HTML using markdown-it, and sanitizes the output with Bleach to prevent XSS payloads. Return the sanitized HTML."
    },
    {
        "name": "Database Migration Script",
        "title": "Alembic Migration Setup",
        "description": "Create a database migration script template using Alembic that adds an email_verified boolean column with a default value of False, and creates a unique index on the email column."
    },
    {
        "name": "Health Check Endpoint",
        "title": "Deep Health Check Endpoint",
        "description": "Implement a deep health check endpoint /healthz that verifies connections to PostgreSQL, Redis, and an external payment gateway API. Return 503 if any service is down."
    },
    {
        "name": "UUID Primary Keys",
        "title": "SQLAlchemy Model with UUID",
        "description": "Design an SQLAlchemy model using UUIDv4 as the primary key type (instead of auto-incrementing integers) to prevent object enumeration attacks on public API endpoints."
    },
    {
        "name": "Elasticsearch Sync",
        "title": "Elasticsearch Product Index Sync",
        "description": "Write a Python script to index product updates from PostgreSQL into Elasticsearch. Implement bulk indexing for performance and handle indexing failures with a retry queue."
    },
    {
        "name": "OpenTelemetry Tracing",
        "title": "Distributed Tracing Integration",
        "description": "Configure OpenTelemetry SDK in FastAPI to trace HTTP requests. Ensure spans include database queries and carry trace context (W3C Trace Context) to downstream requests."
    },
    {
        "name": "Pytest Mocking external API",
        "title": "Mock External API in Pytest",
        "description": "Write test cases for a weather service using pytest and pytest-mock. Mock requests.get calls to return a predefined JSON payload, verifying correct parsing and error handling."
    },
    {
        "name": "API Versioning Route",
        "title": "API Versioning Strategy",
        "description": "Implement URL-based API versioning in FastAPI (e.g. /api/v1/... and /api/v2/...). Structure routes and folders to maintain clean code and share models between versions."
    },
    {
        "name": "JWT Refresh Token",
        "title": "Implement JWT Refresh Tokens",
        "description": "Design a token refresh flow. Store secure, HTTP-only refresh tokens in cookies with expiration, and allow clients to exchange them for short-lived access tokens via /auth/refresh."
    },
    {
        "name": "SQLAlchemy Soft Delete",
        "title": "Soft Delete Model Pattern",
        "description": "Implement a soft-delete mixin in SQLAlchemy. Automatically filter out soft-deleted records (where deleted_at is not null) from select queries using custom query classes."
    },
    {
        "name": "CSV Export Streaming",
        "title": "Stream Large CSV Exports",
        "description": "Create a FastAPI endpoint that queries a large dataset of sales transactions and streams the data back to the client as a CSV file to avoid loading millions of rows into memory."
    },
    {
        "name": "Kubernetes Probe Config",
        "title": "Kubernetes Liveness Readiness Probes",
        "description": "Create standard Kubernetes deployment configurations including livenessProbe, readinessProbe, resources constraints (limits/requests), and securityContext settings."
    },
    {
        "name": "Config Vault Loader",
        "title": "Secure Vault Configuration Loader",
        "description": "Write a Python startup utility that authenticates against HashiCorp Vault via AppRole and loads secret keys into application environment variables on startup."
    },
    {
        "name": "Pytest Parallel Runner",
        "title": "Configure pytest-xdist",
        "description": "Configure a test environment using pytest.ini and pytest-xdist to run tests in parallel. Ensure test database fixtures isolate transactions to prevent database state collision."
    },
    {
        "name": "FastAPI Webhook Sender",
        "title": "Webhook Dispatcher Service",
        "description": "Build a webhook dispatching system in Python. Send POST payloads to user-defined URLs, signing the payload body using an HMAC-SHA256 signature to allow verification by clients."
    },
    {
        "name": "Pydantic V2 Migration",
        "title": "Migrate Models to Pydantic V2",
        "description": "Given a set of Pydantic v1 models, refactor them to use Pydantic v2 features. Use new field validators, model validators, and update config schemas accordingly."
    },
    {
        "name": "GraphQL N+1 Resolver",
        "title": "Resolve N+1 in GraphQL",
        "description": "Implement a GraphQL resolver for posts and their authors. Use DataLoader patterns in Python (aiodataloader) to batch author lookups and solve the N+1 query problem."
    },
    {
        "name": "Redis PubSub Client",
        "title": "Redis Event Pub/Sub Handler",
        "description": "Write a background asyncio listener that subscribes to a Redis channel, parses received JSON event messages, and updates an in-memory client registry accordingly."
    },
    {
        "name": "API Request Logger",
        "title": "Structured API Request Logger",
        "description": "Implement middleware in FastAPI that logs every HTTP request and response in JSON format. Include timestamp, path, method, status code, response time, and user ID."
    },
    {
        "name": "Slow Query Logging",
        "title": "Log Slow Database Queries",
        "description": "Configure SQLAlchemy event listeners to monitor database query execution times. Log a warning with the SQL query and duration if the query takes longer than 500ms."
    },
    {
        "name": "Clickhouse Ingestion API",
        "title": "FastAPI ClickHouse Logs Ingestion",
        "description": "Design a high-throughput endpoint to ingest application logs and write them in micro-batches to a ClickHouse database using clickhouse-driver with efficient queries."
    },
    {
        "name": "Web Scraping Agent",
        "title": "Scrape Product Data securely",
        "description": "Write a Python script using BeautifulSoup and HTTPX to scrape product data from a target website. Handle rate limits, network retries, and parse metadata dynamically."
    },
    {
        "name": "JWT Blacklist Redis",
        "title": "Revoke JWTs using Redis Blacklist",
        "description": "Implement a logout endpoint in FastAPI. Blacklist the user's active JWT in Redis for the remainder of its TTL, and reject requests using blacklisted tokens."
    },
    {
        "name": "Sentry Error Handler",
        "title": "Sentry Integration in FastAPI",
        "description": "Configure Sentry SDK in FastAPI. Capture unhandled exceptions, set user context for authenticated requests, and filter out noise like 404 validation errors."
    },
    {
        "name": "Bcrypt Password Strength",
        "title": "Password Strength Validator",
        "description": "Create a password validator function in Python. Enforce complex password rules (length, casing, digits, special characters) and throw descriptive validation errors."
    },
    {
        "name": "API Payload Compression",
        "title": "Gzip Compression Middleware",
        "description": "Add Gzip compression middleware to FastAPI. Compress responses for requests that include 'Accept-Encoding: gzip', configuring threshold size for compression."
    },
    {
        "name": "Postgres Search Index",
        "title": "PostgreSQL Full-Text Search",
        "description": "Create an API endpoint utilizing PostgreSQL full-text search (tsvector and tsquery) to search through product titles and descriptions, return results ranked by relevance."
    }
]
