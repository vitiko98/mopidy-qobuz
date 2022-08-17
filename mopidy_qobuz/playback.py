# -*- coding: utf-8 -*-

from functools import lru_cache
import logging

from mopidy import backend

from mopidy_qobuz.client import DownloadableTrack
from mopidy_qobuz.client import TrackUrlNotFoundError

logger = logging.getLogger(__name__)


class QobuzPlaybackProvider(backend.PlaybackProvider):
    def __init__(self, audio, backend):
        super().__init__(audio, backend)
        self._format_id = self.backend._config["qobuz"]["quality"]

    def translate_uri(self, uri):
        client = self.backend._client
        track_id = uri.split(":")[-1]
        logger.debug("Track ID: %s", track_id)

        try:
            downloadable = _get_downloadable_track(client, track_id, self._format_id)
        except TrackUrlNotFoundError as error:
            logger.warning("%s raised getting URL for %s", error, uri)
            return None

        if downloadable.demo:
            logger.info("%s is a demo. Can't play", uri)
            return None

        if downloadable.was_fallback:
            logger.info("%s does not met the configured quality: %s", uri, downloadable)

        logger.info("Valid track found: %s", downloadable)

        return downloadable.url

    def should_download(self, uri):
        return True


@lru_cache(maxsize=1024)
def _get_downloadable_track(client, track_id, format_id):
    return DownloadableTrack.from_id(client, track_id, format_id=format_id)
