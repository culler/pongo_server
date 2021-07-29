from django.http import HttpResponse
from django.shortcuts import render
from django.core.cache import cache
from django.views.decorators.cache import cache_page
from django.utils.cache import patch_cache_control
from json import JSONEncoder
from operator import methodcaller
from configparser import ConfigParser
from xml.etree import ElementTree
import collections
import socket
import time
import re
import subprocess
from .models import *
from .spotify_utils import *
from .splayer import SplayerController
from .usb_drives import USBDrive
from .wifi import WifiManager, signal_colors
from . import __path__

# Config Data:
# We store our config data in a ConfigParser object, named
# pongo_config, which is defined at the module level.  However, since each
# uwsgi process will import this module separately, we must take care
# when changing the config data to update the object in each process.
# Currently we just use the config file itself as shared data, and reread the file
# each time we access the config data.  (We have to look up the name
# of the Pongo for the header of several pages.)  The config file is
# short, so this is reasonably fast. (I measured 0.5
# milliseconds.)  But we could consider doing something fancier.
config_file = '/var/tmp/pongo_server/pongo.ini'
pongo_config = ConfigParser()
pongo_config.read(config_file)
splayer_config_file='/var/tmp/pongo_daemon/splayerd/splayerd.cfg'
splayer_config_data = """splayer :
{
  username = "%s";
  password = "%s";
};
"""
splayer_controller = SplayerController()
json_encoder = JSONEncoder()
wifi_manager = WifiManager()
prevent_scroll = False
album_lists = {'title': None, 'artists': None}
apple = re.compile('iPhone|iPad|iPod')
avahi_file = '/etc/avahi/services/pongo.service'
avahi_header = """<?xml version="1.0" encoding="UTF-8" standalone="no" ?>
<!DOCTYPE service-group SYSTEM "avahi-service.dtd">
"""

cache.clear()

def clear():
    global album_lists
    album_lists = {'title': None, 'artists': None}
    cache.clear()

def is_app(request):
    return request.META['HTTP_USER_AGENT'].startswith('Pongo')
    
def index(request):
    return redirect('/albums/')

def albums(request):
    global album_lists
    album_path = request.COOKIES.get('album', None)
    tab = request.COOKIES.get('tab', None)
    if album_path and tab != 'albums':
        return redirect(album_path)
    sort_key = request.COOKIES.get('album_sort_key', 'artists')
    key = request.POST.get('key', None)
    if key and key != sort_key:
        sort_key = key
    spotify_user = get_current_user(request)
    # Don't recompute if we will be getting the album list from the cache.
    if album_lists[sort_key] == None:
        album_list = SpotifyAlbum.objects.all()
        if sort_key == 'artists':
            album_list = sorted(album_list, key=methodcaller('artist_sort'))
        for album in album_list:
            album.owned = album.spotifyuser_set.filter(
                id=spotify_user).exists()
            if album.num_discs > 1:
                album.discs = range(1, album.num_discs + 1)
            else:
                album.discs = None
        album_lists[sort_key] = album_list
    pongo_config.read(config_file)
    context = {'server': pongo_config.get('server', 'name'),
               'spotify_user': spotify_user,
               'albums': album_lists[sort_key],
               'is_app': is_app(request),
               'sort_key': sort_key}
    start = time.time()
    response = render(request, 'pongo/albums.html', context)
    patch_cache_control(response, no_cache=True, no_store=True,
                        must_revalidate=True)
    response.set_cookie('tab', 'albums')
    response.set_cookie('album_sort_key', sort_key)
    if request.COOKIES.get('tab', None) == 'albums':
        response.delete_cookie('album')
    return response

def album(request, id):
    spotify_user = get_current_user(request)
    pongo_config.read(config_file)
    context = {'server': pongo_config.get('server', 'name'),
               'spotify_user': spotify_user}
    try:
        context['album'] = album = SpotifyAlbum.objects.get(id=id)
        context['new_album'] = False;
    except SpotifyAlbum.DoesNotExist:
        try:
            context['album'] = album = import_album_by_id(id)
            context['new_album'] = True;
        except SpotifyException:
                return render(request, 'pongo/album.html',
                              {'invalid_id': id})
    if album is None:
        response = render(request, 'pongo/album.html',
                              {'failed_id': id})
    else:
        discs = collections.defaultdict(list)
        for track in album.tracks():
            discs[track.disc_number].append(track)
        context['discs'] = [sorted(discs[n], key=lambda t : t.track_number)
                            for n in sorted(discs.keys())]
        context['many_discs'] = (len(context['discs']) > 1)
        if spotify_user:
            album.owned = album.spotifyuser_set.filter(
                id=spotify_user).exists()
        response = render(request, 'pongo/album.html', context)
    response.set_cookie('tab', 'albums')
    response.set_cookie('album', request.path)
    return response

def albums_state(request, key='title'):
    global album_lists
    if album_lists.get(key, None) != None:
        response = HttpResponse('"current"')
    else:
        response = HttpResponse('"stale"')
    return response

def playlist(request, id):
    response = HttpResponse('Not implemented yet.')
    response.set_cookie('tab', 'playlists')
    return response

def playlists(request):
    spotify_user = get_current_user(request)
    pongo_config.read(config_file)
    context = {'server': pongo_config.get('server', 'name'),
               'is_app': is_app(request),
               'spotify_user': spotify_user}
    response = render(request, 'pongo/playlists.html', context)
    response.set_cookie('tab', 'playlists')
    return response

def playlists_state(request):
    return HttpResponse('"current"')

def suggest(request):
    spotify_user = get_current_user(request)
    pongo_config.read(config_file)
    context = {'server': pongo_config.get('server', 'name'),
               'is_app': is_app(request),
               'spotify_user': spotify_user}
    response = render(request, 'pongo/suggest.html', context)
    response.set_cookie('tab', 'suggest')
    return response

def album_paste(request, id):
    clear()
    return album(request, id)

def playlist_paste(request, id):
    return HttpResponse('ID = %s'%i)

def paste_error(request):
    return render(request, 'pongo/paste_error.html', {})

def player(request):
    global prevent_scroll
    spotify_user = get_current_user(request)
    try:
        track_ids = splayer_controller.get_queue()
    except socket.error:
        return HttpResponse('Could not connect to splayerd')
    tracks = []
    player_state = splayer_controller.get_state()
    if player_state == 'FAILED':
        return render(request, 'pongo/player.html',
                      {'daemon_is_running': False})
    current = player_state['current_track']
    # This only works for spotify uris!  Fix for others.
    current_id = current.split(':')[-1] if current else None
    has_current_track = 'false';
    for id in track_ids:
        track = SpotifyTrack.objects.get(id=id)
        if (current_id == id):
            track.is_current = True
            has_current_track = 'true'
        else:
            track.is_current= False
        mins, ms = divmod(track.duration_ms, 60000)
        secs = int(round(float(ms)/1000))
        track.duration = '%d:%.2d'%(mins, secs)
        tracks.append(track)
    current_index = player_state['current_index']
    queue_length = player_state['queue_length']
    can_go_back = (has_current_track == 'true' and current_index > 0)
    can_go_forward = (has_current_track == 'true' and
                      0 <= current_index < queue_length - 1)
    player_ready = (player_state['track_loaded'] == 'true' or
                    player_state['current_index'] >= player_state['queue_length'])
    context = {'daemon_is_running': True,
               'server': pongo_config.get('server', 'name'),
               'tracks': tracks,
               'remaining': player_state['remaining'],
               'queue_length': queue_length,
               'player_ready': 'true' if player_ready else 'false',
               'tracks_ahead': queue_length - current_index, 
               'is_paused': player_state['is_paused'],
               'has_current_track': has_current_track,
               'can_go_back': 'true' if can_go_back else 'false',
               'can_go_forward': 'true' if can_go_forward else 'false',
               'prevent_scroll': 'true' if prevent_scroll else 'false',
               'is_app': is_app(request),
               'spotify_user': spotify_user}
    prevent_scroll = False
    response = render(request, 'pongo/player.html', context)
    response.set_cookie('tab', 'player')
    return response

def player_play_album(request, id=None):
    disc = int(request.GET.get('disc', '1'))
    try:
        album = SpotifyAlbum.objects.get(id=id)
    except SpotifyAlbum.DoesNotExist:
        return HttpResponse("That album is not in the database.")
    tracks = [t for t in album.tracks() if t.disc_number == disc]
    tracks.sort(key=lambda t: (t.disc_number, t.track_number))
    track_uris = ['spotify:track:%s'%t.id for t in tracks]
    splayer_controller.play_tracks(*track_uris)
    return redirect('/player/')

def settings(request):
    aps = wifi_manager.access_points
    connected = [ap for ap in aps if ap.active]
    not_connected = [ap for ap in aps if not ap.active]
    pongo_config.read(config_file)
    context = {'server': pongo_config.get('server', 'name'),
               'access_points': not_connected,
               'connected': connected,
               'up_count': wifi_manager.up_count,
               'colors': signal_colors,
               'usb_drives': USBDrive.mounted()}
    return render(request, 'pongo/settings.html', context)

def settings_name(request):
    """
    Change the name of this Pongo in both the config file
    and the avahi service file.
    """
    new_name = request.POST.get('pongo_name', None)
    if new_name:
        # update the avahi service file
        tree = ElementTree.parse(avahi_file)
        root = tree.getroot()
        for child in root:
            if child.tag == 'name':
                child.text = new_name
                break
        with open(avahi_file, 'wb') as output:
            output.write(avahi_header.encode('UTF-8'))
            tree.write(output, encoding='UTF-8', xml_declaration=False)
            output.write(b'\n')
        # update the Pongo config file
        pongo_config.set('server', 'name', new_name)
        with open(config_file, 'w') as config:
            pongo_config.write(config)
        cache.clear()
    return redirect('/settings/')

def settings_connect(request):
    ssid = request.POST['ssid']
    result = wifi_manager.connect(ssid)
    if result is None:
        return redirect('/settings/')
    if result == 'No password':
        context={'get_password': True,
                 'no_password': True,
                 'ssid': ssid}
    else:
        context={'get_password': True,
                 'no_password': False,
                 'saved_failed':True,
                 'ssid': ssid}
    return render(request, 'pongo/settings.html', context)

def settings_connect_new(request):
    ssid = request.POST['ssid']
    password = request.POST['password']
    result = wifi_manager.create(ssid, password)
    if result is None:
        return redirect('/settings/')
    if result == 'Failed':
        context={'get_password': True,
                 'no_password': False,
                 'saved_failed': False,
                 'password': password,
                 'ssid': ssid}
    return render(request, 'pongo/settings.html', context)

def settings_disconnect(request):
    device = request.POST['device']
    wifi_manager.disconnect(device)
    return redirect('/settings/')

def settings_credentials(request):
    if request.method == 'POST':
        data = splayer_config_data%(
            request.POST['username'],
            request.POST['password'])
        with open(splayer_config_file, 'w') as output:
            output.write(data)
    return redirect('/settings/')

def settings_eject(request):
    mounted = dict((d.device, d) for d in USBDrive.mounted())
    for dev in request.POST.getlist('eject[]'):
        mounted[dev].unmount()
    return redirect('/settings/')

def settings_restart(request):
    proc = subprocess.Popen(['/usr/bin/sudo', '/sbin/reboot'],
                     stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    out, err = proc.communicate()
    if err:
        return HttpResponse(err)
    time.sleep(5)

def settings_shutdown(request):
    proc = subprocess.Popen(['/usr/bin/sudo', '/sbin/shutdown', '-h', 'now'],
                     stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    out, err = proc.communicate()
    if err:
        return HttpResponse(err)
    time.sleep(5)

def spotify_album_action(request):
    post = request.POST
    album_id = post['album_id']
    album = SpotifyAlbum.objects.get(id=album_id)
    if 'pongo_remove_album' in post:
        album.delete()
        clear()
        return redirect('/albums/')
    elif 'spotify_save_album' in post:
        save_on_spotify(album.id)
        clear()
        return redirect('/album/%s'%album_id)
    elif 'play_tracks' in post or 'queue_tracks' in post:
        track_dict = dict( ((t.disc_number, t.track_number), t)
                           for t in album.tracks())
        tracks = []
        for key in post:
            if key.startswith('track'):
                disc, track = key.split('_')[1:]
                tracks.append(track_dict[(int(disc), int(track))])
    elif 'play_album' in post or 'queue_album' in post:
        tracks = list(album.tracks())
    else:
        return HttpResponse("Not implemented yet")
    if 'queue_tracks' in post or 'queue_album' in post:
        action = splayer_controller.append_tracks
    else:
        action = splayer_controller.play_tracks
    tracks.sort(key=lambda t: (t.disc_number, t.track_number))
    track_uris = ['spotify:track:%s'%t.id for t in tracks]
    action(*track_uris)
    return redirect('/player/')

def spotify_album_save(request, id=None):
    if id:
        save_on_spotify(id)
        clear()
        return HttpResponse('OK')
    else:
        return HttpResponse('FAILED')

def spotify_album_unsave(request, id=None):
    if id:
        delete_from_spotify(id)
        clear()
        return HttpResponse('OK')
    else:
        return HttpResponse('FAILED')

def spotify_sync_albums(request):
    spotify_user = get_current_user(request)
    if spotify_user == None:
        return redirect('/spotify/sign_in?redirect=/spotify/sync_albums?redirect=%s'%request.GET['redirect'])
    sync_spotify_albums()
    clear()
    return redirect(request.GET['redirect'])

def spotify_player_state(request):
    return HttpResponse(json_encoder.encode(splayer_controller.get_state()))

def spotify_player_pause(request):
    global prevent_scroll
    splayer_controller.pause()
    prevent_scroll = True
    return HttpResponse('OK')

def spotify_player_play(request):
    global prevent_scroll
    state = splayer_controller.get_state()
    if state['is_paused'] == 'true':
        splayer_controller.resume()
    else:
        splayer_controller.restart()
    prevent_scroll = True
    return HttpResponse('OK')

def spotify_player_forward(request):
    splayer_controller.forward()
    return HttpResponse('OK')

def spotify_player_back(request):
    splayer_controller.back()
    return HttpResponse('OK')

def spotify_player_jump(request, n=0):
    splayer_controller.jump(n)
    return HttpResponse('OK')

def spotify_player_eject(request):
    splayer_controller.eject()
    return HttpResponse('OK')

def spotify_player_remove(request, n=None):
    global prevent_scroll
    if n != None:
        splayer_controller.queue_remove(n)
    prevent_scroll = True
    return HttpResponse('OK')

def spotify_auth(request):
    """
    The spotify client (either the mobile app or a webbrowser) will
    load this view when a user finishes authenticating with spotify.
    The query string will contain two keys: code and page.  The code
    must be converted into an access token and a refresh token, to be
    stored in /var/tmp/pongo_auth_cache. Then we should redirect to
    the view specified by the url provided in the page parameter.
    
    The spotify_sign_in view contacts pongomusic.com to register a
    state value with the pongomusic server.  The state value is associated
    with the url that eventually gets provided in the page query. The
    redirect url provided to spotify is https://pongomusic.com/redirect/.
    That view extracts the state, uses it to look up the url to be
    sent as the page, and then redirects to this method. The default value
    of the page is localhost:8880/.

    The mobile app also traps requests to localhost and remaps those to
    this view.  If spotify redirects to "http://localhost:8800...", then
    the client will remap to:
    "http://[this pongo]/spotify_auth/state=xx;code=xx
    """
    code = request.GET['code']
    token_info = get_token_info(code)
    if token_info:
        spotify = Spotify(auth=token_info['access_token'])
        user = spotify.current_user()
        # If this is a new user, save it.
        try:
            SpotifyUser.objects.get(id=user['id'])
        except SpotifyUser.DoesNotExist:
            spotify_user = SpotifyUser.objects.create(
                id=user['id'],
                display_name=user['display_name'])
            spotify_user.save()
        try:
            url = request.GET['page']
        except:
            # Remap by the mobile app
            url = request.GET['state']
        return redirect(url)
    return HttpResponse("""
        <html>
        <head><title>Error</title></head>
        <body>
        <h1 style="text-align: center;">So Sorry!</h1>
        <h2 style="text-align: center;">The authentication failed.</h2>
        <div style="text-align: center;">
        <a style="-webkit-appearance: button;
                  text-decoration: none;
                  color: initial;
                  padding: 5px;"
           href="/">Return</a>
        </body>
        </html>""")

def spotify_sign_in(request):
    path = request.GET['redirect'].rstrip('/') + '/'
    #show_dialog = not os.path.exists(AUTH_CACHE)
    auth_object = oauth2.SpotifyOAuth(PONGO_CLIENT_ID,
                                      PONGO_CLIENT_SECRET,
                                      REDIRECT,
                                      state=get_state(path=path),
                                      scope=SCOPE,
                                      show_dialog=True,
                                      cache_path=AUTH_CACHE)
    clear()
    return redirect(auth_object.get_authorize_url())

def spotify_sign_out(request):
    clear_auth_cache()
    clear()
    path = request.GET['redirect'].rstrip('/') + '/'
    return redirect(path)
