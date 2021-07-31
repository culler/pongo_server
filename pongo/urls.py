from django.urls import path, register_converter
from django.conf.urls import url
from django.conf import settings
from django.conf.urls.static import static
from django.views.decorators.cache import cache_page
from . import views

class SpotifyIdConverter:
    regex = '[0-9A-z]{22}'

    def to_python(self, value):
        return str(value)

    def to_url(self, value):
        return str(value)

class AjaxKeyConverter:
    regex = '[A-z]*'

    def to_python(self, value):
        return str(value)

    def to_url(self, value):
        return str(value)

register_converter(SpotifyIdConverter, 'spid')
register_converter(AjaxKeyConverter, 'key')

urlpatterns = [
    path('', views.index,
        name='index'),

    # AJAX state queries
    path('state/albums/<ajax_key:key/', views.albums_state,
        name='albums_state'),
    path('state/player/', views.spotify_player_state,
        name='player_state'),

    # Pasting
    path('paste/album/<spid:id>/', views.album_paste,
        name='album_paste'),
    path('paste/playlist/<spid:id>/', views.playlist_paste,
        name='playlist_paste'),
    path('paste/error/', views.paste_error, name='paste_error'),
    path('paste/', views.browser_paste, name='browser_paste'),

    # Albums
    path('album/<spid:id>/', views.album, name='album'),
    path('albums/', views.albums, name='albums'),

    # Playlists
    path('playlist/<spid:id>/', views.playlist, name='playlist'),
    path('playlists/', views.playlists, name='playlists'),

    # Suggest
    path('suggest/', views.suggest, name='suggest'),

    # Player
      # AJAX player control commands
    path('player/play/<spid:id>/', views.player_play_album,
        name='player_play_album/'),
    path('player/pause/', views.spotify_player_pause,
        name='player_pause'),
    path('player/play/', views.spotify_player_play,
        name='player_play'),
    path('player/forward/', views.spotify_player_forward,
        name='player_forward'),
    path('player/back/', views.spotify_player_back,
        name='player_back'),
    path('player/eject/', views.spotify_player_eject,
        name='player_eject'),
    path('player/jump/<int:n>/', views.spotify_player_jump,
        name='player_jump'),
    path('player/remove/<int:n>/', views.spotify_player_remove,
        name='player_remove/'),
    path('player/', views.player, name='player'),

    # Settings
    path('settings/name/', views.settings_name, name='settings_name'),
    path('settings/connect_new/', views.settings_connect_new,
        name='settings_connect_new'),
    path('settings/connect/', views.settings_connect,
        name='settings_connect'),
    path('settings/disconnect/', views.settings_disconnect,
        name='settings_disconnect'),
    path('settings/credentials/', views.settings_credentials,
        name='settings_credentials'),
    path('settings/eject/', views.settings_eject,
        name='settings_eject'),
    path('settings/restart/', views.settings_restart,
        name='settings_restart'),
    path('settings/shutdown/', views.settings_shutdown,
        name='settings_shutdown'),
    path('settings/', views.settings, name='settings'),

    # Spotify interaction
    path('spotify/album/save/<spid:id>/', views.spotify_album_save,
        name='spotify_album_save'),
    path('spotify/album/unsave/(<spid:id>/', views.spotify_album_unsave,
         name='spotify_album_unsave'),
    path('spotify/sync_albums/', views.spotify_sync_albums,
        name='spotify_sync_albums'),
      # Authentication
    path('spotify_auth/', views.spotify_auth,
        name='spotify_auth'),
    path('spotify/sign_in/', views.spotify_sign_in,
        name='spotify_sign_in'),
    path('spotify/sign_out/', views.spotify_sign_out,
        name='spotify_sign_out'),
    path('spotify/album/action/', views.spotify_album_action,
        name='spotify_album_action'),
]  + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
