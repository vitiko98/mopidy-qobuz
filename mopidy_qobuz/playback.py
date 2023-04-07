# -*- coding: utf-8 -*-

import logging

from mopidy import backend

from mopidy_qobuz.client import DownloadableTrack

logger = logging.getLogger(__name__)


class QobuzPlaybackProvider(backend.PlaybackProvider):
    def __init__(self, audio, backend):
        super().__init__(audio, backend)
        self._format_id = self.backend._config["qobuz"]["quality"]
        self._tracks = {}

    def translate_uri(self, uri):
        if not uri:
            return None

        client = self.backend._client
        track_id = uri.split(":")[-1]

        logger.debug("Track ID: %s", track_id)

        if track_id in self._tracks:
            downloadable = self._tracks[track_id]
        else:
            try:
                downloadable = DownloadableTrack.from_id(
                    client, track_id, format_id=self._format_id
                )
            except Exception as error:
                logger.warning("%s raised getting URL for %s", error, uri)
                return None
            else:
                self._tracks[track_id] = downloadable

        if downloadable.demo:
            logger.info("%s is a demo. Can't play", uri)
            return None

        if downloadable.was_fallback:
            logger.info("%s does not met the configured quality: %s", uri, downloadable)

        logger.info("Valid track found: %s", downloadable)

        return downloadable.url
