#!/usr/bin/env python3
"""
Alarm Manager Module
Orchestrates alarm subscription and Kafka consumption for Nokia fault notifications
"""

import time
from threading import Thread, Event
from typing import Optional, Callable

from log_config import get_logger
from token_manager import token_manager
from alarm_subscription import alarm_subscription
from kafka_consumer import kafka_consumer

# Get logger
logger = get_logger(__name__)


class AlarmManager:
    """Manages alarm subscription and consumption lifecycle"""

    _instance = None

    def __new__(cls):
        """Singleton pattern"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize alarm manager"""
        if hasattr(self, '_initialized'):
            return

        self.is_running = False
        self.renewal_thread: Optional[Thread] = None
        self._stop_event = Event()

        self._initialized = True
        logger.info("AlarmManager singleton instance created")

    def initialize(self, message_handler: Optional[Callable] = None):
        """
        Initialize alarm system:
        1. Ensure token is available
        2. Create subscription
        3. Start Kafka consumer
        4. Start renewal thread

        Args:
            message_handler: Optional custom message handler for Kafka messages
        """
        logger.info("=" * 80)
        logger.info("ALARM MANAGER - INITIALIZING")
        logger.info("=" * 80)

        try:
            # Step 1: Check token availability
            if not token_manager.is_token_valid():
                logger.info("Token not valid, initializing token manager...")
                token_manager.initialize()
            else:
                logger.info("✓ Token is valid")

            # Step 2: Create subscription
            logger.info("Creating alarm subscription...")
            subscription_info = alarm_subscription.create_subscription(
                category="NSP-FAULT",
                property_filter="severity = 'warning'"
            )

            topic_id = subscription_info.get('topicId')
            if not topic_id:
                raise ValueError("No topic ID received from subscription")

            # Step 3: Set message handler if provided
            if message_handler:
                kafka_consumer.set_message_handler(message_handler)
                logger.info(f"Custom message handler registered")
            else:
                logger.info("Using default message handler (console output)")

            # Step 4: Start Kafka consumer
            logger.info("Starting Kafka consumer...")
            kafka_consumer.start_consuming(topic_id)

            # Step 5: Start renewal thread
            self._start_renewal_thread()

            self.is_running = True

            logger.info("=" * 80)
            logger.info("✓ ALARM MANAGER INITIALIZED SUCCESSFULLY")
            logger.info(f"Subscription ID: {subscription_info.get('subscriptionId')}")
            logger.info(f"Topic ID: {topic_id}")
            logger.info(f"Listening for fault events...")
            logger.info("=" * 80)

        except Exception as e:
            logger.error("=" * 80)
            logger.error(f"✗ ALARM MANAGER INITIALIZATION FAILED: {e}")
            logger.error("=" * 80)
            raise

    def _start_renewal_thread(self):
        """Start background thread for subscription renewal"""
        if self.renewal_thread and self.renewal_thread.is_alive():
            logger.warning("Renewal thread is already running")
            return

        self._stop_event.clear()
        self.renewal_thread = Thread(
            target=self._renewal_worker,
            daemon=True,
            name="SubscriptionRenewalThread"
        )
        self.renewal_thread.start()
        logger.info(f"✓ Subscription renewal thread started")
        logger.info(f"Renewals will occur every 30 minutes")

    def _renewal_worker(self):
        """
        Worker thread for renewing subscription and token
        Runs every 30 minutes
        """
        logger.info("Subscription renewal worker thread started")

        renewal_interval = 30 * 60  # 30 minutes in seconds

        while not self._stop_event.is_set():
            # Wait for interval or stop event
            if self._stop_event.wait(timeout=renewal_interval):
                logger.info("Stop event received, exiting renewal worker")
                break

            try:
                logger.info("Auto-renewal cycle triggered")

                # Renew token first
                logger.info("Renewing access token...")
                token_manager.refresh_access_token()

                # Then renew subscription
                logger.info("Renewing subscription...")
                alarm_subscription.renew_subscription()

                logger.info("✓ Auto-renewal cycle completed successfully")

            except Exception as e:
                logger.error(f"✗ Auto-renewal failed: {e}")
                logger.error("Will retry on next cycle")

        logger.info("Subscription renewal worker thread stopped")

    def shutdown(self):
        """Shutdown alarm manager gracefully"""
        if not self.is_running:
            logger.info("Alarm manager is not running")
            return

        logger.info("=" * 80)
        logger.info("ALARM MANAGER - SHUTTING DOWN")
        logger.info("=" * 80)

        try:
            # Stop renewal thread
            if self.renewal_thread and self.renewal_thread.is_alive():
                logger.info("Stopping renewal thread...")
                self._stop_event.set()
                self.renewal_thread.join(timeout=5)
                if self.renewal_thread.is_alive():
                    logger.warning("Renewal thread did not stop gracefully")
                else:
                    logger.info("✓ Renewal thread stopped")

            # Stop Kafka consumer
            logger.info("Stopping Kafka consumer...")
            kafka_consumer.stop_consuming()

            # Delete subscription
            logger.info("Deleting subscription...")
            alarm_subscription.delete_subscription()

            self.is_running = False

            logger.info("=" * 80)
            logger.info("✓ ALARM MANAGER SHUTDOWN COMPLETE")
            logger.info("=" * 80)

        except Exception as e:
            logger.error(f"Error during alarm manager shutdown: {e}")

    def get_status(self) -> dict:
        """
        Get alarm manager status

        Returns:
            dict: Status information
        """
        subscription_info = alarm_subscription.get_subscription_info()

        return {
            'is_running': self.is_running,
            'kafka_consuming': kafka_consumer.is_consuming(),
            'subscription_id': subscription_info.get('subscriptionId'),
            'topic_id': subscription_info.get('topicId'),
            'expires_at': subscription_info.get('expiresAt')
        }


# Global alarm manager instance
alarm_manager = AlarmManager()
