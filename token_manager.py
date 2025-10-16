#!/usr/bin/env python3
"""
Token Manager Module
Manages Nokia API authentication tokens with automatic background refresh
"""

import requests
import os
from datetime import datetime, timedelta
from threading import Thread, Event, Lock
import urllib3
from typing import Optional, Dict
from dotenv import load_dotenv
import base64

from log_config import get_logger

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Get configured logger
logger = get_logger(__name__)


class TokenManager:
    """Manages authentication tokens with automatic background refresh for Nokia API"""

    _instance = None
    _lock = Lock()

    def __new__(cls):
        """Singleton pattern to ensure only one token manager instance"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the token manager (only once due to singleton pattern)"""
        if hasattr(self, '_initialized'):
            logger.debug("TokenManager already initialized, reusing instance")
            return

        # Load environment variables
        load_dotenv()

        self.base_url = os.getenv('API_BASE_URL', 'https://10.73.0.181/rest-gateway/rest/api/v1').rstrip('/')
        self.username = os.getenv('API_USERNAME')
        self.password = os.getenv('API_PASSWORD')
        self.refresh_interval = int(os.getenv('TOKEN_REFRESH_INTERVAL', '3000'))

        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.token_type: str = "Bearer"
        self.expires_in: int = 3600
        self.token_expiry: Optional[datetime] = None

        # Threading control
        self._stop_event = Event()
        self._refresh_thread: Optional[Thread] = None
        self._token_lock = Lock()

        self._initialized = True
        logger.info("TokenManager singleton instance created")
        logger.info(f"API Base URL: {self.base_url}")
        logger.info(f"Username: {self.username}")
        logger.info(f"Token refresh interval: {self.refresh_interval} seconds ({self.refresh_interval/60:.1f} minutes)")

    def get_initial_token(self) -> Dict:
        """
        Obtain initial access token using basic authentication

        Returns:
            dict: Token response containing access_token, refresh_token, etc.
        """
        url = f"{self.base_url}/auth/token"
        payload = {
            "grant_type": "client_credentials"
        }

        # Create Basic Auth header
        credentials = f"{self.username}:{self.password}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        headers = {
            "Authorization": f"Basic {encoded_credentials}",
            "Content-Type": "application/json"
        }

        try:
            logger.info(f"Requesting initial token from {url}")
            logger.debug(f"Using username: {self.username}")

            response = requests.post(
                url,
                headers=headers,
                json=payload,
                verify=False,
                timeout=30
            )

            logger.debug(f"Token request response status: {response.status_code}")
            response.raise_for_status()
            token_data = response.json()

            # Update internal state with thread safety
            with self._token_lock:
                self.access_token = token_data.get('access_token')
                self.refresh_token = token_data.get('refresh_token')
                self.token_type = token_data.get('token_type', 'Bearer')
                self.expires_in = token_data.get('expires_in', 3600)
                self.token_expiry = datetime.now() + timedelta(seconds=self.expires_in)

            logger.info(f"✓ Initial token obtained successfully")
            logger.info(f"Token type: {self.token_type}")
            logger.info(f"Expires in: {self.expires_in} seconds ({self.expires_in/60:.1f} minutes)")
            logger.info(f"Expiry time: {self.token_expiry.strftime('%Y-%m-%d %H:%M:%S')}")

            return token_data

        except requests.exceptions.RequestException as e:
            logger.error(f"✗ Failed to obtain initial token: {e}")
            logger.error(f"Request URL: {url}")
            raise

    def refresh_access_token(self) -> Dict:
        """
        Refresh the access token using the refresh token

        Returns:
            dict: New token response
        """
        with self._token_lock:
            current_refresh_token = self.refresh_token

        if not current_refresh_token:
            raise ValueError("No refresh token available. Please obtain initial token first.")

        url = f"{self.base_url}/auth/token"
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": current_refresh_token
        }

        try:
            logger.info("Refreshing access token...")
            logger.debug(f"Using refresh token: {current_refresh_token[:20]}...")

            response = requests.post(
                url,
                json=payload,
                verify=False,
                timeout=30
            )

            logger.debug(f"Token refresh response status: {response.status_code}")
            response.raise_for_status()

            token_data = response.json()

            # Update internal state with thread safety
            with self._token_lock:
                self.access_token = token_data.get('access_token')
                self.refresh_token = token_data.get('refresh_token')
                self.token_type = token_data.get('token_type', 'Bearer')
                self.expires_in = token_data.get('expires_in', 3600)
                self.token_expiry = datetime.now() + timedelta(seconds=self.expires_in)

            logger.info(f"✓ Token refreshed successfully")
            logger.info(f"New expiry time: {self.token_expiry.strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"Next refresh in: {self.refresh_interval} seconds ({self.refresh_interval/60:.1f} minutes)")

            return token_data

        except requests.exceptions.RequestException as e:
            logger.error(f"✗ Failed to refresh token: {e}")
            logger.error(f"Request URL: {url}")
            logger.error(f"This may cause authentication failures until next retry")
            raise

    def get_authorization_header(self) -> Dict[str, str]:
        """
        Get the authorization header for API requests

        Returns:
            dict: Authorization header
        """
        with self._token_lock:
            if not self.access_token:
                raise ValueError("No access token available. Please authenticate first.")

            return {
                "Authorization": f"{self.token_type} {self.access_token}"
            }

    def start_auto_refresh(self):
        """Start automatic token refresh in background thread"""
        if self._refresh_thread and self._refresh_thread.is_alive():
            logger.warning("Auto-refresh thread is already running")
            return

        self._stop_event.clear()
        self._refresh_thread = Thread(
            target=self._auto_refresh_worker,
            daemon=True,
            name="TokenRefreshThread"
        )
        self._refresh_thread.start()
        logger.info(f"✓ Auto-refresh thread started")
        logger.info(f"Refresh interval: {self.refresh_interval} seconds ({self.refresh_interval/60:.1f} minutes)")
        logger.info(f"Thread name: {self._refresh_thread.name}")

    def _auto_refresh_worker(self):
        """Worker thread for automatic token refresh"""
        logger.info("Auto-refresh worker thread started")

        while not self._stop_event.is_set():
            # Wait for the specified interval or until stop event is set
            logger.debug(f"Waiting {self.refresh_interval} seconds before next refresh...")
            if self._stop_event.wait(timeout=self.refresh_interval):
                logger.info("Stop event received, exiting auto-refresh worker")
                break

            try:
                logger.info("Auto-refresh cycle triggered")
                self.refresh_access_token()
            except requests.exceptions.HTTPError as e:
                # If refresh fails with 400/401, token is invalid - get new initial token
                if e.response and e.response.status_code in [400, 401]:
                    logger.warning(f"✗ Refresh token invalid (HTTP {e.response.status_code})")
                    logger.info("Attempting to obtain new initial token...")
                    try:
                        self.get_initial_token()
                        logger.info("✓ Successfully obtained new initial token")
                    except Exception as init_error:
                        logger.error(f"✗ Failed to obtain new initial token: {init_error}")
                        logger.error("Will retry on next cycle")
                else:
                    logger.error(f"✗ Auto-refresh failed: {e}")
                    logger.error("Will retry on next cycle")
            except Exception as e:
                logger.error(f"✗ Auto-refresh failed: {e}")
                logger.error("Will retry on next cycle")

        logger.info("Auto-refresh worker thread stopped")

    def stop_auto_refresh(self):
        """Stop the automatic token refresh"""
        if self._refresh_thread and self._refresh_thread.is_alive():
            logger.info("Stopping auto-refresh thread...")
            self._stop_event.set()
            self._refresh_thread.join(timeout=5)
            if self._refresh_thread.is_alive():
                logger.warning("Auto-refresh thread did not stop gracefully within timeout")
            else:
                logger.info("✓ Auto-refresh thread stopped successfully")
        else:
            logger.debug("Auto-refresh thread is not running")

    def is_token_valid(self) -> bool:
        """
        Check if the current token is valid (not expired)

        Returns:
            bool: True if token is valid, False otherwise
        """
        with self._token_lock:
            if not self.access_token or not self.token_expiry:
                return False

            # Consider token invalid if it expires in less than 60 seconds
            return datetime.now() < (self.token_expiry - timedelta(seconds=60))

    def initialize(self):
        """Initialize the token manager by obtaining token and starting auto-refresh"""
        logger.info("=" * 60)
        logger.info("Initializing Token Manager")
        logger.info("=" * 60)

        try:
            self.get_initial_token()
            self.start_auto_refresh()
            logger.info("=" * 60)
            logger.info("✓ Token Manager initialized successfully and ready")
            logger.info("=" * 60)
        except Exception as e:
            logger.error("=" * 60)
            logger.error(f"✗ Token Manager initialization failed: {e}")
            logger.error("=" * 60)
            raise


# Global token manager instance
token_manager = TokenManager()
