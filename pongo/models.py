from __future__ import unicode_literals
import os
from urllib.request import urlretrieve
from django.db import models
from django.conf import settings
from django.core.files import File

class SpotifyAlbum(models.Model):
    id = models.CharField(max_length=22, primary_key=True)
    name = models.CharField(max_length=256)
    num_discs = models.IntegerField(null=True)
    release_year = models.IntegerField(null=True)
    performers = models.TextField(null=True)

    class Meta:
        ordering = ['name']
        
    def __str__(self):
        return self.name

    def make_performers(self):
        # Hack to try to identify which of the artists are performers.
        return ', '.join([a.name for a in self.artists()
                          if a.is_performer()])
    def tracks(self):
        return self.spotifytrack_set.all()

    def artists(self):
        return self.spotifyartist_set.all()

    def images(self):
        image_queryset = self.spotifyimage_set.all()
        if image_queryset.count():
            return sorted(image_queryset, key=lambda x: x.width)
        return []

    def small_image_url(self):
        images = self.images()
        if images:
            return images[0].image_file.url

    def large_image_url(self):
        images = self.images()
        if images:
            return images[-1].image_file.url

    def genres(self):
        return self.spotifygenre_set.all()
    
    def delete(self):
        artists = set(self.spotifyartist_set.all())
        for track in self.tracks():
            artists = artists.union(track.artists())
        genres = set(self.spotifygenre_set.all())
        for artist in artists:
            genres = genres.union(artist.genres())
        image_files = [im.image_file.path for im in self.images() if im.image_file]
        for artist in artists:
            genres = genres.union(artist.spotifygenre_set.all())
        super(SpotifyAlbum, self).delete()
        for artist in artists:
            if artist.spotify_tracks.count() == 0:
                artist.delete()
        for genre in genres:
            if ( genre.spotify_albums.count() == 0 and
                 genre.spotify_artists.count() == 0 ):
                genre.delete()
        for file in image_files:
            try:
                os.unlink(file)
            except IOError:
                pass

    def artist_list(self):
        return ', '.join([a.name for a in self.artists()])

    def artist_sort(self):
        # Rather stupid to sort by first name, but Spotify
        # does the same thing ...
        # Should have an editable artist sort field in the model.
        artists = self.artists()
        if len(artists) > 0:
            words = artists[0].name.split()
            if len(words) > 1:
                first = words[0]
                return first if first.lower() != 'the' else words[1]
            else:
                return words[0]
        else:
            return None

class SpotifyImage(models.Model):
    spotify_url = models.CharField(max_length=128, primary_key=True)
    width = models.IntegerField(default=0)
    height = models.IntegerField(default=0)
    image_file = models.ImageField(width_field='width',
                                   height_field='height',
                                   upload_to='pongo',
                                   null=True)
    spotify_album = models.ForeignKey(SpotifyAlbum,
                                      on_delete=models.CASCADE,
                                      null=True)

    def __str__(self):
        return '%s(%sx%s)'%(self.album().name, self.width, self.height)

    def album(self):
        return self.spotify_album

    def cache(self):
        if not self.image_file:
            image_id = self.spotify_url.split('/')[-1]
            filename = settings.MEDIA_ROOT + os.path.join('pongo', image_id)
            if not os.path.exists(filename):
                tmpfiles = urlretrieve(self.spotify_url)
                os.chmod(tmpfiles[0], 0o644)
            self.image_file.name = image_id
            self.image_file.save(
                image_id,
                File(open(tmpfiles[0], 'rb')))
            self.save()

    def delete(self):
        filename == None
        if self.image_file:
            filename = self.image_file.path
        super(SpotifyImage, self).delete()
        if filename:
            try:
                os.unlink(filename)
            except OSError:
                pass
              
class SpotifyTrack(models.Model):
    id = models.CharField(max_length=22, primary_key=True)
    name = models.CharField(max_length=256)
    disc_number = models.IntegerField()
    track_number = models.IntegerField()
    duration_ms = models.IntegerField()
    spotify_album = models.ForeignKey(SpotifyAlbum,
                                       on_delete=models.CASCADE)

    def __str__(self):
        return self.name
    
    def album(self):
        return self.spotify_album

    def artists(self):
        return self.spotifyartist_set.all()

    def artist_names(self):
        return ', '.join([a.name for a in self.artists()]) 

class SpotifyArtist(models.Model):
    id = models.CharField(max_length=22, primary_key=True)
    name = models.CharField(max_length=256)
    is_composer = models.BooleanField(null=True)
    spotify_albums = models.ManyToManyField(SpotifyAlbum)
    spotify_tracks = models.ManyToManyField(SpotifyTrack)

    def __str__(self):
        return self.name

    def albums(self):
        return self.spotify_albums.all()
    
    def tracks(self):
        return self.spotify_tracks.all()

    def genres(self):
        return self.spotifygenre_set.all()

    def is_performer(self):
        if len(self.spotifygenre_set.filter(id='classical performance')) > 0:
            return True
        if len(self.spotifygenre_set.filter(id='classical')) == 0:
            return True
        return False
    
class SpotifyGenre(models.Model):
    id = models.CharField(max_length=64, primary_key=True)
    spotify_albums = models.ManyToManyField(SpotifyAlbum)
    spotify_artists = models.ManyToManyField(SpotifyArtist)

    def __str__(self):
        return self.id

    def albums(self):
        return self.spotify_albums.all()
    
    def artists(self):
        return self.spotify_artists.all()

class SpotifyUser(models.Model):
    id = models.CharField(max_length=256, primary_key=True)
    display_name = models.CharField(max_length=256, null=True)
    spotify_albums = models.ManyToManyField(SpotifyAlbum)
    
    def __str__(self):
        if self.display_name:
            return self.display_name
        else:
            return self.id
