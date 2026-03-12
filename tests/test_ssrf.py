import pytest
from unittest.mock import patch

from collectors.http_connector import HTTPConnector, SSRFBlockedError

def test_private_ip_blocked():
    connector = HTTPConnector()
    with patch("socket.gethostbyname_ex", return_value=("x", [], ["127.0.0.1"])):
        with pytest.raises(SSRFBlockedError):
            connector._validate_host("http://example.com")
