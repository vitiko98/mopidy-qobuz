# -*- coding: utf-8 -*-

import logging

from mopidy import models

from mopidy_qobuz.client import Album
from mopidy_qobuz.client import Artist
from mopidy_qobuz.client import Track

logger = logging.getLogger(__name__)

_TRIVIAL_VERSIONS = ("album version", "lp version")

# TODO: improve multiple artists priority


def to_artist(artist: Artist):
    return models.Artist(uri=artist.uri, name=artist.name)


def to_artist_ref(artist):
    return models.Ref.artist(uri=artist.uri, name=artist.name)


def to_album(album: Album, hires_required=False):
    if not _is_item_available(album, hires_required):
        return None

    return models.Album(
        uri=album.uri,
        name=_complete_title(album),
        artists=[to_artist(album.artist)],
        num_tracks=album.tracks_count,
        date=album.release_date_original,
    )


def to_album_ref(album: Album, hires_required=False):
    if not _is_item_available(album, hires_required):
        return None

    title = _complete_ref_title(album)
    return models.Ref.album(
        uri=album.uri, name=_watermark_hires(album.hires_streamable, title)
    )


def _is_item_available(item, hires_required=False):
    if not item.streamable:
        logger.info("Not streamable: %s", item)
        return False

    if hires_required and not item.hires_streamable:
        logger.info("XD")
        return False

    return True


def to_track(track: Track, hires_required=False):
    if not _is_item_available(track, hires_required):
        return None

    artist = to_artist(track.artist)
    album = to_album(track.album)
    if album is None:
        return None

    return models.Track(
        uri=track.uri,
        name=_track_complete_title(track),
        artists=[artist],
        album=album,
        date=album.date,
        length=track.duration * 1000,
        disc_no=track.media_number,
        track_no=track.track_number,
    )


def to_track_ref(track: Track, hires_required):
    if not _is_item_available(track, hires_required):
        return None

    return models.Ref.track(uri=track.uri, name=_track_ref_title(track))


def to_playlist_ref(playlist):
    return models.Ref.playlist(uri=playlist.uri, name=playlist.name)


def to_playlist(playlist):
    tracks = [to_track(track) for track in playlist.tracks]
    # See to_track()
    tracks = [track for track in tracks if track is not None]
    return models.Playlist(uri=playlist.uri, name=playlist.name, tracks=tracks)


def _watermark_hires(is_hires_streamable, title):
    if is_hires_streamable:
        return f"{title} [Hi-res]"

    return title


# Probably we can add HI-Res watermarks later?
def _complete_ref_title(item):
    title = _complete_title(item)

    if item.artist:
        return f"{item.artist.name} - {title}"

    return title


def _track_ref_title(track):
    title = _track_complete_title(track)
    if track.artist:
        return f"{track.artist.name} - {title}"

    return title


# Remove unwanted version extra strings from translated title
def _track_complete_title(track):
    release_type = track.album.release_type
    if (
        release_type is not None
        and track.version is not None
        and release_type in track.version
    ):
        return track.title

    return _complete_title(track)


def _complete_title(item):
    if item.version is not None and item.version.lower() not in _TRIVIAL_VERSIONS:
        return (
            f"{item.title.strip()} ({item.version.strip()})"
            if item.version.lower() not in item.title.lower()
            else item.title
        )

    return item.title
