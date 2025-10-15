#!/usr/bin/env python3
"""
Test script for Nokia Gateway API
"""

import requests
import json
import time

# Disable SSL warnings
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

GATEWAY_URL = "http://localhost:6778"


def test_root():
    """Test root endpoint"""
    print("\n=== Testing Root Endpoint ===")
    try:
        response = requests.get(f"{GATEWAY_URL}/")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_health():
    """Test health check endpoint"""
    print("\n=== Testing Health Check Endpoint ===")
    try:
        response = requests.get(f"{GATEWAY_URL}/health")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_trail_list(network_id="788602"):
    """Test trail list endpoint"""
    print(f"\n=== Testing Trail List Endpoint (network_id={network_id}) ===")
    try:
        url = f"{GATEWAY_URL}/api/v1/nokia_gateway/trail_list"
        params = {"network_id": network_id}

        print(f"Request URL: {url}")
        print(f"Parameters: {params}")

        response = requests.get(url, params=params, timeout=30)
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"Response type: {type(data)}")
            if isinstance(data, list):
                print(f"Number of trails: {len(data)}")
                if len(data) > 0:
                    print(f"\nFirst trail sample:")
                    print(json.dumps(data[0], indent=2))
            else:
                print(f"Response: {json.dumps(data, indent=2)}")
            return True
        else:
            print(f"Error Response: {response.text}")
            return False

    except Exception as e:
        print(f"Error: {e}")
        return False


def test_trail_list_invalid_network():
    """Test trail list endpoint with invalid network ID"""
    print("\n=== Testing Trail List Endpoint with Invalid Network ID ===")
    try:
        url = f"{GATEWAY_URL}/api/v1/nokia_gateway/trail_list"
        params = {"network_id": "999999"}

        response = requests.get(url, params=params, timeout=30)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")

        # Nokia API returns 200 with empty list for non-existent network IDs
        # So we expect 200 status code with empty list
        if response.status_code == 200:
            data = response.json()
            return isinstance(data, list) and len(data) == 0
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("Nokia Gateway API - Test Suite")
    print("=" * 60)

    results = {}

    # Run tests
    results['root'] = test_root()
    time.sleep(1)

    results['health'] = test_health()
    time.sleep(1)

    results['trail_list'] = test_trail_list()
    time.sleep(1)

    results['trail_list_invalid'] = test_trail_list_invalid_network()

    # Print summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    for test_name, result in results.items():
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{test_name:30} {status}")

    print("=" * 60)

    # Return exit code
    all_passed = all(results.values())
    if all_passed:
        print("\nAll tests passed!")
        return 0
    else:
        print("\nSome tests failed!")
        return 1


if __name__ == "__main__":
    exit(main())
