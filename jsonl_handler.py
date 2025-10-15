#!/usr/bin/env python3
"""
JSONL Handler Module
Handles writing Kafka messages to JSONL (JSON Lines) format file
"""

import os
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
from dotenv import load_dotenv

from log_config import get_logger

# Get logger
logger = get_logger(__name__)

# Load environment variables
load_dotenv()


class JSONLHandler:
    """Handler for writing Kafka messages to JSONL file"""

    def __init__(self):
        """Initialize JSONL handler"""
        self.output_file = os.getenv('KAFKA_MESSAGES_FILE', 'logs/kafka_messages.jsonl')

        # Ensure directory exists
        output_dir = Path(self.output_file).parent
        output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"JSONLHandler initialized")
        logger.info(f"Output file: {self.output_file}")

    def write_message(self, message: Dict[Any, Any]) -> bool:
        """
        Write a Kafka message to JSONL file

        Args:
            message: Message dict from Kafka

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Add metadata
            enriched_message = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "received_at": datetime.now().isoformat(),
                "message": message
            }

            # Write to file (append mode)
            with open(self.output_file, 'a', encoding='utf-8') as f:
                json_line = json.dumps(enriched_message, ensure_ascii=False)
                f.write(json_line + '\n')

            logger.debug(f"Message written to {self.output_file}")
            return True

        except Exception as e:
            logger.error(f"Failed to write message to JSONL: {e}", exc_info=True)
            return False

    def get_message_count(self) -> int:
        """
        Get total number of messages in JSONL file

        Returns:
            int: Number of messages (lines) in file
        """
        try:
            if not Path(self.output_file).exists():
                return 0

            with open(self.output_file, 'r', encoding='utf-8') as f:
                return sum(1 for _ in f)

        except Exception as e:
            logger.error(f"Failed to count messages: {e}")
            return 0

    def get_file_size(self) -> int:
        """
        Get size of JSONL file in bytes

        Returns:
            int: File size in bytes
        """
        try:
            if not Path(self.output_file).exists():
                return 0

            return Path(self.output_file).stat().st_size

        except Exception as e:
            logger.error(f"Failed to get file size: {e}")
            return 0

    def clear_file(self) -> bool:
        """
        Clear the JSONL file (useful for testing or maintenance)

        Returns:
            bool: True if successful
        """
        try:
            if Path(self.output_file).exists():
                Path(self.output_file).unlink()
                logger.info(f"Cleared JSONL file: {self.output_file}")
            return True

        except Exception as e:
            logger.error(f"Failed to clear JSONL file: {e}")
            return False


# Global JSONL handler instance
jsonl_handler = JSONLHandler()
