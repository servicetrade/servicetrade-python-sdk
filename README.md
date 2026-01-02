# ServiceTrade Python SDK

A Python client for the ServiceTrade REST API with OAuth2 authentication and automatic token refresh.

## Installation

```bash
pip install servicetrade
```

## Quick Start

### Using Username/Password

```python
from servicetrade import ServicetradeClient

client = ServicetradeClient(
    username="user@example.com",
    password="your_password"
)

# Login to get access token
client.login()

# Make API requests
jobs = client.get("/job")
print(jobs)
```

### Using Client Credentials

```python
from servicetrade import ServicetradeClient

client = ServicetradeClient(
    client_id="your_client_id",
    client_secret="your_client_secret"
)

client.login()
jobs = client.get("/job")
```

### Using Refresh Token (Recommended)

```python
from servicetrade import ServicetradeClient

client = ServicetradeClient(
    refresh_token="your_refresh_token"
)

client.login()
jobs = client.get("/job")
```

### Using Pre-existing Token

```python
from servicetrade import ServicetradeClient

client = ServicetradeClient(
    token="your_bearer_token",
    # Provide credentials for auto-refresh
    username="user@example.com",
    password="your_password"
)

# No login needed if token is valid
jobs = client.get("/job")
```

## API Methods

### HTTP Methods

```python
# GET request
result = client.get("/job/123")

# POST request
result = client.post("/job", {"name": "New Job", "location": "123 Main St"})

# PUT request
result = client.put("/job/123", {"name": "Updated Job"})

# DELETE request
result = client.delete("/job/123")
```

### File Attachments

```python
from servicetrade import ServicetradeClient, FileAttachment

client = ServicetradeClient(username="user", password="pass")
client.login()

# Upload a file
file = FileAttachment(
    value=b"file contents here",
    filename="document.pdf",
    content_type="application/pdf"
)

result = client.attach(
    {"entityType": "job", "entityId": 123},
    file
)
```

### Reading from a file path

```python
from pathlib import Path
from servicetrade import FileAttachment

file = FileAttachment(
    value=Path("/path/to/document.pdf"),
    filename="document.pdf",
    content_type="application/pdf"
)
```

## Configuration Options

```python
client = ServicetradeClient(
    # API Configuration
    base_url="https://api.servicetrade.com",  # Default
    api_prefix="/api",                         # Default
    user_agent="My App/1.0",                   # Custom user agent

    # Authentication
    username="user@example.com",
    password="password",
    # OR
    client_id="client_id",
    client_secret="client_secret",
    # OR
    refresh_token="refresh_token",
    # OR
    token="existing_bearer_token",

    # Options
    auto_refresh_auth=True,                    # Auto-refresh tokens (default)

    # Callbacks
    on_set_auth=lambda token: save_token(token),
    on_unset_auth=lambda: clear_token(),
)
```

## Custom Headers

```python
client.set_custom_header("X-Custom-Header", "value")
```

## Error Handling

```python
from servicetrade import (
    ServicetradeClient,
    ServicetradeAuthError,
    ServicetradeAPIError,
)

client = ServicetradeClient(username="user", password="pass")

try:
    client.login()
except ServicetradeAuthError as e:
    print(f"Authentication failed: {e.message}")
    print(f"Status code: {e.status_code}")

try:
    result = client.get("/nonexistent")
except ServicetradeAPIError as e:
    print(f"API error: {e.message}")
    print(f"Status code: {e.status_code}")
    print(f"Response data: {e.response_data}")
```

## Authentication Flow

The SDK supports three OAuth2 grant types, prioritized in this order:

1. **Refresh Token Grant** - Most secure, only stores refresh token
2. **Client Credentials Grant** - For service-to-service authentication
3. **Password Grant** - Direct user authentication

### Automatic Token Refresh

By default, the SDK automatically refreshes tokens when:
- A request returns a 401 Unauthorized response
- The token is about to expire (within 5 minutes of expiry)

To disable automatic refresh:

```python
client = ServicetradeClient(
    username="user",
    password="pass",
    auto_refresh_auth=False
)
```

## Development

### Setup

```bash
# Clone the repository
git clone https://github.com/servicetrade/servicetrade-python-sdk.git
cd servicetrade-python-sdk

# Install development dependencies
pip install -e ".[dev]"
```

### Running Tests

```bash
pytest
```

### Running Tests with Coverage

```bash
pytest --cov=servicetrade --cov-report=html
```

### Linting and Formatting

```bash
# Check linting
ruff check src tests

# Format code
ruff format src tests

# Type checking
mypy src
```

## License

MIT License - see LICENSE file for details.
