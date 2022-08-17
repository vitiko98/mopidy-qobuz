from mopidy_qobuz import backend
from unittest import mock
import pytest


def test_backend(qobuz_config):
    assert backend.QobuzBackend(config=qobuz_config, audio=mock.Mock()) is not None
