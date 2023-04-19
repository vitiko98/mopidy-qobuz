****************************
Mopidy-Qobuz
****************************

`Mopidy <https://mopidy.com/>`_ extension for playing Hi-Res/Lossless music from Qobuz.

Requires a non-free account.

Features
============
* Up to 24b/196k playback
* Artist, album and track search
* Browse support
* Playlists support
* Featured lists support
* Image support

Installation
============

Install by running::

    pip install mopidy-qobuz-hires

or::

    pip install git+https://github.com/vitiko98/mopidy-qobuz


``pip install mopidy-qobuz`` **IS NOT RELATED to this repository/extension.**

**This extension conflicts with** https://github.com/taschenb/mopidy-qobuz (https://pypi.org/project/Mopidy-Qobuz).
You will need to uninstall it if it's in your system.

Configuration
=============

Before starting Mopidy, you must add ``username``, ``password``, ``app_id`` and ``secret`` fields
to the Mopidy configuration file::

    [qobuz]
    username = alice
    password = secret
    app_id = foo
    secret = bar
    quality = 6


See this `gist <https://gist.github.com/vitiko98/bb89fd203d08e285d06abf40d96db592>`_ to get
`app_id` and `secret` values yourself.

The following configuration values are available:

- ``qobuz/enabled``: If the Qobuz extension should be enabled or not.
  Defaults to ``true``.

- ``qobuz/username``: Qobuz username (or email). You *must* provide this.

- ``qobuz/password``: Qobuz password. You *must* provide this.

- ``qobuz/app_id``: Qobuz app id. You *must* provide this.

- ``qobuz/secret``: Qobuz secret key. You *must* provide this.

- ``qobuz/quality``: Quality code integer. 5 is 320 MP3; 6 is FLAC; 7 is FLAC 24
  ≤ 96; 27 is FLAC 24 > 96. Defaults to 6.

- ``qobuz/search_album_count``: Maximum number of albums returned in search
  results. Defaults to 10.

- ``qobuz/search_track_count``: Maximum number of tracks returned in search
  results. Defaults to 10.

- ``qobuz/search_artist_count``: Maximum number of artists returned in search
  results. Defaults to 0.

- ``qobuz/custom_libraries``: An optional directory containing custom YAML library files. 
  See ``tests/data/library.yml`` for more info.

Status
=================
This extension is in alpha development.


Project resources
=================

- `Source code <https://github.com/vitiko98/mopidy-qobuz>`_
- `Issue tracker <https://github.com/vitiko98/mopidy-qobuz/issues>`_
