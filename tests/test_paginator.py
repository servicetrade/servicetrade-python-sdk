"""Tests for the Paginator class."""

import base64
import json
import time

import responses

from servicetrade import Paginator, ServicetradeClient

BASE_URL = "https://api.servicetrade.com"
API_PREFIX = "/api"


def create_mock_token(exp_offset: int = 3600) -> str:
    header = (
        base64.urlsafe_b64encode(json.dumps({"alg": "HS256"}).encode())
        .decode()
        .rstrip("=")
    )
    payload = (
        base64.urlsafe_b64encode(
            json.dumps({"exp": int(time.time()) + exp_offset}).encode()
        )
        .decode()
        .rstrip("=")
    )
    signature = base64.urlsafe_b64encode(b"signature").decode().rstrip("=")
    return f"{header}.{payload}.{signature}"


def mock_auth() -> str:
    token = create_mock_token()
    responses.add(
        responses.POST,
        f"{BASE_URL}{API_PREFIX}/oauth2/token",
        json={"access_token": token},
        status=200,
    )
    return token


class TestPaginator:
    """Test Paginator class."""

    @responses.activate
    def test_single_page(self):
        mock_auth()
        responses.add(
            responses.GET,
            f"{BASE_URL}{API_PREFIX}/job",
            json={"data": {
                "jobs": [{"id": 1}, {"id": 2}],
                "totalPages": 1,
            }},
            status=200,
        )

        client = ServicetradeClient(client_id="id", client_secret="secret")
        client.login()

        paginator = Paginator(client, "/job", "jobs")
        items = list(paginator)

        assert items == [{"id": 1}, {"id": 2}]

    @responses.activate
    def test_multi_page(self):
        mock_auth()
        # Page 1
        responses.add(
            responses.GET,
            f"{BASE_URL}{API_PREFIX}/job",
            json={"data": {
                "jobs": [{"id": 1}, {"id": 2}],
                "totalPages": 3,
            }},
            status=200,
        )
        # Page 2
        responses.add(
            responses.GET,
            f"{BASE_URL}{API_PREFIX}/job",
            json={"data": {
                "jobs": [{"id": 3}, {"id": 4}],
                "totalPages": 3,
            }},
            status=200,
        )
        # Page 3
        responses.add(
            responses.GET,
            f"{BASE_URL}{API_PREFIX}/job",
            json={"data": {
                "jobs": [{"id": 5}],
                "totalPages": 3,
            }},
            status=200,
        )

        client = ServicetradeClient(client_id="id", client_secret="secret")
        client.login()

        paginator = Paginator(client, "/job", "jobs")
        items = list(paginator)

        assert len(items) == 5
        assert items == [{"id": 1}, {"id": 2}, {"id": 3}, {"id": 4}, {"id": 5}]

    @responses.activate
    def test_empty_results(self):
        mock_auth()
        responses.add(
            responses.GET,
            f"{BASE_URL}{API_PREFIX}/job",
            json={"data": {
                "jobs": [],
                "totalPages": 1,
            }},
            status=200,
        )

        client = ServicetradeClient(client_id="id", client_secret="secret")
        client.login()

        paginator = Paginator(client, "/job", "jobs")
        items = list(paginator)

        assert items == []

    @responses.activate
    def test_missing_items_key(self):
        mock_auth()
        responses.add(
            responses.GET,
            f"{BASE_URL}{API_PREFIX}/job",
            json={"data": {
                "totalPages": 1,
            }},
            status=200,
        )

        client = ServicetradeClient(client_id="id", client_secret="secret")
        client.login()

        paginator = Paginator(client, "/job", "jobs")
        items = list(paginator)

        assert items == []

    @responses.activate
    def test_passes_custom_params(self):
        mock_auth()
        responses.add(
            responses.GET,
            f"{BASE_URL}{API_PREFIX}/job",
            json={"data": {
                "jobs": [{"id": 1}],
                "totalPages": 1,
            }},
            status=200,
        )

        client = ServicetradeClient(client_id="id", client_secret="secret")
        client.login()

        paginator = Paginator(client, "/job", "jobs", params={"status": "open"})
        list(paginator)

        # Verify custom params were sent along with page param
        request_url = responses.calls[-1].request.url
        assert "status=open" in request_url
        assert "page=1" in request_url
