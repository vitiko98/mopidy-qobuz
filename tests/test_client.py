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
    client_ = qobuz_client.Client(APP_ID, SECRET)
    client_.login(EMAIL, PWD)
    yield client_


def test_client(client):
    assert client is not None


def test_track_not_expired(client):
    d_track = qobuz_client.DownloadableTrack.from_id(client, "156914988")
    assert d_track.is_expired() is False


def test_login_raises_authentication_error(client):
    with pytest.raises(qobuz_client.AuthenticationError):
        client.login("foo", "bar")
