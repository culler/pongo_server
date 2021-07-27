import socket
import sys
import time
import json

class SplayerController(object):
    def __init__(self):
        self.decoder = json.JSONDecoder()
        self.encoder = json.JSONEncoder()
        self.received = ''
        
    def _send_command(self, command):
        result = None
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect('/var/tmp/pongo_daemon/control')
        sock.sendall(command.encode('ascii') + b'\n')
        try:
            while self.received.count('\n') == 0:
                block = sock.recv(4096).decode('ascii')
                if len(block) == 0:
                    break
                else:
                    self.received += block
            parts = self.received.split('\n', 1)
            preamble = parts[0]
            self.received = parts[1] if len(parts) == 2 else ''
            if preamble.startswith('DATA'):
                while self.received.count('\n') == 0:
                    block = sock.recv(4096).decode('ascii')
                    if len(block) == 0:
                        break
                    else:
                        self.received += block
                parts = self.received.split('\n', 1)
                data = parts[0]
                self.received = parts[1] if len(parts) == 2 else ''
                result = self.decoder.decode(data)
            else:
                result = preamble.strip()
        except socket.timeout:
            result = 'timed out'
        sock.close()
        return result

    def play_tracks(self, *uris):
        self._send_command('eject')
        for uri in uris:
            if uri:
                self._send_command('append %s'%uri)

    def append_tracks(self, *uris):
        for uri in uris:
            if uri:
                self._send_command('append %s'%uri)

    def get_queue(self):
        return [t.split(':')[-1] for t in self._send_command('queue')]

    def get_current_track(self):
        current = self._send_command('current')
        if current:
            return current.split(':')[-1]
        else:
            return None

    def get_remaining(self):
        return self._send_command('remaining')

    def get_state(self):
        return self._send_command('state')

    def pause(self):
        self._send_command('pause')

    def resume(self):
        self._send_command('resume')

    def restart(self):
        self._send_command('restart')

    def forward(self):
        self._send_command('next')

    def back(self):
        self._send_command('previous')

    def jump(self, n):
        self._send_command('jump %d'%int(n))

    def eject(self):
        self._send_command('eject')

    def queue_remove(self, n):
        self._send_command('remove %d'%int(n))

