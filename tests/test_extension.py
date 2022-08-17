from unittest import mock

from mopidy_qobuz import backend as backend_lib
from mopidy_qobuz import Extension


def test_get_default_config():
    ext = Extension()
    config = ext.get_default_config()

    assert "[qobuz]" in config
    assert "enabled = true" in config
    assert "username =" in config
    assert "password =" in config
    assert "app_id =" in config
    assert "secret =" in config
    assert "quality = 6" in config
    assert "search_album_count = 10" in config
    assert "search_track_count = 10" in config
    assert "search_artist_count = 0" in config


def test_get_config_schema():
    ext = Extension()
    schema = ext.get_config_schema()

    assert "enabled" in schema
    assert "username" in schema
    assert "password" in schema
    assert "password" in schema
    assert "app_id" in schema
    assert "secret" in schema
    assert "quality" in schema
    assert "search_album_count" in schema
    assert "search_track_count" in schema
    assert "search_artist_count" in schema


def test_setup():
    registry = mock.Mock()

    ext = Extension()
    ext.setup(registry)
    calls = [mock.call("backend", backend_lib.QobuzBackend)]
    registry.add.assert_has_calls(calls, any_order=True)
