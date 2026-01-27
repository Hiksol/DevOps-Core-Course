import os
import socket
import platform
import psutil
import logging
from datetime import datetime, timezone
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# ---------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger("devops-info-service")
logger.info("Starting DevOps Info Service...")

# ---------------------------------------------------------
# FastAPI app initialization
# ---------------------------------------------------------
app = FastAPI()

START_TIME = datetime.now(timezone.utc)

DEBUG = os.getenv("DEBUG", "false").lower() == "true"
if DEBUG:
    logger.setLevel(logging.DEBUG)
    logger.debug("Debug mode enabled")

# ---------------------------------------------------------
# Helper functions
# ---------------------------------------------------------
def get_uptime():
    delta = datetime.now(timezone.utc) - START_TIME
    seconds = int(delta.total_seconds())
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60

    logger.debug(f"Calculated uptime: {seconds} seconds")

    return {
        "seconds": seconds,
        "human": f"{hours} hours, {minutes} minutes"
    }


def get_system_info():
    info = {
        "hostname": socket.gethostname(),
        "platform": platform.system(),
        "platform_version": platform.version(),
        "architecture": platform.machine(),
        "cpu_count": psutil.cpu_count(),
        "python_version": platform.python_version()
    }

    logger.debug(f"System info collected: {info}")
    return info

# ---------------------------------------------------------
# Error handlers
# ---------------------------------------------------------
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    logger.warning(f"404 Not Found: {request.url}")
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not Found",
            "message": "Endpoint does not exist"
        }
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    logger.error(f"500 Internal Server Error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred"
        }
    )

# ---------------------------------------------------------
# Endpoints
# ---------------------------------------------------------
@app.get("/")
async def main(request: Request):
    logger.info(f"Received request: {request.method} {request.url.path}")

    uptime = get_uptime()

    response = {
        "service": {
            "name": "devops-info-service",
            "version": "1.0.0",
            "description": "DevOps course info service",
            "framework": "FastAPI"
        },
        "system": get_system_info(),
        "runtime": {
            "uptime_seconds": uptime["seconds"],
            "uptime_human": uptime["human"],
            "current_time": datetime.now(timezone.utc).isoformat(),
            "timezone": "UTC"
        },
        "request": {
            "client_ip": request.client.host,
            "user_agent": request.headers.get("user-agent"),
            "method": request.method,
            "path": request.url.path
        },
        "endpoints": [
            {"path": "/", "method": "GET", "description": "Service information"},
            {"path": "/health", "method": "GET", "description": "Health check"}
        ]
    }

    logger.debug(f"Response payload: {response}")
    return response


@app.get("/health")
async def health():
    uptime = get_uptime()
    logger.info("Health check requested")

    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": uptime["seconds"]
    }

# ---------------------------------------------------------
# Application entrypoint
# ---------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", 5000))

    logger.info(f"Running on {HOST}:{PORT} (debug={DEBUG})")

    uvicorn.run(
        "app:app",
        host=HOST,
        port=PORT,
        reload=DEBUG
    )
