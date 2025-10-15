#!/usr/bin/env python3
"""
Alarm Subscription Service
Handles Nokia API alarm/fault subscription management
"""

import requests
import os
import urllib3
from typing import Dict, Optional
from datetime import datetime
from dotenv import load_dotenv

from log_config import get_logger
from token_manager import token_manager

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Get logger
logger = get_logger(__name__)

# Load environment variables
load_dotenv()


class AlarmSubscription:
    """Manages alarm/fault subscriptions with Nokia API"""

    def __init__(self):
        """Initialize alarm subscription manager"""
        self.subscription_host = os.getenv('SUBSCRIPTION_HOST', '10.73.0.181')
        self.subscription_port = int(os.getenv('SUBSCRIPTION_PORT', '8544'))
        self.subscription_timeout = int(os.getenv('SUBSCRIPTION_TIMEOUT', '3400000'))

        self.subscription_id: Optional[str] = None
        self.topic_id: Optional[str] = None
        self.expires_at: Optional[str] = None

        logger.info("AlarmSubscription initialized")
        logger.info(f"Subscription Host: {self.subscription_host}:{self.subscription_port}")

    def create_subscription(self, category: str = "NSP-FAULT", property_filter: str = "severity = 'warning'") -> Dict:
        """
        Create a subscription to Nokia notification service

        Args:
            category: Notification category (default: NSP-FAULT)
            property_filter: Filter expression (default: severity = 'warning')

        Returns:
            dict: Subscription information including subscriptionId, topicId, expiresAt
        """
        url = f"https://{self.subscription_host}:{self.subscription_port}/nbi-notification/api/v1/notifications/subscriptions"

        payload = {
            "categories": [
                {
                    "name": category,
                    "propertyFilter": property_filter
                }
            ]
        }

        try:
            logger.info(f"Creating subscription for category: {category}")
            logger.info(f"Subscription URL: {url}")
            logger.debug(f"Property filter: {property_filter}")

            # Get authorization header
            headers = token_manager.get_authorization_header()
            headers["Content-Type"] = "application/json"

            response = requests.post(
                url,
                json=payload,
                headers=headers,
                verify=False,
                timeout=30
            )

            logger.debug(f"Subscription response status: {response.status_code}")
            response.raise_for_status()

            response_data = response.json()
            logger.debug(f"Subscription response: {response_data}")

            # Extract subscription info
            if 'response' in response_data and 'data' in response_data['response']:
                data = response_data['response']['data']
            else:
                data = response_data

            self.subscription_id = data.get('subscriptionId')
            self.topic_id = data.get('topicId')
            self.expires_at = data.get('expiresAt')

            subscription_info = {
                'subscriptionId': self.subscription_id,
                'topicId': self.topic_id,
                'expiresAt': self.expires_at
            }

            logger.info(f"✓ Subscription created successfully")
            logger.info(f"Subscription ID: {self.subscription_id}")
            logger.info(f"Topic ID: {self.topic_id}")
            logger.info(f"Expires at: {self.expires_at}")

            return subscription_info

        except requests.exceptions.RequestException as e:
            logger.error(f"✗ Failed to create subscription: {e}")
            raise

    def renew_subscription(self) -> bool:
        """
        Renew existing subscription

        Returns:
            bool: True if renewal successful, False otherwise
        """
        if not self.subscription_id:
            logger.error("No subscription ID available for renewal")
            return False

        url = f"https://{self.subscription_host}:{self.subscription_port}/nbi-notification/api/v1/notifications/subscriptions/{self.subscription_id}/renewals"

        try:
            logger.info(f"Renewing subscription: {self.subscription_id}")

            # Get authorization header
            headers = token_manager.get_authorization_header()
            headers["Content-Type"] = "application/json"

            response = requests.post(
                url,
                json={},
                headers=headers,
                verify=False,
                timeout=30
            )

            response.raise_for_status()

            logger.info(f"✓ Subscription {self.subscription_id} renewed successfully")
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"✗ Failed to renew subscription: {e}")
            return False

    def delete_subscription(self) -> bool:
        """
        Delete existing subscription

        Returns:
            bool: True if deletion successful, False otherwise
        """
        if not self.subscription_id:
            logger.warning("No subscription ID available for deletion")
            return False

        url = f"https://{self.subscription_host}:{self.subscription_port}/nbi-notification/api/v1/notifications/subscriptions/{self.subscription_id}"

        try:
            logger.info(f"Deleting subscription: {self.subscription_id}")

            # Get authorization header
            headers = token_manager.get_authorization_header()

            response = requests.delete(
                url,
                headers=headers,
                verify=False,
                timeout=30
            )

            response.raise_for_status()

            logger.info(f"✓ Subscription {self.subscription_id} deleted successfully")
            self.subscription_id = None
            self.topic_id = None
            self.expires_at = None
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"✗ Failed to delete subscription: {e}")
            return False

    def get_subscription_info(self) -> Dict:
        """
        Get current subscription information

        Returns:
            dict: Subscription info
        """
        return {
            'subscriptionId': self.subscription_id,
            'topicId': self.topic_id,
            'expiresAt': self.expires_at
        }


# Global alarm subscription instance
alarm_subscription = AlarmSubscription()
