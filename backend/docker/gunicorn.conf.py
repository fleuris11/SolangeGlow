"""Production application server: gunicorn manages uvicorn workers (HTTP and WebSockets)."""

import os

bind = "0.0.0.0:8000"
worker_class = "uvicorn_worker.UvicornWorker"
workers = int(os.environ.get("WEB_CONCURRENCY", "3"))
# Long uploads (lesson videos): the worker keeps answering meanwhile.
timeout = 120
graceful_timeout = 30
keepalive = 5
# Restarted now and then: a slow memory growth never reaches the server's limit.
max_requests = 2000
max_requests_jitter = 200
# Only Caddy and the web server reach this port: their address headers can be trusted, and
# REMOTE_ADDR becomes the visitor's address (rate limits, audit journal).
forwarded_allow_ips = "*"
# Addresses and tokens in URLs have no place in the logs; errors still go to stderr.
accesslog = None
errorlog = "-"
loglevel = os.environ.get("GUNICORN_LOG_LEVEL", "warning")
