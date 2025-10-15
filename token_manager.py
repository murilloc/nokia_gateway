#!/usr/bin/env python3
"""
Token Manager Module
Manages Nokia API authentication tokens with automatic background refresh
"""

import requests
import logging
import os
from datetime import datetime, timedelta
from threading import Thread, Event, Lock
import urllib3
from typing import Optional, Dict
from dotenv import load_dotenv
import base64

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


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
        logger.info("TokenManager initialized")

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

            response = requests.post(
                url,
                headers=headers,
                json=payload,
                verify=False,
                timeout=30
            )

            response.raise_for_status()
            token_data = response.json()

            # Update internal state with thread safety
            with self._token_lock:
                self.access_token = token_data.get('access_token')
                self.refresh_token = token_data.get('refresh_token')
                self.token_type = token_data.get('token_type', 'Bearer')
                self.expires_in = token_data.get('expires_in', 3600)
                self.token_expiry = datetime.now() + timedelta(seconds=self.expires_in)

            logger.info(f"Token obtained successfully. Expires in {self.expires_in} seconds at {self.token_expiry}")

            return token_data

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to obtain initial token: {e}")
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
            response = requests.post(
                url,
                json=payload,
                verify=False,
                timeout=30
            )
            response.raise_for_status()

            token_data = response.json()

            # Update internal state with thread safety
            with self._token_lock:
                self.access_token = token_data.get('access_token')
                self.refresh_token = token_data.get('refresh_token')
                self.token_type = token_data.get('token_type', 'Bearer')
                self.expires_in = token_data.get('expires_in', 3600)
                self.token_expiry = datetime.now() + timedelta(seconds=self.expires_in)

            logger.info(f"Token refreshed successfully. New expiry: {self.token_expiry}")

            return token_data

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to refresh token: {e}")
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
            logger.warning("Auto-refresh is already running")
            return

        self._stop_event.clear()
        self._refresh_thread = Thread(
            target=self._auto_refresh_worker,
            daemon=True
        )
        self._refresh_thread.start()
        logger.info(f"Auto-refresh started with interval: {self.refresh_interval} seconds")

    def _auto_refresh_worker(self):
        """Worker thread for automatic token refresh"""
        while not self._stop_event.is_set():
            # Wait for the specified interval or until stop event is set
            if self._stop_event.wait(timeout=self.refresh_interval):
                break

            try:
                self.refresh_access_token()
            except Exception as e:
                logger.error(f"Auto-refresh failed: {e}")

    def stop_auto_refresh(self):
        """Stop the automatic token refresh"""
        if self._refresh_thread and self._refresh_thread.is_alive():
            logger.info("Stopping auto-refresh...")
            self._stop_event.set()
            self._refresh_thread.join(timeout=5)
            logger.info("Auto-refresh stopped")

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
        logger.info("Initializing token manager...")
        self.get_initial_token()
        self.start_auto_refresh()
        logger.info("Token manager ready")


# Global token manager instance
token_manager = TokenManager()
