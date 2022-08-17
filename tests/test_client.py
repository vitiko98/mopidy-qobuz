import os

import pytest

from mopidy_qobuz import client as qobuz_client

EMAIL = os.environ.get("QOBUZ_EMAIL")
PWD = os.environ.get("QOBUZ_PASSWORD")
APP_ID = os.environ.get("QOBUZ_APP_ID")
SECRET = os.environ.get("QOBUZ_SECRET")

pytestmark = pytest.mark.skipif(
    any(item is None for item in (EMAIL, PWD, APP_ID, SECRET)),
    reason="QOBUZ env vars not provided",
)


@pytest.fixture(scope="session")
def client():
    yield qobuz_client.Client(APP_ID, SECRET)


def test_client(client):
    assert client is not None


def test_login_raises_authentication_error(client):
    with pytest.raises(qobuz_client.AuthenticationError):
        client.login("foo", "bar")


def test_login(client):
    client.login(EMAIL, PWD)
