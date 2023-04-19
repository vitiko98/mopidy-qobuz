# -*- coding: utf-8 -*-

import logging
import os
import re

from mopidy import models
import yaml

from mopidy_qobuz import translators
from mopidy_qobuz.client import Album
from mopidy_qobuz.client import Artist
from mopidy_qobuz.client import Featured
from mopidy_qobuz.client import Focus
from mopidy_qobuz.client import Playlist
from mopidy_qobuz.client import User
from mopidy_qobuz.client import Track

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
_CUSTOM_DIRS = models.Ref.directory(uri="qobuz:custom", name="Custom Libraries")
_FAVORITE_ALBUMS = models.Ref.directory(uri="qobuz:favorites:albums", name="Albums")
_FAVORITE_ARTISTS = models.Ref.directory(
    uri="qobuz:favorites:artists", name="Artists"
)  # Agregado
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


def _get_callable(uri):
    for key, val in _CALLABLES.items():
        if not isinstance(key, re.Pattern):
            if not uri.startswith(key):
                continue
        else:
            if not key.search(uri):
                continue

        logger.debug("Got callable (%s) for %s", val, uri)
        return val


def browse(uri, client, config={}):
    try:
        return _STATIC[uri]
    except KeyError:
        pass

    callable_ = _get_callable(uri)

    if callable_:
        return callable_(uri=uri, client=client, config=config)

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


def _favorite_contents(*, uri, client, config):
    user = User(client)
    to_return = []

    if uri.startswith("qobuz:favorites:albums"):
        to_return = [
            translators.to_album_ref(album) for album in user.get_favorites(limit=50)
        ]
    if uri.startswith("qobuz:favorites:artists"):
        to_return = [
            translators.to_artist_ref(artist)
            for artist in user.get_favorites_artists(limit=500)
        ]
    elif uri.startswith("qobuz:favorites:playlists"):
        to_return = [
            translators.to_playlist_ref(playlist)
            for playlist in user.get_playlists(limit=50)
        ]

    return _filter_none(to_return)


def _browse_playlist(*, uri: str, client, config):
    playlist_id = uri.split(":")[-1]
    playlist = Playlist.from_id(client, playlist_id)
    tracks = [translators.to_track_ref(track, False) for track in playlist.tracks]
    return _filter_none(tracks)


def _browse_album(*, uri: str, client, config):
    album_id = uri.split(":")[-1]
    album = Album.from_id(client, album_id)
    tracks = [translators.to_track_ref(track, False) for track in album.tracks]
    return _filter_none(tracks)


def _browse_artist(*, uri: str, client, config):
    artist_id = uri.split(":")[-1]
    artist = Artist.from_id(client, artist_id)
    albums = [translators.to_album_ref(album, False) for album in artist.albums]
    return _filter_none(albums)


def _browse_focus(*, uri: str, client, config):
    focus_id = uri.split(":")[-1]
    focus = Focus.from_id(client, focus_id)

    contents = [translators.to_album_ref(album) for album in focus.albums]
    contents.extend(
        [translators.to_playlist_ref(playlist) for playlist in focus.playlists]
    )

    return _filter_none(contents)


def _browse_featured_playlist_genres(*, uri: str, client, config):
    genre = uri.split(":")[-1]
    featured = Featured(client)
    playlists = featured.get_playlists(genre_ids=None if genre == "-1" else genre)
    return [translators.to_playlist_ref(playlist) for playlist in playlists]


def _browse_featured_playlist_tags(*, uri: str, client, config):
    tag = uri.split(":")[-1]
    featured = Featured(client)
    playlists = featured.get_playlists(tags=None if tag == "all" else tag)
    return [translators.to_playlist_ref(playlist) for playlist in playlists]


def _browse_featured_album_tags(*, uri: str, client, config):
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


def _browse_featured_focus_genres(*, uri: str, client, config):
    genre = uri.split(":")[-1]
    featured = Featured(client)
    items = featured.get_focus(genre_ids=None if genre == "-1" else genre)
    return [_focus_to_directory(item) for item in items]


def _browse_custom(*, uri: str, client, config: dict):
    yaml_items = _get_yaml_items(config)
    return [
        models.Ref.directory(uri=f"qobuz:custom:{k}", name=k) for k in yaml_items.keys()
    ]


def _browse_custom_sub(*, uri: str, client, config: dict):
    id_ = uri.split(":")[-1]
    items = _get_yaml_items(config)[id_]
    return [
        models.Ref.directory(uri=f"qobuz:custom:{id_}:{k}", name=k)
        for k in items.keys()
    ]


_uris_map = {
    "album": (translators.to_album_ref, Album.from_id),
    "track": (translators.to_track_ref, Track.from_id),
    "playlist": (translators.to_playlist_ref, Playlist.from_id),
}


def _browse_custom_sub_items(*, uri: str, client, config: dict):
    parent = uri.split(":")[-2]
    id_ = uri.split(":")[-1]
    refs_ = []
    items = _get_yaml_items(config)[parent][id_]

    for uri_ in items:
        type_, id_ = uri_.strip().split(":")[-2:]
        try:
            translator_, client_method = _uris_map[type_]
        except KeyError:
            logger.warning("%s URI not supported", uri_)
            continue

        try:
            refs_.append(translator_(client_method(client, id_)))
        except Exception as error:
            logger.warning(error)

    return refs_


def _get_yaml_items(config):
    folder_path = config.get("custom_libraries")
    if not folder_path:
        logger.warning("Not folder path set")
        return {}

    if not os.path.isdir(folder_path):
        logger.warning("custom_libraries (%s) doesn't exist", folder_path)
        return {}

    return _read_yaml_folder(folder_path)


def _read_yaml_folder(folder_path):
    yaml_items = {}
    for filename in os.listdir(folder_path):
        if filename.endswith((".yaml", ".yml")):
            file_path = os.path.join(folder_path, filename)
            with open(file_path, "r") as f:
                content = yaml.safe_load(f)
                if "title" not in content or "items" not in content:
                    logger.error("Title/Items not set in %s", file_path)
                    continue

                yaml_items[content["title"].replace(":", "")] = {
                    k.replace(":", ""): v for k, v in content["items"].items()
                }

    return yaml_items


def _filter_none(items):
    return [item for item in items if item is not None]


_STATIC = {
    "qobuz:directory": [_FAVORITES, _FEATURED, _CUSTOM_DIRS],
    "qobuz:favorites": [_FAVORITE_ALBUMS, _FAVORITE_ARTISTS, _FAVORITE_PLAYLISTS],
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
    "qobuz:favorites:artists": _favorite_contents,  # list of albums or playlists
    "qobuz:featured:playlists:genres:": _browse_featured_playlist_genres,
    "qobuz:featured:playlists:tags:": _browse_featured_playlist_tags,
    "qobuz:featured:albums:tags:": _browse_featured_album_tags,
    "qobuz:featured:focus:genres:": _browse_featured_focus_genres,
    "qobuz:playlist:": _browse_playlist,
    "qobuz:album:": _browse_album,
    "qobuz:focus:": _browse_focus,
    "qobuz:artist": _browse_artist,  # Agregado
    re.compile(r"^qobuz:custom$"): _browse_custom,
    re.compile(r"^qobuz:custom:.+:.+$"): _browse_custom_sub_items,
    re.compile(r"^qobuz:custom:.+$"): _browse_custom_sub,
}
