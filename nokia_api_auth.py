#!/usr/bin/env python3
"""
Nokia API Authentication and Token Management
Handles authentication, token refresh, and authenticated API requests
"""

import requests
import time
import logging
import json
import os
from datetime import datetime, timedelta
from threading import Thread, Event
import urllib3
from typing import Optional, Dict
from dotenv import load_dotenv

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NokiaAPIAuth:
    """Manages authentication and token refresh for Nokia API"""

    def __init__(self, base_url: str, username: str, password: str):
        """
        Initialize the Nokia API authentication manager

        Args:
            base_url: Base URL of the API (e.g., https://10.73.0.181/rest-gateway/rest/api/v1)
            username: API username
            password: API password
        """
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.token_type: str = "Bearer"
        self.expires_in: int = 3600
        self.token_expiry: Optional[datetime] = None

        # Threading control
        self._stop_event = Event()
        self._refresh_thread: Optional[Thread] = None

    def get_initial_token(self) -> Dict:
        """
        Obtain initial access token using basic authentication

        Returns:
            dict: Token response containing access_token, refresh_token, etc.
        """
        import base64

        url = f"{self.base_url}/auth/token"
        payload = {
            "grant_type": "client_credentials"
        }

        # Create Basic Auth header manually
        credentials = f"{self.username}:{self.password}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        headers = {
            "Authorization": f"Basic {encoded_credentials}",
            "Content-Type": "application/json"
        }

        try:
            logger.info(f"Requesting initial token from {url}")
            logger.debug(f"Username: {self.username}")
            logger.debug(f"Authorization header: Basic {encoded_credentials}")
            logger.debug(f"Payload: {payload}")

            response = requests.post(
                url,
                headers=headers,
                json=payload,
                verify=False,  # Disable SSL verification for self-signed certs
                timeout=30
            )

            logger.debug(f"Response status: {response.status_code}")
            logger.debug(f"Response headers: {dict(response.headers)}")
            logger.debug(f"Response body: {response.text}")

            response.raise_for_status()

            token_data = response.json()

            # Update internal state
            self.access_token = token_data.get('access_token')
            self.refresh_token = token_data.get('refresh_token')
            self.token_type = token_data.get('token_type', 'Bearer')
            self.expires_in = token_data.get('expires_in', 3600)
            self.token_expiry = datetime.now() + timedelta(seconds=self.expires_in)

            logger.info(f"Token obtained successfully. Expires in {self.expires_in} seconds")
            logger.info(f"Token expiry time: {self.token_expiry}")

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
        if not self.refresh_token:
            raise ValueError("No refresh token available. Please obtain initial token first.")

        url = f"{self.base_url}/auth/token"
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token
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

            # Update internal state
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
        if not self.access_token:
            raise ValueError("No access token available. Please authenticate first.")

        return {
            "Authorization": f"{self.token_type} {self.access_token}"
        }

    def start_auto_refresh(self, refresh_interval: int = 3600):
        """
        Start automatic token refresh in background thread

        Args:
            refresh_interval: Interval in seconds between token refreshes (default: 3600 = 60 minutes)
        """
        if self._refresh_thread and self._refresh_thread.is_alive():
            logger.warning("Auto-refresh is already running")
            return

        self._stop_event.clear()
        self._refresh_thread = Thread(
            target=self._auto_refresh_worker,
            args=(refresh_interval,),
            daemon=True
        )
        self._refresh_thread.start()
        logger.info(f"Auto-refresh started with interval: {refresh_interval} seconds")

    def _auto_refresh_worker(self, interval: int):
        """
        Worker thread for automatic token refresh

        Args:
            interval: Refresh interval in seconds
        """
        while not self._stop_event.is_set():
            # Wait for the specified interval or until stop event is set
            if self._stop_event.wait(timeout=interval):
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

    def make_authenticated_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """
        Make an authenticated request to the API

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (will be appended to base_url)
            **kwargs: Additional arguments to pass to requests

        Returns:
            requests.Response: API response
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = kwargs.pop('headers', {})
        headers.update(self.get_authorization_header())

        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            verify=False,
            **kwargs
        )

        return response

    def get_trail_list(self, network_id: str) -> Dict:
        """
        Get trail list for a specific network ID

        Args:
            network_id: Network ID (e.g., '788602')

        Returns:
            dict: Trail list data
        """
        endpoint = f"https://10.73.0.181:8443/oms1350/data/npr/trails/{network_id}"

        try:
            logger.info(f"Fetching trail list for network ID: {network_id}")

            # Make direct request (different base URL)
            headers = self.get_authorization_header()
            response = requests.get(
                endpoint,
                headers=headers,
                verify=False,
                timeout=30
            )
            response.raise_for_status()

            trail_data = response.json()
            logger.info(f"Successfully retrieved trail list. Count: {len(trail_data) if isinstance(trail_data, list) else 'N/A'}")

            return trail_data

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get trail list: {e}")
            raise

    def get_trail_current_route(self, trail_id: str) -> Dict:
        """
        Get current route for a specific trail ID

        Args:
            trail_id: Trail ID (e.g., '864572')

        Returns:
            dict: Trail current route data
        """
        endpoint = f"https://10.73.0.181:8443/oms1350/data/npr/trails/{trail_id}/currentRoute"

        try:
            logger.info(f"Fetching current route for trail ID: {trail_id}")

            # Make direct request (different base URL)
            headers = self.get_authorization_header()
            response = requests.get(
                endpoint,
                headers=headers,
                verify=False,
                timeout=30
            )
            response.raise_for_status()

            route_data = response.json()
            logger.info(f"Successfully retrieved current route for trail {trail_id}")

            return route_data

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get current route: {e}")
            raise


def main():
    """Main execution function"""

    # Load environment variables from .env file
    load_dotenv()

    # Configuration from environment variables
    BASE_URL = os.getenv('API_BASE_URL', 'https://10.73.0.181/rest-gateway/rest/api/v1')
    USERNAME = os.getenv('API_USERNAME', 'api_user')
    PASSWORD = os.getenv('API_PASSWORD', 'api_user@')

    logger.info(f"Loaded configuration - URL: {BASE_URL}, Username: {USERNAME}")

    # Initialize authentication manager
    auth = NokiaAPIAuth(BASE_URL, USERNAME, PASSWORD)

    try:
        # Get initial token
        initial_token = auth.get_initial_token()
        print("\n=== Initial Token Response ===")
        print(json.dumps(initial_token, indent=2))

        print(f"\nAccess Token: {auth.access_token}")
        print(f"Refresh Token: {auth.refresh_token}")
        print(f"Token Type: {auth.token_type}")
        print(f"Expires In: {auth.expires_in} seconds")
        print(f"Token Expiry: {auth.token_expiry}")

        # Start automatic token refresh every 50 minutes (3000 seconds)
        auth.start_auto_refresh(refresh_interval=3000)

        print("\n=== Token auto-refresh is active ===")
        print("Making API requests...\n")

        # Example 1: Get Trail List
        try:
            print("\n=== Trail List Request ===")
            network_id = "788602"
            trail_list = auth.get_trail_list(network_id)

            logger.info(f"Trail List Response for network {network_id}:")
            logger.info(f"Response type: {type(trail_list)}")
            logger.info(f"Response data: {json.dumps(trail_list, indent=2)}")

            print(f"\nTrail List for Network {network_id}:")
            print(json.dumps(trail_list, indent=2))
        except Exception as e:
            logger.error(f"Failed to retrieve trail list: {e}")

        # Example 2: Get Trail Current Route (commented out for now)
        # try:
        #     print("\n=== Trail Current Route Request ===")
        #     trail_id = "864572"
        #     current_route = auth.get_trail_current_route(trail_id)
        #
        #     logger.info(f"Current Route Response for trail {trail_id}:")
        #     logger.info(f"Response type: {type(current_route)}")
        #     logger.info(f"Response data: {json.dumps(current_route, indent=2)}")
        #
        #     print(f"\nCurrent Route for Trail {trail_id}:")
        #     print(json.dumps(current_route, indent=2))
        # except Exception as e:
        #     logger.error(f"Failed to retrieve current route: {e}")

        # Keep the program running to maintain token refresh
        print("\n=== Program is running ===")
        print("Token will auto-refresh every 50 minutes.")
        print("Press Ctrl+C to stop...\n")

        # Keep main thread alive
        while True:
            time.sleep(10)

    except KeyboardInterrupt:
        print("\n\nShutting down...")
        auth.stop_auto_refresh()

    except Exception as e:
        logger.error(f"Error in main: {e}")
        auth.stop_auto_refresh()
        raise


if __name__ == "__main__":
    main()
