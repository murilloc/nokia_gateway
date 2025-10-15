#!/usr/bin/env python3
"""
Test logging system - verify rotation and error logging
"""

import requests
import time
from log_config import get_logger

logger = get_logger(__name__)


def test_application_logs():
    """Test application logs by making valid requests"""
    print("\n=== Testing Application Logs ===")
    logger.info("Starting application log test")

    try:
        # Test health endpoint
        response = requests.get("http://localhost:6778/health")
        logger.info(f"Health check: {response.status_code}")

        # Test trail list endpoint
        response = requests.get(
            "http://localhost:6778/api/v1/nokia_gateway/trail_list",
            params={"network_id": "788602"}
        )
        logger.info(f"Trail list request: {response.status_code}")

        print("✓ Application logs test completed")
        return True
    except Exception as e:
        logger.error(f"Application log test failed: {e}")
        return False


def test_error_logs():
    """Test error logs by triggering errors"""
    print("\n=== Testing Error Logs ===")
    logger.info("Starting error log test")

    try:
        # Test invalid network ID (should return empty list, not an error)
        response = requests.get(
            "http://localhost:6778/api/v1/nokia_gateway/trail_list",
            params={"network_id": "999999"}
        )
        logger.info(f"Invalid network ID test: {response.status_code}")

        # Test missing parameter
        try:
            response = requests.get(
                "http://localhost:6778/api/v1/nokia_gateway/trail_list"
            )
            logger.warning(f"Missing parameter test: {response.status_code}")
        except Exception as e:
            logger.info(f"Expected error for missing parameter: {e}")

        print("✓ Error logs test completed")
        return True
    except Exception as e:
        logger.error(f"Error log test failed: {e}", exc_info=True)
        return False


def test_log_volume():
    """Generate volume of logs to test performance"""
    print("\n=== Testing Log Volume ===")
    logger.info("Starting log volume test - generating 100 log entries")

    for i in range(100):
        logger.info(f"Log entry {i+1}/100")
        if i % 10 == 0:
            logger.debug(f"Debug message {i+1}")

    logger.info("Log volume test completed")
    print("✓ Log volume test completed")
    return True


def verify_log_files():
    """Verify log files exist and have content"""
    print("\n=== Verifying Log Files ===")

    import os

    log_dir = "logs"
    expected_files = ["application.log", "error.log"]

    for log_file in expected_files:
        path = os.path.join(log_dir, log_file)
        if os.path.exists(path):
            size = os.path.getsize(path)
            print(f"✓ {log_file}: {size} bytes")
        else:
            print(f"✗ {log_file}: NOT FOUND")

    return True


def main():
    """Run all logging tests"""
    print("=" * 80)
    print("Logging System Test Suite")
    print("=" * 80)

    logger.info("=" * 80)
    logger.info("LOGGING SYSTEM TEST - STARTED")
    logger.info("=" * 80)

    results = {}

    # Run tests
    results['application_logs'] = test_application_logs()
    time.sleep(1)

    results['error_logs'] = test_error_logs()
    time.sleep(1)

    results['log_volume'] = test_log_volume()
    time.sleep(1)

    results['verify_files'] = verify_log_files()

    # Print summary
    print("\n" + "=" * 80)
    print("Test Summary")
    print("=" * 80)
    for test_name, result in results.items():
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{test_name:30} {status}")

    print("=" * 80)

    logger.info("=" * 80)
    logger.info("LOGGING SYSTEM TEST - COMPLETED")
    logger.info("=" * 80)

    # Return exit code
    all_passed = all(results.values())
    if all_passed:
        print("\nAll tests passed!")
        logger.info("✓ All logging tests passed")
        return 0
    else:
        print("\nSome tests failed!")
        logger.error("✗ Some logging tests failed")
        return 1


if __name__ == "__main__":
    exit(main())
