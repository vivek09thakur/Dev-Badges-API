import http.client
import socket
import ssl
import urllib.error
import urllib.request
from typing import Optional

from .constants import HTTP_TIMEOUT


class UpstreamError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def _create_connection(address, timeout=socket._GLOBAL_DEFAULT_TIMEOUT, source_address=None):
    infos = socket.getaddrinfo(*address, type=socket.SOCK_STREAM)
    infos.sort(key=lambda info: info[0] != socket.AF_INET)
    err: Optional[OSError] = None
    for family, kind, proto, _, sockaddr in infos:
        sock = socket.socket(family, kind, proto)
        try:
            if timeout is not socket._GLOBAL_DEFAULT_TIMEOUT:
                sock.settimeout(timeout)
            if source_address:
                sock.bind(source_address)
            sock.connect(sockaddr)
            return sock
        except OSError as e:
            err = e
            sock.close()
    raise err or OSError(f"no addresses found for {address[0]}")


class _Ipv4FirstHttpsConnection(http.client.HTTPSConnection):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._create_connection = _create_connection


class _Ipv4FirstHttpsHandler(urllib.request.HTTPSHandler):
    def https_open(self, req):
        return self.do_open(_Ipv4FirstHttpsConnection, req, context=self._context)


class HttpClient:
    def __init__(self, timeout: int = HTTP_TIMEOUT):
        self.timeout = timeout
        self.opener = urllib.request.build_opener(_Ipv4FirstHttpsHandler(context=ssl.create_default_context()))

    def get_bytes(self, url: str, headers: Optional[dict[str, str]] = None) -> bytes:
        req = urllib.request.Request(url, headers=headers or {})
        try:
            with self.opener.open(req, timeout=self.timeout) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            raise UpstreamError(404 if e.code == 404 else 502, f"Upstream returned {e.code}")
        except urllib.error.URLError as e:
            raise UpstreamError(502, f"Upstream unreachable: {e.reason}")

    def get(self, url: str, headers: Optional[dict[str, str]] = None) -> str:
        return self.get_bytes(url, headers).decode("utf-8", errors="replace")
