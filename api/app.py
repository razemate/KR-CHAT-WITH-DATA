import logging
import time
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from vanna.servers.fastapi import VannaFastAPIServer
from api.vanna_calls import agent

# --- Phase 7.1: Structured Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("vanna_api")

# --- Phase 3.2: CORS Configuration ---
config = {
    "cors": {
        "enabled": True,
        "allow_origins": ["https://your-production-domain.com", "http://localhost:5173"],
        "allow_credentials": True,
        "allow_methods": ["*"],
        "allow_headers": ["*"],
    }
}

# Initialize Vanna Server with config
vanna_server = VannaFastAPIServer(agent, config=config)

# Create FastAPI app
app = vanna_server.create_app()

# --- Phase 7.2 & 7.3: Request Correlation & Rate Limiting (Simple) ---
# Simple in-memory rate limiter
RATE_LIMIT_WINDOW = 300  # 5 minutes
RATE_LIMIT_MAX_REQUESTS = 60
request_counts = {}

@app.middleware("http")
async def rate_limit_and_log_middleware(request: Request, call_next):
    # 1. Request ID & Correlation
    request_id = request.headers.get("X-Request-ID", str(time.time()))
    
    # 2. Rate Limiting
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    
    # Clean up old entries
    if client_ip in request_counts:
        request_counts[client_ip] = [t for t in request_counts[client_ip] if now - t < RATE_LIMIT_WINDOW]
    else:
        request_counts[client_ip] = []
        
    if len(request_counts[client_ip]) >= RATE_LIMIT_MAX_REQUESTS:
        logger.warning(f"Rate limit exceeded for IP: {client_ip}")
        return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})
        
    request_counts[client_ip].append(now)
    
    # 3. Logging
    logger.info(f"Request started: {request.method} {request.url} (ID: {request_id})")
    start_time = time.time()
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        logger.info(f"Request finished: {response.status_code} (ID: {request_id}, Time: {process_time:.3f}s)")
        return response
    except Exception as e:
        logger.error(f"Request failed: {str(e)} (ID: {request_id})")
        raise e

# --- Phase 4.2: Error Envelope ---
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "INTERNAL_ERROR", "message": str(exc)}},
    )

# Add root endpoint for health check
@app.get("/")
def read_root():
    return {"status": "ok", "service": "Vanna AI Backend"}
