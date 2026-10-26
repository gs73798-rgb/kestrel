import io
import urllib.error
import urllib.request
from email.message import Message
from unittest.mock import patch

import pytest

from kestrel.providers.clients import MAX_ATTEMPTS, _backoff_seconds, _post_with_retry


class _Response(io.BytesIO):
    headers = {"Content-Type": "application/json"}


def _http_error(code, retry_after=None):
    headers = Message()
    if retry_after is not None:
        headers["Retry-After"] = retry_after
    return urllib.error.HTTPError("http://test/v1/responses", code, "err", headers, io.BytesIO(b"busy"))


def _request():
    return urllib.request.Request("http://test/v1/responses", data=b"{}", method="POST")


def test_rate_limit_is_retried_then_succeeds():
    sleeps = []
    responses = [_http_error(429, retry_after="1"), _Response(b'{"ok": true}')]

    with patch("kestrel.providers.clients.urllib.request.urlopen", side_effect=responses):
        body, content_type = _post_with_retry(_request(), timeout=5, sleep=sleeps.append)

    assert body == '{"ok": true}'
    assert content_type == "application/json"
    assert sleeps == [1.0]  # 服务端给了 Retry-After，就以它为准


def test_client_error_is_not_retried():
    sleeps = []

    with patch("kestrel.providers.clients.urllib.request.urlopen", side_effect=[_http_error(401)]) as urlopen:
        with pytest.raises(urllib.error.HTTPError):
            _post_with_retry(_request(), timeout=5, sleep=sleeps.append)

    assert urlopen.call_count == 1
    assert sleeps == []


def test_server_error_gives_up_after_max_attempts():
    sleeps = []

    with patch("kestrel.providers.clients.urllib.request.urlopen", side_effect=[_http_error(503)] * MAX_ATTEMPTS) as urlopen:
        with pytest.raises(urllib.error.HTTPError):
            _post_with_retry(_request(), timeout=5, sleep=sleeps.append)

    assert urlopen.call_count == MAX_ATTEMPTS
    assert len(sleeps) == MAX_ATTEMPTS - 1


def test_network_error_is_retried():
    sleeps = []
    responses = [urllib.error.URLError("connection reset"), _Response(b"done")]

    with patch("kestrel.providers.clients.urllib.request.urlopen", side_effect=responses):
        body, _ = _post_with_retry(_request(), timeout=5, sleep=sleeps.append)

    assert body == "done"
    assert len(sleeps) == 1


def test_backoff_honors_retry_after_with_cap_and_grows_exponentially():
    assert _backoff_seconds(0, retry_after="2") == 2.0
    assert _backoff_seconds(0, retry_after="9999") == 10.0
    assert 0.5 <= _backoff_seconds(0) <= 0.75
    assert 1.0 <= _backoff_seconds(1) <= 1.25
