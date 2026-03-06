# ServiceTrade Python SDK

A Python client for the ServiceTrade REST API with OAuth2 authentication and automatic token refresh.

## Installation

```bash
pip install servicetrade
```

## Quick Start

### Using Client Credentials

```python
from servicetrade import ServicetradeClient

client = ServicetradeClient(
    client_id="your-client-id",
    client_secret="your-client-secret"
)

# No need to call login() — the SDK authenticates lazily on the first API call.
jobs = client.get("/job")
print(jobs)
```

### Using Refresh Token

```python
from servicetrade import ServicetradeClient

client = ServicetradeClient(
    refresh_token="your-refresh-token"
)

jobs = client.get("/job")
```

### Using a Pre-existing Token

```python
from servicetrade import ServicetradeClient

client = ServicetradeClient(
    token="your-bearer-token",
    # Provide credentials for auto-refresh when the token expires
    client_id="your-client-id",
    client_secret="your-client-secret"
)

# No login needed if token is valid
jobs = client.get("/job")
```

## API Methods

### HTTP Methods

```python
# GET request
result = client.get("/job/123")

# GET with query parameters
data = client.get("/job", params={"status": "scheduled", "locationId": 456})
jobs = data["jobs"]

# POST request
job = client.post("/job", {
    "type": "inspection",
    "description": "Quarterly HVAC Inspection",
    "locationId": 123,
    "vendorId": 456,
})

# PUT request
client.put("/job/123", {"description": "Updated Inspection Description"})

# DELETE request (returns None)
client.delete("/location/456")
```

### Paginator

Iterate over all pages of a paginated endpoint automatically:

```python
from servicetrade import Paginator, ServicetradeClient

client = ServicetradeClient(
    client_id="your-client-id",
    client_secret="your-client-secret"
)

paginator = Paginator(client, "/job", "jobs", params={"status": "scheduled"})
for job in paginator:
    print(f"Job #{job['id']}: {job['description']}")
```

The `Paginator` constructor takes:
- `client` — a `ServicetradeClient` instance
- `path` — the API endpoint path (e.g., `"/job"`)
- `items_key` — the key in the response that contains the list of items (e.g., `"jobs"`)
- `params` — optional dict of query parameters to include on every request

### File Attachments

```python
from servicetrade import ServicetradeClient, FileAttachment

client = ServicetradeClient(client_id="your-client-id", client_secret="your-client-secret")

# Upload a file
file = FileAttachment(
    value=b"file contents here",
    filename="document.pdf",
    content_type="application/pdf"
)

result = client.attach(
    {"entityType": 3, "entityId": 123, "purposeId": 7},
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

## Response Handling

### Return values

- `get()`, `post()`, `put()` return the `data` field from the response when present, or the full response dict/list otherwise.
- `delete()` returns `None`.

### Accessing the full response

Use `get_last_response()` to access status code, headers, and full body:

```python
result = client.get("/job/123")
response = client.get_last_response()

print(response.status_code)   # 200
print(response.is_success())  # True
print(response.body)          # Full response body (dict)
print(response.headers)       # Response headers (dict)
```

### Accessing the auth token

```python
token = client.get_auth_token()
```

## Configuration Options

```python
client = ServicetradeClient(
    # API Configuration
    base_url="https://api.servicetrade.com",  # Default
    api_prefix="/api",                         # Default
    user_agent="My App/1.0",                   # Custom user agent

    # Authentication (pick one)
    client_id="your-client-id",
    client_secret="your-client-secret",
    # OR
    refresh_token="your-refresh-token",
    # OR
    token="your-bearer-token",

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

client = ServicetradeClient(client_id="your-client-id", client_secret="your-client-secret")

try:
    result = client.get("/nonexistent")
except ServicetradeAPIError as e:
    print(f"API error: {e.message}")
    print(f"Status code: {e.status_code}")
    print(f"Response data: {e.response_data}")

    # Structured errors from ServiceTrade API
    if e.error_messages:
        print(f"Errors: {e.error_messages}")
    if e.validation:
        print(f"Validation: {e.validation}")
```

## Authentication Flow

The SDK supports two OAuth2 grant types, prioritized in this order:

1. **Refresh Token Grant** — Most secure, only stores refresh token
2. **Client Credentials Grant** — For service-to-service authentication

### Lazy Authentication

The SDK automatically authenticates on the first API call if no token exists. You can also call `login()` explicitly for eager authentication:

```python
client = ServicetradeClient(client_id="your-client-id", client_secret="your-client-secret")

# Eager authentication (optional)
client.login()

# Or just make API calls — login happens automatically
jobs = client.get("/job")
```

### Automatic Token Refresh

By default, the SDK automatically refreshes tokens when:
- A request returns a 401 Unauthorized response
- The token is about to expire (within 5 minutes of expiry)

To disable automatic refresh:

```python
client = ServicetradeClient(
    client_id="id",
    client_secret="secret",
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

### Type Checking

```bash
mypy src
```

## License

MIT License - see LICENSE file for details.
