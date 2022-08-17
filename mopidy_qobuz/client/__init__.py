# License: GPL
# Author : Vitiko <vhnz98@gmail.com>
# -*- coding: utf-8 -*-

import hashlib
import json
import logging
import time

import requests


class QobuzException(Exception):
    pass


class TrackUrlNotFoundError(QobuzException):
    pass


class AuthenticationError(QobuzException):
    pass


class IneligibleError(QobuzException):
    pass


class InvalidAppIdError(QobuzException):
    pass


class InvalidAppSecretError(QobuzException):
    pass


class BadRequestError(QobuzException):
    pass


class NotFoundError(QobuzException):
    pass


class InvalidQuality(QobuzException):
    pass


logger = logging.getLogger(__name__)

BASE_URL = "https://www.qobuz.com/api.json/0.2"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36."


class Client:
    def __init__(self, app_id=None, secret=None, user_agent=None, session=None):
        self.secret = str(secret)
        self.app_id = str(app_id)
        self._session = session or requests.Session()
        self._session.headers.update(
            {"User-Agent": user_agent or USER_AGENT, "X-App-Id": self.app_id}
        )
        self._label = None
        self._logged_in = False

    def login(self, email: str, password: str, force=False):
        if not self._logged_in or force:
            self._auth(email, password)
        else:
            logger.info("Already logged in")

    def _auth(self, email, pwd):
        params = {
            "email": email,
            "password": pwd,
            "app_id": self.app_id,
        }
        response = self._session.get(f"{BASE_URL}/user/login", params=params)

        if response.status_code == 401:
            raise AuthenticationError(_get_message(response))

        if response.status_code == 400:
            raise InvalidAppIdError(_get_message(response))

        response = response.json()

        try:
            subscription = response["user"]["credential"]["parameters"]
        except (KeyError, TypeError):
            subscription = None

        if subscription:
            self._label = response["user"]["credential"]["parameters"]["short_label"]

        self._uat = response["user_auth_token"]
        self._session.headers.update({"X-User-Auth-Token": self._uat})

        logger.info("Logged: OK // Qobuz membership: %s", self._label)

    def get(self, endpoint: str, params: dict, raise_for_status=True):
        logger.debug("Making a call: %s - %s", endpoint, params)
        response = self._session.get(f"{BASE_URL}/{endpoint}", params=params)
        return _handle_response(response, raise_for_status)

    def post(self, endpoint: str, data: dict, raise_for_status=True):
        logger.debug("Making a call: %s - %s", endpoint, data)
        response = self._session.post(f"{BASE_URL}/{endpoint}", data=data)
        return _handle_response(response, raise_for_status)

    @property
    def membership(self):
        return self._label

    def raise_for_secret(self):
        DownloadableTrack.from_id(self, "5966783", 5)


_exception_codes = {400: BadRequestError, 401: AuthenticationError, 404: NotFoundError}


def _handle_response(response, raise_for_status):
    if response.status_code == 200 or not raise_for_status:
        return response

    try:
        raise _exception_codes[response.status_code](_get_message(response))
    except KeyError:
        # Ok?
        raise BadRequestError(f"Not implemented status code: {response.json()}")


def _get_message(response):
    try:
        return response.json()["message"] or "No message"
    except (KeyError, json.JSONDecodeError):
        return "No message"


class DownloadableTrack:
    def __init__(self, client: Client, data: dict):
        self._data = data
        self.id = data["track_id"]
        self.url = data.get("url")
        self.duration = data.get("duration")
        self.bit_depth = data.get("bit_depth", 16)
        self.sampling_rate = data.get("sampling_rate", 44.1)
        self.restrictions = data.get("restrictions", [])
        self._client = client
        self._size = None

    @classmethod
    def from_id(cls, client: Client, id, format_id=6, intent="stream"):
        """
        raises InvalidQuality, TrackUrlNotFoundError, InvalidAppSecretError
        """
        unix = time.time()

        try:
            valid = int(format_id) in (5, 6, 7, 27)
        except ValueError:
            valid = False

        if not valid:
            raise InvalidQuality("Invalid quality id: choose between 5, 6, 7 or 27")

        r_sig = f"trackgetFileUrlformat_id{format_id}intentstreamtrack_id{id}{unix}{client.secret}"
        r_sig_hashed = hashlib.md5(r_sig.encode("utf-8")).hexdigest()
        params = {
            "request_ts": unix,
            "request_sig": r_sig_hashed,
            "track_id": id,
            "format_id": format_id,
            "intent": intent,
        }

        response = client.get("track/getFileUrl", params, raise_for_status=False)
        response_dict = response.json()

        if response.status_code == 400 and "Invalid Request" in response_dict.get(
            "message", ""
        ):
            raise InvalidAppSecretError(f"Invalid app secret: {client.secret}")

        if response.status_code != 200 or not response_dict.get("url"):
            raise TrackUrlNotFoundError(response_dict)

        return cls(client, response_dict)

    @property
    def was_fallback(self):
        try:
            return any(
                restriction["code"] == "FormatRestrictedByFormatAvailability"
                for restriction in self.restrictions
            )
        except (KeyError, IndexError):
            return False

    @property
    def demo(self):
        return "sample" in self._data or not self._data.get("sampling_rate")

    @property
    def size(self):
        if self.url is None:
            return 0

        if self._size is None:
            response = self._client._session.head(self.url, allow_redirects=True)
            self._size = response.headers.get("Content-Length", 0)

        return self._size

    @property
    def extension(self):
        if "flac" in self._data.get("mime_type", "n/a"):
            return "FLAC"

        return "MP3"

    def __repr__(self):
        return f"<DownloadableTrack {self.id}@{self.extension} [{self.bit_depth}/{self.sampling_rate}]>"


class _WithMetadata:
    _endpoint = "album/get"
    _param = "album_id"

    def __init__(self, client: Client, data: dict):
        try:
            self.id = data["id"]
        except KeyError:
            raise ValueError("Can't construct without ID")

        self._client = client
        self._metadata = data.get("metadata")

    def _get_metadata(self):
        logger.debug("Getting metadata for ID: %s", id)
        if self._metadata is None:
            self._metadata = self._client.get(
                self._endpoint, params={self._param: self.id}
            ).json()
            return self._metadata

        logger.debug("Metadata already loaded")
        return self._metadata

    @classmethod
    def from_id(cls, client, id):
        response = client.get(cls._endpoint, params={cls._param: id}).json()
        return cls(client, response)


# This class should be removed
class _BigWithMetadata(_WithMetadata):
    _endpoint = "artist/get"
    _param = "artist_id"
    _key = "albums_count"
    _extra = "albums"

    def __init__(self, client: Client, data):
        super().__init__(client, data)
        self._metadata = None

    def _get_metadata(self):
        return self._multi_meta(self._key, self._extra)

    def _multi_meta(self, key, extra):
        total = 1
        offset = 0
        while total > 0:
            j = self._client.get(
                self._endpoint,
                {
                    self._param: self.id,
                    "offset": offset,
                    # "type": None,
                    "extra": extra,
                },
            ).json()

            if offset == 0:
                yield j
                try:
                    total = j[key] - 500
                except (KeyError, IndexError) as error:
                    logger.debug(
                        "%s raised trying to fetch metadata: %s", type(error), error
                    )
                    break
            else:
                yield j
                total -= 500

            offset += 500


class Track(_WithMetadata):
    _endpoint = "track/get"
    _param = "track_id"

    def __init__(self, client: Client, data: dict, album=None, artist=None):
        super().__init__(client, data)

        # Ignored keys (for now): release_date_download, release_date_stream,
        # purchasable, purchasable_at previewable, sampleable, articles, performers

        self.title = data.get("title")
        self.copyright = data.get("copyright")
        self.work = data.get("work")
        self.audio_info = data.get("audio_info")
        self.duration = data.get("duration", 0)
        self.release_date_original = data.get("release_date_original")
        self.purchasable = data.get("purchasable", False)
        self.work = data.get("work")
        self.version = data.get("version")
        self.media_number = data.get("media_number", 1)
        self.track_number = data.get("track_number", 1)
        self.parental_warning = data.get("parental_warning", False)
        self.maximum_sampling_rate = data.get("maximum_sampling_rate")
        self.maximum_channel_count = data.get("maximum_channel_count")
        self.streamable = data.get("streamable", False)
        self.hires_streamable = data.get("hires_streamable", False)

        self.album = album or Album(client, data.get("album", {}))

        performer = data.get("performer")
        if artist is not None:
            self.artist = artist
        elif performer is not None:
            self.artist = Artist(client, performer)
        else:
            self.artist = self.album.artist

        self.composer = data.get("composer")
        if self.composer is not None:
            self.composer = Artist(client, self.composer)

    @property
    def uri(self):
        return f"qobuz:track:{self.id}"

    @classmethod
    def from_search(cls, client, query, limit=10):
        tracks = client.get("track/search", {"query": query, "limit": limit}).json()
        try:
            return [cls(client, item) for item in tracks["tracks"]["items"]]
        except (IndexError, KeyError):
            return []

    def get_downloadable(self, format_id=6, intent="stream"):
        """
        :param format_id:
        :param intent:
        raises InvalidQuality, TrackUrlNotFoundError
        """
        return DownloadableTrack.from_id(self._client, self.id, format_id, intent)

    def __hash__(self):
        return hash(self.uri)

    def __repr__(self):
        return f"<Track {self.id}: {self.track_number}. {self.title}>"


class _WithImageMixin:
    _image: dict

    def image(self, key="large"):
        """
        :param key: small, thumbnail, or large
        """
        try:
            return self._image[key]
        except (TypeError, KeyError):
            return None


class Album(_WithMetadata, _WithImageMixin):
    def __init__(self, client: Client, data: dict):
        super().__init__(client, data)

        self.title = data.get("title", "Unknown")
        self.released_at = data.get("released_at")
        self._image = data.get("image", {})
        self.media_count = data.get("media_count")
        self.version = data.get("version")
        self.upc = data.get("upc")
        self.duration = data.get("duration")
        self.tracks_count = data.get("tracks_count", 1)
        self.release_date_original = data.get("release_date_original")
        self.release_type = data.get("release_type")
        self.parental_warning = data.get("parental_warning", False)
        self.hires_streamable = data.get("hires_streamable", False)
        self.streamable = data.get("streamable", self.hires_streamable)
        self.artist = Artist(client, data.get("artist"))

        self._tracks = data.get("tracks", {}).get("items")
        if self._tracks is not None:
            self._tracks = [
                Track(self._client, track, album=self) for track in self._tracks
            ]

        self.label = data.get("label")
        if self.label is not None:
            self.label = Label(client, self.label)

    @property
    def tracks(self):
        if self._tracks is None:
            self._tracks = [
                Track(self._client, track, album=self)
                for track in self._get_metadata()["tracks"]["items"]
            ]

        return self._tracks

    @property
    def uri(self):
        return f"qobuz:album:{self.id}"

    @classmethod
    def from_search(cls, client, query, limit=10):
        albums = client.get(
            "album/search", {"query": query, "limit": limit, "extra": "release_type"}
        ).json()
        try:
            return [cls(client, item) for item in albums["albums"]["items"]]
        except (IndexError, KeyError):
            return []

    def __hash__(self):
        return hash(self.uri)

    def __repr__(self):
        return f"<Album {self.id}: {self.title} ({self.release_date_original})>"


class Artist(_BigWithMetadata, _WithImageMixin):
    def __init__(self, client: Client, data, albums=None, tracks=None):
        super().__init__(client, data)

        self.name = data.get("name", "Unknown")
        self.albums_as_primary_artist_count = data.get("albums_as_primary_artist_count")
        self.albums_as_primary_composer_count = data.get(
            "albums_as_primary_composer_count"
        )
        self.picture = data.get("picture")
        self.albums_count = data.get("albums_count")
        self.slug = data.get("slug")
        self._image = data.get("image")
        self.picture = data.get("picture")
        self.similar_artist_ids = data.get("similar_artist_ids")
        self.information = data.get("information")
        self.biography = data.get("biography")
        self._albums = albums
        self._tracks = tracks

    @property
    def albums(self):
        if self._albums is None:
            self._albums = []
            for iterable in self._get_metadata():
                try:
                    self._albums.extend(
                        Album(self._client, data)
                        for data in iterable["albums"]["items"]
                    )
                except KeyError as error:
                    logger.debug("Unexpected KeyError fetching data: %s", error)

        return self._albums

    @property
    def tracks(self):
        if self._tracks is None:
            self._tracks = []
            # TODO: Sort by popularity
            for iterable in self._multi_meta("tracks_count", "tracks_appears_on"):
                try:
                    self._tracks.extend(
                        Track(self._client, data)
                        for data in iterable["tracks_appears_on"]["items"]
                    )
                except KeyError as error:
                    logger.debug("Unexpected KeyError fetching data: %s", error)

        return self._tracks

    @property
    def uri(self):
        return f"qobuz:artist:{self.id}"

    @classmethod
    def from_search(cls, client, query, limit=10):
        artists = client.get("artist/search", {"query": query, "limit": limit}).json()
        try:
            return [cls(client, item) for item in artists["artists"]["items"]]
        except (IndexError, KeyError):
            return []

    def __hash__(self):
        return hash(self.uri)

    def __repr__(self):
        return f"<Artist {self.id}: {self.name}>"


class Playlist(_BigWithMetadata):
    _endpoint = "playlist/get"
    _param = "playlist_id"
    _key = "tracks_count"
    _extra = "tracks"

    def __init__(self, client, data: dict):
        super().__init__(client, data)

        self.id = data.get("id")
        self.name = data.get("name", "Unknown")
        self.tracks_count = data.get("tracks_count")
        self.duration = data.get("duration")
        self._tracks = None
        self._deleted = False

    @classmethod
    def create(
        cls, client, name, description=None, is_public=True, is_collaborative=False
    ):
        data = {
            "name": name,
            "description": description or "",
            "is_public": "true" if is_public else "false",
            "is_collaborative": "false" if not is_collaborative else "true",
        }
        response = client.post("playlist/create", data)
        # TODO: improve error handling
        response.raise_for_status()

        playlist_dict = response.json()
        if not playlist_dict.get("id"):
            raise IneligibleError

        return cls.from_id(client, playlist_dict["id"])

    def delete(self):
        response = self._client.post("playlist/delete", {"playlist_id": str(self.id)})
        self._deleted = True
        return response.json()

    @property
    def tracks(self):
        if self._tracks is None:
            self._tracks = []
            # TODO: Sort by popularity
            for iterable in self._multi_meta("tracks_count", "tracks"):
                try:
                    self._tracks.extend(
                        Track(self._client, data)
                        for data in iterable["tracks"]["items"]
                    )
                except KeyError as error:
                    logger.debug("Unexpected KeyError fetching data: %s", error)

        return self._tracks

    def subscribe(self):
        response = self._client.post(
            "playlist/subscribe", {"playlist_id": str(self.id)}
        )
        return response.json()

    def delete_tracks(self, tracks):
        data = {
            "playlist_id": str(self.id),
            "playlist_track_ids": ",".join([str(item.id) for item in tracks]),
        }
        response = self._client.post("playlist/addTracks", data)
        return response.json()

    def add_tracks(self, tracks, no_duplicate=True):
        data = {
            "playlist_id": str(self.id),
            "track_ids": ",".join([str(item.id) for item in tracks]),
            "no_duplicate": "true" if no_duplicate else "false",
        }
        response = self._client.post("playlist/addTracks", data)
        return response.json()

    def refresh(self):
        self._tracks = None

    @property
    def uri(self):
        return f"qobuz:playlist:{self.id}"

    def __hash__(self):
        return hash(self.uri)

    def __repr__(self):
        return f"<Playlist {self.id}: {self.name} ({self.tracks_count} tracks)>"


class Label(_BigWithMetadata):
    _endpoint = "label/get"
    _param = "label_id"
    _key = "albums_count"
    _extra = "albums"

    def __init__(self, client, data: dict):
        super().__init__(client, data)

        self.id = data.get("id")
        self.name = data.get("name", "Unknown")

    def __repr__(self):
        return f"<Label {self.id}: {self.name}>"


class User:
    def __init__(self, client: Client):
        self._client = client

    def get_playlists(self, limit=10):
        response = self._client.get(
            "playlist/getUserPlaylists", {"limit": limit}
        ).json()
        try:
            return [
                Playlist(self._client, data) for data in response["playlists"]["items"]
            ]
        except (KeyError, TypeError):
            return []

    def get_favorites(self, type="albums", offset=0, limit=10):
        # TODO: serialize more types
        response = self._client.get(
            "favorite/getUserFavorites",
            {"type": type, "offset": offset, "limit": limit},
        ).json()

        try:
            return [Album(self._client, data) for data in response["albums"]["items"]]
        except KeyError:
            return []

    def modify_favorites(self, method="create", albums=None, artists=None, tracks=None):
        data = {
            "artist_ids": _to_str_list(artists),
            "album_ids": _to_str_list(albums),
            "track_ids": _to_str_list(tracks),
        }
        response = self._client.post(f"favorite/{method}", data)
        return response.json()


def _to_str_list(items):
    if items is None:
        return ""

    return ",".join([item.id for item in items])


class Focus(_WithMetadata):
    _endpoint = "focus/get"
    _param = "focus_id"

    def __init__(self, client, data, id=None, name=None):
        try:
            super().__init__(client, {"id": id or data["id"]})
        except KeyError:
            raise ValueError("Can't construct without ID")

        self.name = name or data.get("title", "Unknown")
        self.title = self.name  # Consistency with API
        self._containers = None
        self._albums = None
        self._playlists = None

    @property
    def albums(self):
        if self._albums is None:
            self._albums = self._get_albums()

        return self._albums

    @property
    def playlists(self):
        if self._playlists is None:
            self._playlists = self._get_playlists()

        return self._playlists

    @classmethod
    def from_id(cls, client, id):
        logger.debug("Calling from ID: %s", id)
        response = client.get(cls._endpoint, params={cls._param: id}).json()
        return cls(client, response, id=id)

    def _get_albums(self):
        containers = self._get_containers()

        albums = []
        for key in containers.keys():
            if (
                "album" not in containers[key].get("type", "n/a").lower()
            ):  # avoid KeyError
                continue

            try:
                items = containers[key]["albums"]["items"]
            except KeyError:
                logger.debug("No albums found in %s container", containers[key])
                continue

            for data in items:
                # 'streamable' key is missing here. Can we blatantly assume
                # that is streamable?
                data.update({"streamable": True})
                albums.append(Album(self._client, data))

        return albums

    def _get_playlists(self):
        containers = self._get_containers()

        playlists = []
        for key in containers.keys():
            if (
                "playlist" not in containers[key].get("type", "n/a").lower()
            ):  # avoid KeyError
                continue

            try:
                playlists.append(Playlist(self._client, containers[key]["playlist"]))
            except KeyError:
                logger.debug("No playlists found in %s container", containers[key])
                continue

        return playlists

    def _get_containers(self):
        if self._containers is None:
            try:
                self._containers = self._get_metadata()["containers"]
            except KeyError:
                logger.debug("No containers found in %s", self)
                self._containers = {}

        return self._containers

    def __repr__(self):
        return f"<Focus {self.id}: {self.name}>"


class Featured:
    def __init__(self, client: Client):
        self._client = client

    def get_playlists(
        self, tags=None, genre_ids=None, limit=25, offset=0, type="editor-picks"
    ):
        response = self._client.get(
            "playlist/getFeatured",
            {
                "type": type,
                "tags": tags,
                "limit": limit,
                "offset": offset,
                "genre_ids": genre_ids,
            },
        ).json()

        try:
            return [
                Playlist(self._client, data) for data in response["playlists"]["items"]
            ]
        except TypeError:
            return []

    def get_albums(self, offset=0, limit=25, genre_ids=None, type="press-awards"):
        response = self._client.get(
            "album/getFeatured",
            {
                "type": type,
                "offset": offset,
                "limit": limit,
                "genre_ids": genre_ids,
            },
        ).json()

        try:
            return [Album(self._client, data) for data in response["albums"]["items"]]
        except TypeError:
            return []

    def get_focus(self, offset=0, limit=30, genre_ids=None, type=None):
        response = self._client.get(
            "focus/list",
            {
                "type": type,
                "offset": offset,
                "limit": limit,
                "genre_ids": genre_ids,
            },
        ).json()
        try:
            return [Focus(self._client, data) for data in response["focus"]["items"]]
        except TypeError:
            return []
