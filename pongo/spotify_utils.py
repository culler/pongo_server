from urllib.request import urlopen
from django.db import transaction
from django.shortcuts import redirect
from spotipy import oauth2, Spotify, SpotifyException
from .models import *
from pongo_server.settings import PONGO_CLIENT_ID, PONGO_CLIENT_SECRET
import time
import uuid
import requests
import subprocess
hostname_result = subprocess.run(['/bin/hostname'], capture_output=True)
hostname = hostname_result.stdout.decode('utf8').strip()
PORT = 8880
REDIRECT = 'https://pongomusic.com/redirect/'

# Universal values
SCOPE = 'user-library-read user-library-modify'
AUTH_CACHE = '/var/tmp/pongo_auth_cache'

def get_state(path='/'):
    state = uuid.uuid4().hex
    url = 'http://%s:8880%s'%(hostname, path)
    requests.post('https://pongomusic.com/redirect/',
        data={'state': state, 'url': url},
        headers={'referrer': 'https://pongomusic.com'})
    return state

def get_auth_url(page):
    auth_object = oauth2.SpotifyOAuth(PONGO_CLIENT_ID,
                                      PONGO_CLIENT_SECRET,
                                      REDIRECT,
                                      state=get_state(),
                                      scope=SCOPE,
                                      cache_path=AUTH_CACHE)
    return auth_object.get_authorize_url()

def get_token_info(code):
    auth_object = oauth2.SpotifyOAuth(PONGO_CLIENT_ID,
                                      PONGO_CLIENT_SECRET,
                                      REDIRECT,
                                      scope=SCOPE,
                                      cache_path=AUTH_CACHE)
    token_info = auth_object.get_cached_token()
    if not token_info or (token_info['expires_at'] - time.time() < 30):
        token_info = auth_object.get_access_token(code)
    return token_info

def get_current_user(request=None):
    """
    When a request is supplied, this will redirect to the spotify
    authentication url if necessary.
    """
    if request == None:
        path = '/'
    else:
        path = request.get_full_path().rstrip('/') + '/'
    auth_object = oauth2.SpotifyOAuth(PONGO_CLIENT_ID,
                                      PONGO_CLIENT_SECRET,
                                      REDIRECT,
                                      scope=SCOPE,
                                      cache_path=AUTH_CACHE)
    token = auth_object.get_cached_token()
    # print(token)
    if token:
        spotify = Spotify(auth=token['access_token'])
        try:
            user = spotify.current_user()
            return user['id']
        except:
            pass

def clear_auth_cache():
    try:
        os.unlink(AUTH_CACHE)
    except OSError:
        pass

@transaction.atomic
def import_album(album_data, user, spotify):
    # When Spotify removes an album they do not retire the id
    # but they make the album name be an empty string. ????!#!#$
    # For example, they did this with the Bill Evans album
    # spotify:album:0B1wceFa5QuvyABLesFT14
    if not album_data['name']:
        # print 'album %s has been removed by Spotify'%album_data['id']
        return
    album, created = SpotifyAlbum.objects.get_or_create(
        id=album_data['id'],
        defaults={
            'name': album_data['name'],
            'release_year': int(album_data['release_date'].split('-')[0])})
    if user:
        user.spotify_albums.add(album)
    if not created:
        return
    for image_data in album_data['images']:
        url = image_data['url']
        try:
            image, created = SpotifyImage.objects.get_or_create(
                spotify_url=url,
                spotify_album = album)
            if created:
                image.cache()
        # The same image can be associated to different albums, causing
        # a Uniquess error.
        except Exception as e:
            #print e
            #print url
            pass
    for genre_name in album_data['genres']:
        genre, created = SpotifyGenre.objects.get_or_create(id=genre_name)
        genre.albums.add(album)

    for artist_data in album_data['artists']:
        artist_id = artist_data['id']
        artist, created = SpotifyArtist.objects.get_or_create(
            id=artist_id, defaults={'name':artist_data['name']})
        artist.spotify_albums.add(album)
        artist_data = spotify.artist(artist_id)
        for genre_name in artist_data['genres']:
            genre, created = SpotifyGenre.objects.get_or_create(id=genre_name)
            genre.spotify_artists.add(artist)

    tracks = album_data['tracks']['items']
    offset = len(tracks)
    while len(tracks) < album_data['tracks']['total']:
        next_batch = spotify.album_tracks(album_data['id'], offset=offset)
        tracks += next_batch['items']
        offset += len(next_batch['items'])
    num_discs = 1
    for track_data in tracks:
        num_discs = max(num_discs, track_data['disc_number'])
        track, created = SpotifyTrack.objects.get_or_create(
            id=track_data['id'],
            defaults={
            'name': track_data['name'],
            'disc_number': track_data['disc_number'],
            'track_number': track_data['track_number'],
            'duration_ms': track_data['duration_ms'],
                'spotify_album': album})
        for artist_data in track_data['artists']:
            artist, created = SpotifyArtist.objects.get_or_create(
                id=artist_data['id'], defaults={'name': artist_data['name']})
            artist.spotify_tracks.add(track)
    album.num_discs = num_discs
    album.performers = album.make_performers()
    album.save()
    return album

def get_cloud_albums():
    auth_object = oauth2.SpotifyOAuth(PONGO_CLIENT_ID,
                                      PONGO_CLIENT_SECRET,
                                      REDIRECT,
                                      scope=SCOPE,
                                      cache_path=AUTH_CACHE)
    access_token = auth_object.get_cached_token()['access_token']
    spotify = Spotify(auth=access_token)
    first_batch = spotify.current_user_saved_albums(limit=50)
    albums = [a['album'] for a in first_batch['items']]
    offset = len(albums)
    while len(albums) < first_batch['total']:
        next_batch = spotify.current_user_saved_albums(
            limit=50, offset=offset)
        items = [a['album'] for a in next_batch['items']]
        albums += items
        offset += len(items)
    return spotify.current_user(), albums

def sync_spotify_albums():
    start = time.time()
#    print('downloading albums')
    user_info, cloud_albums = get_cloud_albums()
#    print(time.time() - start, 'seconds')
    cloud = dict((a['id'], a) for a in cloud_albums)
    user = SpotifyUser.objects.get(id=user_info['id'])
    auth_object = oauth2.SpotifyOAuth(PONGO_CLIENT_ID,
                                      PONGO_CLIENT_SECRET,
                                      REDIRECT,
                                      scope=SCOPE,
                                      cache_path=AUTH_CACHE)
    access_token = auth_object.get_cached_token()['access_token']
    spotify = Spotify(auth=access_token)
    local = dict((a.id, a)
                 for a in SpotifyAlbum.objects.filter(spotifyuser=user))
 #   print(time.time() - start, 'seconds')
    cloud_ids = set(cloud.keys())
    local_ids = set(local.keys())
    for id in cloud_ids - local_ids:
        album_data = cloud[id]
#        print('importing', album_data['name'])
        import_album(album_data, user, spotify)

def import_album_by_id(id, user=None):
    auth_object = oauth2.SpotifyOAuth(PONGO_CLIENT_ID,
                                      PONGO_CLIENT_SECRET,
                                      REDIRECT,
                                      scope=SCOPE,
                                      cache_path=AUTH_CACHE)
    access_token = auth_object.get_cached_token()['access_token']
    spotify = Spotify(auth=access_token)
    album_data = spotify.album(id)
#    print 'importing', album_data['name']
    return import_album(album_data, user, spotify)

def save_on_spotify(album_id):
    auth_object = oauth2.SpotifyOAuth(PONGO_CLIENT_ID,
                                      PONGO_CLIENT_SECRET,
                                      REDIRECT,
                                      scope=SCOPE,
                                      cache_path=AUTH_CACHE)
    access_token = auth_object.get_cached_token()['access_token']
    spotify = Spotify(auth=access_token)
    user_info = spotify.current_user()
    user = SpotifyUser.objects.get(id=user_info['id'])
#    print 'saving', [album_id]
    spotify.current_user_saved_albums_add([album_id])
    album = SpotifyAlbum.objects.get(id=album_id)
    user.spotify_albums.add(album)

def delete_from_spotify(album_id):
    auth_object = oauth2.SpotifyOAuth(PONGO_CLIENT_ID,
                                      PONGO_CLIENT_SECRET,
                                      REDIRECT,
                                      scope=SCOPE,
                                      cache_path=AUTH_CACHE)
    access_token = auth_object.get_cached_token()['access_token']
    spotify = Spotify(auth=access_token)
    user_info = spotify.current_user()
    user = SpotifyUser.objects.get(id=user_info['id'])
    album = SpotifyAlbum.objects.get(id=album_id)
    spotify.current_user_saved_albums_delete([album_id])
    user.spotify_albums.remove(album)
