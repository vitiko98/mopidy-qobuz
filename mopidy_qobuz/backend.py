# -*- coding: utf-8 -*-

import logging

from mopidy import backend
import pykka

from mopidy_qobuz import client as qclient
from mopidy_qobuz import library
from mopidy_qobuz import playback
from mopidy_qobuz import playlists

logger = logging.getLogger(__name__)


class QobuzBackend(pykka.ThreadingActor, backend.Backend):
    def __init__(self, config, audio):
        super().__init__()
        self._config = config
        self._audio = audio
        self._client = None
        self.playlists = playlists.QobuzPlaylistsProvider(self)
        self.library = library.QobuzLibraryProvider(self)
        self.playback = playback.QobuzPlaybackProvider(audio, self)
        self.uri_schemes = ["qobuz"]

    def ping(self):
        return True

    def on_start(self):
        logger.info("Starting Qobuz client")
        config = self._config["qobuz"]
        self._client = qclient.Client(config["app_id"], config["secret"])

        self._client.login(config["username"], config["password"])

        logger.info(
            "Set quality: %s [%s membership]",
            config["quality"],
            self._client.membership.upper(),
        )

    def on_stop(self):
        # TODO: implement logout
        pass
