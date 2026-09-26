"""Rate-limit key: the visitor's IP, including behind a local Cloudflare Tunnel."""

from __future__ import annotations

from starlette.requests import Request

from app.deps import client_key


def request(host: str, headers: dict[str, str] | None = None) -> Request:
    raw = [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()]
    return Request(
        {"type": "http", "client": (host, 1234), "headers": raw, "method": "GET", "path": "/"}
    )


def test_direct_clients_are_keyed_by_their_address():
    assert client_key(request("203.0.113.9")) == "203.0.113.9"


def test_tunnel_requests_use_the_visitor_address():
    assert client_key(request("127.0.0.1", {"CF-Connecting-IP": "198.51.100.7"})) == "198.51.100.7"
    assert client_key(request("::1", {"CF-Connecting-IP": "198.51.100.8"})) == "198.51.100.8"


def test_the_header_is_ignored_from_non_local_clients():
    # a remote client can't pick its own rate-limit bucket
    assert client_key(request("203.0.113.9", {"CF-Connecting-IP": "1.2.3.4"})) == "203.0.113.9"
