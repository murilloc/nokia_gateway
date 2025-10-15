#!/usr/bin/env python3
"""
Nokia Gateway API
FastAPI-based REST Gateway for Nokia API with automatic token management
"""

import logging
import requests
import urllib3
from typing import Dict, Optional, List, Any
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from token_manager import token_manager

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


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
    # Startup: Initialize token manager
    logger.info("Starting Nokia Gateway API...")
    try:
        token_manager.initialize()
        logger.info("Nokia Gateway API started successfully")
    except Exception as e:
        logger.error(f"Failed to initialize token manager: {e}")
        raise

    yield

    # Shutdown: Stop token refresh
    logger.info("Shutting down Nokia Gateway API...")
    token_manager.stop_auto_refresh()
    logger.info("Nokia Gateway API stopped")


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
        logger.info(f"Received trail_list request for network_id: {network_id}")

        # Check if token is valid
        if not token_manager.is_token_valid():
            logger.warning("Token is not valid, attempting to refresh...")
            try:
                token_manager.refresh_access_token()
            except Exception as e:
                logger.error(f"Failed to refresh token: {e}")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Authentication service unavailable"
                )

        # Get authorization header
        headers = token_manager.get_authorization_header()

        # Make request to Nokia API
        endpoint = f"https://10.73.0.181:8443/oms1350/data/npr/trails/{network_id}"

        logger.info(f"Requesting trail list from: {endpoint}")

        response = requests.get(
            endpoint,
            headers=headers,
            verify=False,
            timeout=30
        )

        # Handle different status codes
        if response.status_code == 401:
            logger.error("Authentication failed (401)")
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
            logger.error(f"Nokia API server error: {response.status_code}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Nokia API server error"
            )

        response.raise_for_status()
        trail_data = response.json()

        logger.info(f"Successfully retrieved trail list for network {network_id}")

        return trail_data

    except HTTPException:
        # Re-raise HTTPException as-is
        raise
    except requests.exceptions.Timeout:
        logger.error("Request to Nokia API timed out")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Request to Nokia API timed out"
        )
    except requests.exceptions.RequestException as e:
        logger.error(f"Request to Nokia API failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to communicate with Nokia API: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error in trail_list endpoint: {e}")
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
