# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import logging
import os
import pathlib
import sys

from mopidy import config
from mopidy import ext

__version__ = "0.1.0"


logger = logging.getLogger(__name__)

file_dir = os.path.dirname(__file__)
sys.path.append(file_dir)


class Extension(ext.Extension):
    dist_name = "Mopidy-Qobuz"
    ext_name = "qobuz"
    version = __version__

    def get_default_config(self):
        return config.read(pathlib.Path(__file__).parent / "ext.conf")

    def get_config_schema(self):
        schema = super().get_config_schema()

        schema["username"] = config.String()
        schema["password"] = config.Secret()
        schema["app_id"] = config.String()
        schema["secret"] = config.Secret()
        schema["quality"] = config.Integer(choices=[5, 6, 7, 27])
        schema["search_artist_count"] = config.Integer()
        schema["search_track_count"] = config.Integer()
        schema["search_album_count"] = config.Integer()

        return schema

    def setup(self, registry):
        from .backend import QobuzBackend

        registry.add("backend", QobuzBackend)
