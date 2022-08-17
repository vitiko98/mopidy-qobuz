import pytest


@pytest.fixture
def qobuz_config():
    return {
        "http": {"hostname": "127.0.0.1", "port": "6680"},
        "proxy": {"hostname": "host_mock", "port": "port_mock"},
        "qobuz": {
            "enabled": True,
            "username": "foo",
            "password": "bar",
            "app_id": 12345678,
            "secret": "abcdefghijklmnopq",
            "quality": 6,
            "search_album_count": 10,
            "search_track_count": 10,
            "search_artist_count": 0,
        },
    }
