import logging
import requests
from enum import Enum

# url constants
AUTHENTICATE_BY_NAME_URL = "/Users/AuthenticateByName"
SEARCH_HINTS_URL = "/Search/Hints"
ARTISTS_URL = "/Artists"
PLAYLIST_URL = "/Playlists"
ARTIST_INSTANT_MIX_URL = ARTISTS_URL + "/InstantMix"
SONG_FILE_URL = "/Audio"
DOWNLOAD_URL = "/Download"
ITEMS_ARTIST_KEY = "ArtistIds"
ITEMS_PARENT_ID_KEY = "ParentId"
ITEMS_URL = "/Items"
ITEMS_ALBUMS_URL = ITEMS_URL + "?SortBy=SortName&SortOrder=Ascending&IncludeItemTypes=MusicAlbum&Recursive=true&" + ITEMS_ARTIST_KEY + "="
ITEMS_SONGS_BY_ARTIST_URL = ITEMS_URL + "?SortBy=SortName&SortOrder=Ascending&IncludeItemTypes=Audio&Recursive=true&" + ITEMS_ARTIST_KEY + "="
ITEMS_SONGS_BY_ALBUM_URL = ITEMS_URL + "?SortBy=IndexNumber&" + ITEMS_PARENT_ID_KEY + "="
LIMIT = "&Limit="
SERVER_INFO_URL = "/System/Info"
SERVER_INFO_PUBLIC_URL = SERVER_INFO_URL + "/Public"
# auth constants
AUTH_USERNAME_KEY = "Username"
AUTH_PASSWORD_KEY = "Pw"
MAX_STREAM_BITRATE = "MaxStreamingBitrate=140000000&"
AUDIO_CODEC = "AudioCodec=mp3&"
TRANSCODING_SETTING = "TranscodingContainer=ts&TranscodingProtocol=hls"
CONTAINER = "Container=opus%2Cmp3%7Cmp3%2Caac%2Cm4a%2Cm4b%7Caac%2Cflac%2Cwebma%2Cwebm%2Cwav%2Cogg&"
JELLY_ARGS = CONTAINER + TRANSCODING_SETTING + MAX_STREAM_BITRATE + AUDIO_CODEC



# query param constants
AUDIO_STREAM = "universal"
API_KEY = "api_key="


class PublicJellyfinClient(object):
    """
    Handles the publically exposed jellyfin endpoints

    """

    def __init__(self, host, device="noDevice", client="NoClient", client_id="1234", version="0.1"):
        """
        Sets up the connection to the Jellyfin server
        :param host:
        """
        self.log = logging.getLogger(__name__)
        self.host = host
        self.auth = None
        self.device = device
        self.client = client
        self.client_id = client_id
        self.version = version

    def get_server_info_public(self):
        return requests.get(self.host + SERVER_INFO_PUBLIC_URL)


class JellyfinClient(PublicJellyfinClient):
    """
    Handles communication to the Jellyfin server

    """

    def __init__(self, host, username, password, api_key, device="noDevice", client="NoClient", client_id="1234", version="0.1"):
        """
        Sets up the connection to the Jellyfin server
        :param host:
        :param username:
        :param password:
        """

        super().__init__(host, device, client, client_id, version)
        self.log = logging.getLogger(__name__)
        self.auth = self._auth_by_user(username, password)
        self.api_key = api_key

    def _auth_by_user(self, username, password):
        """
        Authenticates to jellyfin via username and password

        :param username:
        :param password:
        :return:
        """
        auth_payload = \
            {AUTH_USERNAME_KEY: username, AUTH_PASSWORD_KEY: password}
        response = self._post(AUTHENTICATE_BY_NAME_URL, auth_payload)
        assert response.status_code is 200
        return JellyfinAuthorization.from_response(response)

    def get_headers(self):
        """
        Returns specific Jellyfin headers including auth token if available

        :return:
        """
        media_browser_header = "MediaBrowser Client="+self.client +\
                               ", Device="+self.device +\
                               ", DeviceId="+self.client_id +\
                               ", Version="+self.version
        if self.auth and self.auth.user_id:
            media_browser_header = \
                media_browser_header + ", UserId=" + self.auth.user_id
        headers = {"X-Emby-Authorization": media_browser_header}
        if self.auth and self.auth.token:
            headers["X-Emby-Token"] = self.auth.token
        return headers

    def search(self, query, media_types=[]):

        query_params = '?searchTerm={0}'.format(query)

        types = None
        for type in media_types:
            types = type + ","

        if types:
            types = types[:len(types) - 1]
            query_params = query_params + '&IncludeItemTypes={0}'.format(types)

        return self._get(SEARCH_HINTS_URL + query_params)
        #return self._get(SEARCH_HINTS_URL + query_params)

    def instant_mix(self, item_id):
        # userId query param is required even though its not
        # required in swagger
        # https://emby.media/community/index.php?/
        # topic/50760-instant-mix-api-value-cannot-be-null-error/
        instant_item_mix = '/Items/{0}/InstantMix?userId={1}&Limit=200'\
            .format(item_id, self.auth.user_id)
        return self._get(instant_item_mix)

    def get_song_file(self, song_id):
        url = '{0}{1}/{2}/{3}?userId={4}&{5}{6}&{7}DeviceId=none'\
            .format(self.host, SONG_FILE_URL,
                    song_id, AUDIO_STREAM, self.auth.user_id, API_KEY, self.api_key, JELLY_ARGS)
        return url

    def get_albums_by_artist(self, artist_id):
        url = "/Users/" + self.auth.user_id + ITEMS_ALBUMS_URL + str(artist_id)
        return self._get(url)

    def get_songs_by_album(self, album_id):
        url = "/Users/" + self.auth.user_id + ITEMS_SONGS_BY_ALBUM_URL + str(album_id)
        return self._get(url)

    def get_songs_by_artist(self, artist_id, limit=None):
        url = "/Users/" + self.auth.user_id + ITEMS_SONGS_BY_ARTIST_URL + str(artist_id)
        if limit:
            url = url + LIMIT+str(limit)
        return self._get(url)

    def get_songs_by_playlist(self, playlist_id):
        url = PLAYLIST_URL + "/" + str(playlist_id) + ITEMS_URL
        return self._get(url)

    def get_all_artists(self):
        return self._get(ARTISTS_URL)

    def get_server_info(self):
        return self._get(SERVER_INFO_URL)

    def _post(self, url, payload):
        """
        Post with host and headers provided

        :param url:
        :param payload:
        :return:
        """
        return requests.post(
            self.host + url, json=payload, headers=self.get_headers())

    def _get(self, url):
        """
        Get with host and headers provided

        :param url:
        :return:
        """
        return requests.get(self.host + url, headers=self.get_headers())


class JellyfinAuthorization(object):

    def __init__(self, user_id, token):
        self.user_id = user_id
        self.token = token

    @classmethod
    def from_response(cls, response):
        """
        Helper method for converting a response into
        an Jellyfin Authorization

        :param response:
        :return:
        """
        auth_content = response.json()
        return JellyfinAuthorization(
            auth_content["User"]["Id"], auth_content["AccessToken"])


class JellyfinMediaItem(object):

    """
    Stripped down representation of a media item in Jellyfin

    """

    def __init__(self, id, name, type):
        self.id = id
        self.name = name
        self.type = type

    @classmethod
    def from_item(cls, item):
        media_item_type = MediaItemType.from_string(item["Type"])
        return JellyfinMediaItem(item["Id"], item["Name"], media_item_type)

    @staticmethod
    def from_list(items):
        media_items = []
        for item in items:
            media_items.append(JellyfinMediaItem.from_item(item))

        return media_items


class MediaItemType(Enum):
    ARTIST = "MusicArtist"
    ALBUM = "MusicAlbum"
    SONG = "Audio"
    OTHER = "Other"
    PLAYLIST = "Playlist"

    @staticmethod
    def from_string(enum_string):
        for item_type in MediaItemType:
            if item_type.value == enum_string:
                return item_type
        return MediaItemType.OTHER
