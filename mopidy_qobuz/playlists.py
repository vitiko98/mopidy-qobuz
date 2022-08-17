# -*- coding: utf-8 -*-
import logging

from mopidy import backend

from mopidy_qobuz.client import Playlist
from mopidy_qobuz.client import User
from mopidy_qobuz.translators import to_playlist
from mopidy_qobuz.translators import to_playlist_ref
from mopidy_qobuz.translators import to_track_ref

logger = logging.getLogger(__name__)


class QobuzPlaylistsProvider(backend.PlaylistsProvider):
    def __init__(self, backend):
        self._backend = backend

    def as_list(self):
        user = User(self._backend._client)
        return [to_playlist_ref(playlist) for playlist in user.get_playlists(limit=100)]

    def get_items(self, uri):
        playlist = self._get_playlist(uri)

        if playlist is not None:
            return [to_track_ref(track, False) for track in playlist.tracks]

        return playlist

    def lookup(self, uri):
        playlist = self._get_playlist(uri)

        if playlist is not None:
            return to_playlist(playlist)

        return playlist

    def refresh(self):
        # TODO
        pass

    def create(self):
        # Apparently possible with Qobuz API. TODO.
        pass

    def delete(self):
        # Apparently possible with Qobuz API. TODO.
        pass

    def save(self):
        # Apparently possible with Qobuz API. TODO.
        pass

    def _get_playlist(self, uri):
        if uri is None or not uri.startswith("qobuz:playlist"):
            return None

        return Playlist.from_id(self._backend._client, uri.split(":")[-1])
