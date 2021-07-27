from subprocess import Popen, PIPE

signal_colors = ['#ef0e0b', '#f7a002', '#d6d227', '#87d627', '#08f61f']

nm_version_bytes, _ = Popen(['NetworkManager', '--version'], stdout=PIPE).communicate()
nm_version = map(int, nm_version_bytes.strip().split(b'.'))

class AccessPoint(object):
    """
    A wireless access point.
    """
    def __init__(self, active, ssid, bssid, signal, security, device):
        if ssid and ssid[0] == ssid[-1] == "'":
            ssid = ssid[1:-1]
        self.active, self.ssid, self.bssid, self.signal, self.security, self.device = (
            active == 'yes', ssid, bssid, signal, security, device)

    def __repr__(self):
        return '{} ({})'.format(self.ssid, self.bssid)

    @property
    def color(self):
        return signal_colors[min(4, self.signal // 20)]

class WifiConnection(object):
    """
    A NetworkManager wifi connection.
    """
    _new_ssid_command = ['nmcli', '-s', '-t', '--fields', '802-11-wireless.ssid',
                         'con', 'show', 'uuid']
    _old_ssid_command = ['nmcli', '-t', '--fields', '802-11-wireless', 'con',
                         'list', 'uuid']

    def __init__(self, name, uuid):
        self.name, self.uuid = name, uuid

    def __repr__(self):
        return self.name

    @property
    def ssid(self):
        info, _ = Popen(self._new_ssid_command + [self.uuid], stdout=PIPE).communicate()
        info = info.decode('ascii')
        return info.split(':',1)[1].strip()

class WifiManager(object):
    """
    An object that manages NetworkManager wifi connections using nmcli.
    """

    _ap_command = ['nmcli', '-t', '-f', 'ACTIVE,SSID,BSSID,MODE,SIGNAL,SECURITY,DEVICE',
                   'dev', 'wifi', 'list']
    _connect_command = ['sudo', 'nmcli', 'con', 'up', 'uuid']
    _status_command = ['nmcli', '-t', '-f', 'STATE', 'dev', 'status']
    _disconnect_command = ['sudo', 'nmcli', 'dev', 'disconnect', 'iface']
    _add_command = ['sudo', 'nmcli', 'dev', 'wifi', 'con', '', 'password', '', 'name', '']
    _delete_command = ['sudo', 'nmcli', 'con', 'delete']
    _create_command = ['nmcli', 'dev', 'wifi', 'connect']
    _con_command = ['nmcli', '-t', '-f', 'NAME,UUID,TYPE', 'con', 'show']
 
    def __init__(self):
        self._connections = []

    @property
    def access_points(self):
        """
        A list of AccessPoint objects representing all wireless access points that
        are visible.
        """
        ap_list = []
        aps, _ = Popen(self._ap_command, stdout=PIPE).communicate()
        aps = aps.decode('ascii')
        for line in aps.split('\n'):
            try:
                active, ssid, bssid, mode, signal, security, device = line.replace(r'\:', '.').split(':')
                if mode.startswith('Infra'):
                    bssid = bssid.replace('.', ':')
                    ap_list.append(AccessPoint(active, ssid, bssid, int(signal), security, device))
            except ValueError:
                pass
        return sorted(ap_list, key=lambda x: -x.signal)

    @property
    def connections(self):
        """
        A list of WifiConnection objects representing all NetworkManager wireless connections.
        """
        connection_list = []
        cons, _ = Popen(self._con_command, stdout=PIPE).communicate()
        cons = cons.decode('ascii')
        for line in cons.split('\n'):
            try:
                name, uuid, con_type = line.strip().split(':')
                if con_type == '802-11-wireless':
                    connection_list.append(WifiConnection(name, uuid))
            except ValueError:
                pass
        return connection_list

    @property
    def up_count(self):
        """
        Return the number of active connections, wired or wireless.
        """
        states, _ = Popen(self._status_command, stdout=PIPE).communicate()
        states = states.decode('ascii')
        return states.split('\n').count('connected') 
        
    def _run_cmd(self, command):
        """
        Run an nmcli command.
        """
        process = Popen(command, stderr=PIPE, stdout=PIPE)
        out, err = process.communicate()
        if process.returncode != 0:
            return err

    def connect(self, ssid):
        """
        Try to connect to an access point with the specified ssid.
        First iterate through all connections with that ssid. 
        """
        connections = self.connections
        password_saved = False
        for con in connections:
            if con.ssid == ssid:
                password_saved = True
                result = self._run_cmd(self._connect_command + [con.uuid])
                if result is None:
                    return
        if password_saved:
            return 'Failed'
        else:
            return 'No password'

    def create(self, ssid, password):
        """
        Create a new connection with the specified ssid and password.  Try
        to connect; if this succeeds, save the new connection and delete all
        old connections with the same ssid.
        """
        connections = self.connections
        same_ssid = []
        for con in connections:
            if con.ssid == ssid:
                same_ssid.append(con)
        result = self._run_cmd(self._create_command + [ssid, 'password', password])
        if result is None:
            for con in same_ssid:
                self.delete(con.uuid)
        else:
            return 'Failed'

    def disconnect(self, device):
        """
        Disconnect from the access point with specified ssid.
        """
        self._run_cmd(self._disconnect_command + [device])

    def delete(self, uuid):
        """
        Delete the connection with the specified uuid.
        """
        self._run_cmd(self._delete_command + [uuid])

    def add(self, ssid, password, device=None):
        """
        Add a new connection with the specified ssid and WPA/WPA2 password.
        """
        cmd = list(self._add_command)
        cmd[cmd.index('')] = ssid
        cmd[cmd.index('')] = password 
        cmd[cmd.index('')] = ssid
        if device:
            cmd[cmd.index('*')] = device
        self._run_cmd(cmd)
