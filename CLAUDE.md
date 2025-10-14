# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python client for Nokia API authentication that manages OAuth-style tokens with automatic refresh. The project uses a virtual environment and focuses on secure API communication with self-signed SSL certificates.

## Development Setup

### Virtual Environment
Always activate the virtual environment before working:
```bash
source venv/bin/activate  # Linux/Mac
```

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Run the Main Program
```bash
python nokia_api_auth.py
```

## Architecture

### Core Component: `NokiaAPIAuth` Class

The entire authentication logic is centralized in the `NokiaAPIAuth` class in `nokia_api_auth.py`. This class handles:

1. **Token Lifecycle Management**
   - Initial token acquisition via HTTP Basic Auth (`get_initial_token()`)
   - Token refresh using refresh_token (`refresh_access_token()`)
   - Automatic background refresh via daemon thread (`start_auto_refresh()`)

2. **Threading Model**
   - Main thread: Handles API requests and user interaction
   - Daemon thread: Runs `_auto_refresh_worker()` to refresh token every 3600 seconds (60 minutes)
   - Thread control via `Event` object (`_stop_event`) for graceful shutdown

3. **Token Storage**
   - `access_token`: Used in Authorization header for API requests
   - `refresh_token`: Used to obtain new access_token
   - `token_expiry`: datetime object tracking when token expires
   - All tokens stored as instance variables, updated on each refresh

### Authentication Flow

```
Initial Auth:  POST /auth/token (Basic Auth) → access_token + refresh_token
               ↓
Auto Refresh:  Every 60 min → POST /auth/token (with refresh_token) → new tokens
               ↓
API Requests:  Any endpoint (with Authorization: Bearer <access_token>)
```

### Key Methods

- `make_authenticated_request(method, endpoint, **kwargs)`: Helper for making authenticated HTTP requests (GET, POST, PUT, DELETE). Automatically adds Authorization header with current access_token.
- `get_authorization_header()`: Returns dict with Authorization header for manual use.

### SSL Certificate Handling

The API uses self-signed certificates. All requests use `verify=False` and SSL warnings are disabled via `urllib3.disable_warnings()`.

## Configuration

Credentials are in `.env` file (not committed to git):
- `API_BASE_URL`: Base URL of Nokia API
- `API_USERNAME`: Basic auth username
- `API_PASSWORD`: Basic auth password
- `TOKEN_REFRESH_INTERVAL`: Seconds between token refreshes (default: 3600)

## Important Implementation Notes

### Token Refresh Timing
- Tokens expire in 3600 seconds (60 minutes)
- Auto-refresh is triggered every 3600 seconds, not based on expiry time
- The refresh uses the most recent `refresh_token` received (either from initial auth or previous refresh)

### Error Handling
- All HTTP errors raise exceptions and are logged
- Failed auto-refresh is logged but doesn't crash the program
- Check logs for 401 errors indicating token refresh issues

### Thread Safety
- The daemon thread only reads/writes instance variables (`access_token`, `refresh_token`, etc.)
- Main thread can safely read these values for API requests
- No explicit locking needed due to Python's GIL and simple read/write pattern

## Extending the Client

When adding new features:

1. **New API endpoints**: Use `make_authenticated_request()` - don't create new auth logic
2. **Custom headers**: Pass `headers` kwarg to `make_authenticated_request()`, it will merge with Authorization header
3. **Different refresh intervals**: Pass `refresh_interval` parameter to `start_auto_refresh()`
4. **Manual token refresh**: Call `refresh_access_token()` directly if needed before the automatic refresh

## Dependencies

- `requests`: HTTP client for API calls
- `urllib3`: SSL configuration
- `python-dotenv`: Environment variable management (optional, not currently used in main program)
