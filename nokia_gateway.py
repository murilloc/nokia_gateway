#!/usr/bin/env python3
"""
Nokia Gateway API
FastAPI-based REST Gateway for Nokia API with automatic token management
"""

import requests
import urllib3
from typing import Dict, Optional, List, Any
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from log_config import get_logger
from token_manager import token_manager
from alarm_manager import alarm_manager

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Get configured logger
logger = get_logger(__name__)


# Pydantic models for request/response
class ErrorResponse(BaseModel):
    """Error response model"""
    error: str
    detail: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response model"""
    status: str
    service: str
    token_valid: bool


# Lifespan context manager for startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI app
    Handles startup and shutdown events
    """
    # Startup: Initialize services
    logger.info("=" * 80)
    logger.info("NOKIA GATEWAY API - STARTING")
    logger.info("=" * 80)

    try:
        # Initialize token manager
        token_manager.initialize()

        # Initialize alarm manager
        logger.info("Initializing alarm manager...")
        alarm_manager.initialize()

        logger.info("=" * 80)
        logger.info("✓ Nokia Gateway API started successfully")
        logger.info("Server ready to accept requests on port 6778")
        logger.info("=" * 80)
    except Exception as e:
        logger.error("=" * 80)
        logger.error(f"✗ Failed to initialize services: {e}")
        logger.error("=" * 80)
        raise

    yield

    # Shutdown: Stop services
    logger.info("=" * 80)
    logger.info("NOKIA GATEWAY API - SHUTTING DOWN")
    logger.info("=" * 80)

    # Stop alarm manager
    alarm_manager.shutdown()

    # Stop token refresh
    token_manager.stop_auto_refresh()

    logger.info("✓ Nokia Gateway API stopped gracefully")
    logger.info("=" * 80)


# Create FastAPI application
app = FastAPI(
    title="Nokia Gateway API",
    description="REST Gateway for Nokia API with automatic token management",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint"""
    return {
        "service": "Nokia Gateway API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Nokia Gateway API",
        "token_valid": token_manager.is_token_valid()
    }


@app.post("/shutdown", tags=["Control"])
async def shutdown():
    """
    Shutdown the Nokia Gateway API gracefully

    This endpoint will stop all services and terminate the application.
    Use with caution in production environments.

    Returns:
        Success message
    """
    logger.warning("⚠ Shutdown requested via REST API")

    # Send response before shutting down
    response = {
        "status": "success",
        "message": "Nokia Gateway API is shutting down...",
        "note": "All services will be stopped gracefully"
    }

    # Schedule shutdown after response is sent
    # Using signal to trigger graceful shutdown
    import asyncio
    asyncio.create_task(_delayed_shutdown())

    return response


async def _delayed_shutdown():
    """Delayed shutdown to allow response to be sent"""
    import asyncio
    await asyncio.sleep(1)  # Wait 1 second for response to be sent
    logger.warning("Initiating graceful shutdown...")
    os.kill(os.getpid(), signal.SIGTERM)


@app.get("/api/v1/nokia_gateway/alarm_status", tags=["Alarms"])
async def get_alarm_status():
    """
    Get alarm manager status

    Returns:
        Alarm manager status including subscription and Kafka consumer info
    """
    try:
        logger.info("→ Received alarm_status request")

        status_info = alarm_manager.get_status()

        logger.info("✓ Alarm status retrieved successfully")

        return {
            "status": "success",
            "data": status_info
        }

    except Exception as e:
        logger.error(f"✗ Error retrieving alarm status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve alarm status: {str(e)}"
        )


@app.get("/api/v1/nokia_gateway/trail_list", tags=["Trail"])
async def get_trail_list(
    network_id: str = Query(..., description="Network ID to fetch trail list for")
) -> List[Dict[str, Any]]:
    """
    Get trail list for a specific network ID

    Args:
        network_id: Network ID (e.g., '788602')

    Returns:
        Trail list data from Nokia API

    Raises:
        HTTPException: If the request fails
    """
    try:
        logger.info(f"→ Received trail_list request for network_id: {network_id}")

        # Check if token is valid
        if not token_manager.is_token_valid():
            logger.warning("Token validation failed, attempting refresh...")
            try:
                token_manager.refresh_access_token()
                logger.info("Token refreshed successfully after validation failure")
            except Exception as e:
                logger.error(f"✗ Failed to refresh token: {e}")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Authentication service unavailable"
                )

        # Get authorization header
        headers = token_manager.get_authorization_header()
        logger.debug("Authorization header obtained")

        # Make request to Nokia API
        endpoint = f"https://10.73.0.181:8443/oms1350/data/npr/trails/{network_id}"

        logger.info(f"Requesting trail data from Nokia API: {endpoint}")

        response = requests.get(
            endpoint,
            headers=headers,
            verify=False,
            timeout=30
        )

        logger.debug(f"Nokia API response status: {response.status_code}")

        # Handle different status codes
        if response.status_code == 401:
            logger.error("✗ Authentication failed (401 Unauthorized)")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication failed"
            )
        elif response.status_code == 404:
            logger.warning(f"Network ID {network_id} not found (404)")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Network ID {network_id} not found"
            )
        elif response.status_code >= 500:
            logger.error(f"✗ Nokia API server error: {response.status_code}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Nokia API server error"
            )

        response.raise_for_status()
        trail_data = response.json()

        trails_count = len(trail_data) if isinstance(trail_data, list) else 1
        logger.info(f"✓ Successfully retrieved trail list for network {network_id}")
        logger.info(f"  Trails count: {trails_count}")

        return trail_data

    except HTTPException:
        # Re-raise HTTPException as-is
        raise
    except requests.exceptions.Timeout:
        logger.error("✗ Request to Nokia API timed out (30s timeout)")
        logger.error(f"  Endpoint: {endpoint}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Request to Nokia API timed out"
        )
    except requests.exceptions.RequestException as e:
        logger.error(f"✗ Request to Nokia API failed: {e}")
        logger.error(f"  Endpoint: {endpoint}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to communicate with Nokia API: {str(e)}"
        )
    except Exception as e:
        logger.error(f"✗ Unexpected error in trail_list endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "detail": str(exc)
        }
    )


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting Nokia Gateway API on port 6778...")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=6778,
        log_level="info"
    )
