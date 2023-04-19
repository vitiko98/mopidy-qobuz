import os

import pytest

from mopidy_qobuz import client as qobuz_client
from mopidy_qobuz import browse


def test_read_yaml_folder():
    result = browse._read_yaml_folder("tests/data")
    assert result

    assert result["Test list"] == {"2010s Hip Hop": ["qobuz:album:0060253743926"]}


@pytest.fixture
def config():
    return {"custom_libraries": "tests/data"}


def test_get_callable_custom():
    result = browse._get_callable("qobuz:custom")
    assert result == browse._browse_custom


def test_get_callable_custom_sub():
    result = browse._get_callable("qobuz:custom:Test list")
    assert result == browse._browse_custom_sub


def test_get_callable_custom_sub_items():
    result = browse._get_callable("qobuz:custom:Test list:2010s Hip Hop")
    assert result == browse._browse_custom_sub_items


def test_browse_custom(config):
    result = browse._browse_custom(uri="test", client=None, config=config)
    assert result == [
        browse.models.Ref.directory(name="Test list", uri="qobuz:custom:Test list")
    ]


def test_browse_custom_sub(config):
    result = browse._browse_custom_sub(
        uri="qobuz:custom:Test list", client=None, config=config
    )
    assert result == [
        browse.models.Ref.directory(
            name="2010s Hip Hop", uri="qobuz:custom:Test list:2010s Hip Hop"
        )
    ]


EMAIL = os.environ.get("QOBUZ_EMAIL")
PWD = os.environ.get("QOBUZ_PASSWORD")
APP_ID = os.environ.get("QOBUZ_APP_ID")
SECRET = os.environ.get("QOBUZ_SECRET")


_skip = pytest.mark.skipif(
    any(item is None for item in (EMAIL, PWD, APP_ID, SECRET)),
    reason="QOBUZ env vars not provided",
)


@pytest.fixture(scope="module")
def client():
    client = qobuz_client.Client(APP_ID, SECRET)
    client.login(EMAIL, PWD)  # type: ignore
    yield client


@_skip
def test_browse_custom_sub_items(client, config):
    result = browse._browse_custom_sub_items(
        uri="qobuz:custom:Test list:2010s Hip Hop", client=client, config=config
    )
    assert (
        browse.models.Ref.album(
            name="Kanye West - Yeezus", uri="qobuz:album:0060253743926"
        )
        in result
    )
