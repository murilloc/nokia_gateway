#!/usr/bin/env python3
"""
Kafka Consumer Module
Handles Kafka connection and message consumption for Nokia alarms/faults
"""

import os
import json
import ssl
from threading import Thread, Event
from typing import Optional, Callable
from kafka import KafkaConsumer
from kafka.errors import KafkaError
from dotenv import load_dotenv

from log_config import get_logger
from jsonl_handler import jsonl_handler

# Get logger
logger = get_logger(__name__)

# Load environment variables
load_dotenv()


class NokiaKafkaConsumer:
    """Kafka consumer for Nokia alarm/fault notifications"""

    def __init__(self):
        """Initialize Kafka consumer"""
        self.kafka_broker = os.getenv('KAFKA_BROKER', '10.73.0.181')
        self.kafka_port = int(os.getenv('KAFKA_PORT', '9193'))
        self.kafka_group_id = os.getenv('KAFKA_GROUP_ID', 'nokia-gateway-group')

        # Certificate paths
        self.ca_cert = os.getenv('CA', 'config/certs/nsp.truststore')
        self.client_cert = os.getenv('PEM_CERT', 'config/certs/nfmt.pem')
        self.client_key = os.getenv('KEY', 'config/certs/key.pem')
        self.passphrase = os.getenv('PASSPHRASE', 'NokiaNfmt1!')

        self.consumer: Optional[KafkaConsumer] = None
        self.consumer_thread: Optional[Thread] = None
        self._stop_event = Event()
        self.message_handler: Optional[Callable] = None
        self.topic_id: Optional[str] = None

        logger.info("NokiaKafkaConsumer initialized")
        logger.info(f"Kafka Broker: {self.kafka_broker}:{self.kafka_port}")
        logger.info(f"Group ID: {self.kafka_group_id}")

    def create_consumer(self, topic_id: str) -> KafkaConsumer:
        """
        Create Kafka consumer with SSL configuration

        Args:
            topic_id: Kafka topic ID to subscribe to

        Returns:
            KafkaConsumer: Configured Kafka consumer instance
        """
        self.topic_id = topic_id

        # SSL context configuration
        ssl_context = ssl.create_default_context(
            purpose=ssl.Purpose.SERVER_AUTH,
            cafile=self.ca_cert
        )
        ssl_context.load_cert_chain(
            certfile=self.client_cert,
            keyfile=self.client_key,
            password=self.passphrase
        )
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        try:
            logger.info(f"Creating Kafka consumer for topic: {topic_id}")

            consumer = KafkaConsumer(
                topic_id,
                bootstrap_servers=f"{self.kafka_broker}:{self.kafka_port}",
                group_id=self.kafka_group_id,
                auto_offset_reset='earliest',
                enable_auto_commit=True,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')) if m else None,
                security_protocol='SSL',
                ssl_context=ssl_context
            )

            logger.info("✓ Kafka consumer created successfully")
            return consumer

        except Exception as e:
            logger.error(f"✗ Failed to create Kafka consumer: {e}")
            raise

    def set_message_handler(self, handler: Callable):
        """
        Set message handler callback

        Args:
            handler: Callable that takes message as parameter
        """
        self.message_handler = handler
        logger.info(f"Message handler set: {handler.__name__}")

    def start_consuming(self, topic_id: str):
        """
        Start consuming messages in background thread

        Args:
            topic_id: Kafka topic ID to consume from
        """
        if self.consumer_thread and self.consumer_thread.is_alive():
            logger.warning("Consumer thread is already running")
            return

        try:
            # Create consumer
            self.consumer = self.create_consumer(topic_id)

            # Start consumer thread
            self._stop_event.clear()
            self.consumer_thread = Thread(
                target=self._consume_worker,
                daemon=True,
                name="KafkaConsumerThread"
            )
            self.consumer_thread.start()

            logger.info(f"✓ Started consuming from topic: {topic_id}")
            logger.info(f"Consumer thread: {self.consumer_thread.name}")

        except Exception as e:
            logger.error(f"✗ Failed to start consuming: {e}")
            raise

    def _consume_worker(self):
        """Worker thread for consuming Kafka messages"""
        logger.info("Kafka consumer worker thread started")
        logger.info(f"Listening for messages on topic: {self.topic_id}")

        message_count = 0

        try:
            for message in self.consumer:
                if self._stop_event.is_set():
                    logger.info("Stop event received, exiting consumer worker")
                    break

                message_count += 1

                try:
                    # Log message metadata
                    logger.debug(f"Received message from partition {message.partition}, offset {message.offset}")

                    # Get message value
                    message_value = message.value

                    if message_value:
                        logger.info(f"✓ Message #{message_count} received from Kafka")
                        logger.debug(f"Message content: {json.dumps(message_value, indent=2)}")

                        # Call message handler if set
                        if self.message_handler:
                            self.message_handler(message_value)
                        else:
                            # Default: print to console
                            self._default_message_handler(message_value)

                except Exception as e:
                    logger.error(f"✗ Error processing message: {e}", exc_info=True)

        except KafkaError as e:
            logger.error(f"✗ Kafka error in consumer worker: {e}")
        except Exception as e:
            logger.error(f"✗ Unexpected error in consumer worker: {e}", exc_info=True)
        finally:
            logger.info(f"Kafka consumer worker stopped. Total messages processed: {message_count}")

    def _default_message_handler(self, message: dict):
        """
        Default message handler - prints to console and writes to JSONL file

        Args:
            message: Message dict from Kafka
        """
        # Write to JSONL file
        jsonl_handler.write_message(message)

        # Print to console
        print("\n" + "=" * 80)
        print("NEW ALARM/FAULT EVENT")
        print("=" * 80)
        print(json.dumps(message, indent=2))
        print("=" * 80 + "\n")

    def stop_consuming(self):
        """Stop consuming messages"""
        if not self.consumer_thread or not self.consumer_thread.is_alive():
            logger.debug("Consumer thread is not running")
            return

        logger.info("Stopping Kafka consumer...")
        self._stop_event.set()

        # Close consumer
        if self.consumer:
            try:
                self.consumer.close()
                logger.info("Kafka consumer closed")
            except Exception as e:
                logger.error(f"Error closing Kafka consumer: {e}")

        # Wait for thread to finish
        if self.consumer_thread:
            self.consumer_thread.join(timeout=5)
            if self.consumer_thread.is_alive():
                logger.warning("Consumer thread did not stop gracefully within timeout")
            else:
                logger.info("✓ Kafka consumer thread stopped successfully")

    def is_consuming(self) -> bool:
        """
        Check if consumer is actively consuming

        Returns:
            bool: True if consumer thread is alive
        """
        return self.consumer_thread is not None and self.consumer_thread.is_alive()


# Global Kafka consumer instance
kafka_consumer = NokiaKafkaConsumer()
