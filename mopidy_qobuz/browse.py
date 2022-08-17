# -*- coding: utf-8 -*-

import logging

from mopidy import models

from mopidy_qobuz import translators
from mopidy_qobuz.client import Album
from mopidy_qobuz.client import Featured
from mopidy_qobuz.client import Focus
from mopidy_qobuz.client import Playlist
from mopidy_qobuz.client import User

logger = logging.getLogger(__name__)

ROOT_DIR = models.Ref.directory(uri="qobuz:directory", name="Qobuz")

GENRE_IDS = {
    -1: "All",
    112: "Rock",
    80: "Jazz",
    10: "Classical",
    64: "Electronic/Dance",
    127: "Soul/Funk/R&B",
    5: "Folk/Americana",
    133: "Hip-Hop/Rap",
    4: "Country",
    116: "Metal",
    3: "Blues",
    149: "Latin",
    91: "Soundtracks",
    94: "World",
    59: "Comedy/Other",
}
TAGS = (
    "all",
    "hi-res",
    "new",
    "focus",
    "danslecasque",
    "label",
    "mood",
    "artist",
    "event",
    "partner",
)
FEATURED_ALBUM_TYPES = {
    "new-releases-full": "New Releases",
    "recent-releases": "Still Trending",
    "press-awards": "Press Awards",
    "most-streamed": "Top Releases",
}

_FAVORITES = models.Ref.directory(uri="qobuz:favorites", name="Favorites")
_FAVORITE_ALBUMS = models.Ref.directory(uri="qobuz:favorites:albums", name="Albums")
_FAVORITE_PLAYLISTS = models.Ref.directory(
    uri="qobuz:favorites:playlists", name="Playlists"
)


_FEATURED = models.Ref.directory(uri="qobuz:featured", name="Featured (Recommended)")
_FEATURED_PLAYLISTS = models.Ref.directory(
    uri="qobuz:featured:playlists", name="Playlists"
)
_FEATURED_PLAYLISTS_GENRES = models.Ref.directory(
    uri="qobuz:featured:playlists:genres", name="By Genre"
)
_FEATURED_PLAYLISTS_TAGS = models.Ref.directory(
    uri="qobuz:featured:playlists:tags", name="By Tags"
)
_FEATURED_ALBUMS = models.Ref.directory(uri="qobuz:featured:albums", name="Albums")
_FEATURED_FOCUS = models.Ref.directory(uri="qobuz:featured:focus", name="Focus")


def browse(uri, client, config={}):
    try:
        return _STATIC[uri]
    except KeyError:
        pass

    for key, val in _CALLABLES.items():
        if not uri.startswith(key):
            continue

        return val(uri=uri, client=client)

    logger.info("Can't process uri format: %s", uri)


def _featured_album_tags():
    return [
        models.Ref.directory(uri=f"qobuz:featured:albums:tags:{key}", name=val)
        for key, val in FEATURED_ALBUM_TYPES.items()
    ]


def _genre_contents(uri="qobuz:featured:albums"):
    return [
        models.Ref.directory(uri=f"{uri}:genres:{key}", name=val)
        for key, val in GENRE_IDS.items()
    ]


def _tag_contents(uri="qobuz:featured:playlists"):
    return [
        models.Ref.directory(uri=f"{uri}:tags:{name}", name=name.title())
        for name in TAGS
    ]


def _favorite_contents(*, uri, client):
    user = User(client)
    to_return = []

    if uri.startswith("qobuz:favorites:albums"):
        to_return = [
            translators.to_album_ref(album) for album in user.get_favorites(limit=50)
        ]
    elif uri.startswith("qobuz:favorites:playlists"):
        to_return = [
            translators.to_playlist_ref(playlist)
            for playlist in user.get_playlists(limit=50)
        ]

    return _filter_none(to_return)


def _browse_playlist(*, uri: str, client):
    playlist_id = uri.split(":")[-1]
    playlist = Playlist.from_id(client, playlist_id)
    tracks = [translators.to_track_ref(track, False) for track in playlist.tracks]
    return _filter_none(tracks)


def _browse_album(*, uri: str, client):
    album_id = uri.split(":")[-1]
    album = Album.from_id(client, album_id)
    tracks = [translators.to_track_ref(track, False) for track in album.tracks]
    return _filter_none(tracks)


def _browse_focus(*, uri: str, client):
    focus_id = uri.split(":")[-1]
    focus = Focus.from_id(client, focus_id)

    contents = [translators.to_album_ref(album) for album in focus.albums]
    contents.extend(
        [translators.to_playlist_ref(playlist) for playlist in focus.playlists]
    )

    return _filter_none(contents)


def _browse_featured_playlist_genres(*, uri: str, client):
    genre = uri.split(":")[-1]
    featured = Featured(client)
    playlists = featured.get_playlists(genre_ids=None if genre == "-1" else genre)
    return [translators.to_playlist_ref(playlist) for playlist in playlists]


def _browse_featured_playlist_tags(*, uri: str, client):
    tag = uri.split(":")[-1]
    featured = Featured(client)
    playlists = featured.get_playlists(tags=None if tag == "all" else tag)
    return [translators.to_playlist_ref(playlist) for playlist in playlists]


def _browse_featured_album_tags(*, uri: str, client):
    if "genres" not in uri:
        return _genre_contents(uri)

    # qobuz:featured:albums:tags:xxx:genres:xxx
    genre = uri.split(":")[-1]
    tag = uri.split(":")[-3]

    featured = Featured(client)
    albums = featured.get_albums(genre_ids=None if genre == "-1" else genre, type=tag)

    return [translators.to_album_ref(album) for album in albums]


def _focus_to_directory(focus: Focus):
    return models.Ref.directory(uri=f"qobuz:focus:{focus.id}", name=focus.name)


def _browse_featured_focus_genres(*, uri: str, client):
    genre = uri.split(":")[-1]
    featured = Featured(client)
    items = featured.get_focus(genre_ids=None if genre == "-1" else genre)
    return [_focus_to_directory(item) for item in items]


def _filter_none(items):
    return [item for item in items if item is not None]


_STATIC = {
    "qobuz:directory": [_FAVORITES, _FEATURED],
    "qobuz:favorites": [_FAVORITE_ALBUMS, _FAVORITE_PLAYLISTS],
    "qobuz:featured": [_FEATURED_ALBUMS, _FEATURED_PLAYLISTS, _FEATURED_FOCUS],
    "qobuz:featured:albums": _featured_album_tags(),
    "qobuz:featured:focus": _genre_contents("qobuz:featured:focus"),
    "qobuz:featured:playlists": [_FEATURED_PLAYLISTS_TAGS, _FEATURED_PLAYLISTS_GENRES],
    "qobuz:featured:playlists:genres": _genre_contents("qobuz:featured:playlists"),
    "qobuz:featured:playlists:tags": _tag_contents("qobuz:featured:playlists"),
}

_CALLABLES = {
    "qobuz:favorites:albums": _favorite_contents,  # list of albums or playlists
    "qobuz:favorites:playlists": _favorite_contents,  # list of albums or playlists
    "qobuz:featured:playlists:genres:": _browse_featured_playlist_genres,
    "qobuz:featured:playlists:tags:": _browse_featured_playlist_tags,
    "qobuz:featured:albums:tags:": _browse_featured_album_tags,
    "qobuz:featured:focus:genres:": _browse_featured_focus_genres,
    "qobuz:playlist:": _browse_playlist,
    "qobuz:album:": _browse_album,
    "qobuz:focus:": _browse_focus,
}
