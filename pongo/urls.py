from django.conf.urls import url
from django.conf import settings
from django.conf.urls.static import static
from django.views.decorators.cache import cache_page
from . import views

urlpatterns = [
    url(r'^$', views.index,
        name='index'),

    # AJAX state queries
    url(r'^state/albums/(?P<key>[A-z]*)', views.albums_state,
        name='albums_state'),
    url(r'^state/player', views.spotify_player_state,
        name='player_state'),

    # Pasting
    url(r'^paste/album/(?P<id>[0-9A-z]{22})', views.album_paste,
        name='album_paste'),
    url(r'^paste/playlist(?P<id>[0-9A-z]{22})', views.playlist_paste,
        name='playlist_paste'),
    url(r'paste/error', views.paste_error, name='paste_error'),

    # Albums
    url(r'^album/(?P<id>[0-9A-z]{22})', views.album, name='album'),
    url(r'^albums', views.albums, name='albums'),

    # Playlists
    url(r'^playlist/(?P<id>[0-9A-z]{22})', views.playlist, name='playlist'),
    url(r'^playlists', views.playlists, name='playlists'),

    # Suggest
    url(r'^suggest', views.suggest, name='suggest'),
    
    # Player
      # AJAX player control commands
    url(r'^player/play/(?P<id>[0-9A-z]{22})', views.player_play_album,
        name='player_play_album'),
    url(r'^player/pause', views.spotify_player_pause,
        name='player_pause'),
    url(r'^player/play', views.spotify_player_play,
        name='player_play'),
    url(r'^player/forward', views.spotify_player_forward,
        name='player_forward'),
    url(r'^player/back', views.spotify_player_back,
        name='player_back'),
    url(r'^player/eject', views.spotify_player_eject,
        name='player_eject'),
    url(r'^player/jump/(?P<n>[0-9]+)', views.spotify_player_jump,
        name='player_jump'),
    url(r'^player/remove/(?P<n>[0-9]+)', views.spotify_player_remove,
        name='player_remove'),
      # player page
    url(r'^player', views.player, name='player'),

    # Settings
    url(r'^settings/name', views.settings_name, name='settings_name'),
    url(r'^settings/connect_new', views.settings_connect_new, name='settings_connect_new'),
    url(r'^settings/connect', views.settings_connect, name='settings_connect'),
    url(r'^settings/disconnect', views.settings_disconnect, name='settings_disconnect'),
    url(r'^settings/eject', views.settings_eject, name='settings_eject'),
    url(r'^settings/restart', views.settings_restart, name='settings_restart'),
    url(r'^settings/shutdown', views.settings_shutdown, name='settings_shutdown'),
    url(r'^settings', views.settings, name='settings'),
    
    # Spotify interaction

      # AJAX commands
    url(r'^spotify/album/save/(?P<id>[0-9A-z]{22})', views.spotify_album_save,
        name='spotify_album_save'),
    url(r'^spotify/album/unsave/(?P<id>[0-9A-z]{22})',
        views.spotify_album_unsave, name='spotify_album_unsave'),
    url(r'^spotify/sync_albums', views.spotify_sync_albums,
        name='spotify_sync_albums'),
      # Authentication
    url(r'^spotify_auth', views.spotify_auth,
        name='spotify_auth'),
    url(r'^spotify/sign_in', views.spotify_sign_in,
        name='spotify_sign_in'),
    url(r'^spotify/sign_out', views.spotify_sign_out,
        name='spotify_sign_out'),
    url(r'^spotify/album/action', views.spotify_album_action,
        name='spotify_album_action'),
]  + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
