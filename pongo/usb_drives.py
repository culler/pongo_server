import os, re
from subprocess import call, Popen, PIPE

class USBDrive(object):

    def __init__(self, id, device):
        self.id, self.device = id, device

    def __repr__(self):
        if self.device:
            return '<%s on %s>'%(self.label, self.device)
        else:
            return '<unmounted drive>'
    @classmethod
    def _attached(cls):
        """
        Return a list of USBDrive instances for all usb_drives
        attached to the system, mounted or not.
        """
        root = '/dev/disk/by-id'
        result = []
        for id in os.listdir(root):
            if not id.startswith('usb'):
                continue
            link = os.path.join(root, id)
            dev_rel = os.path.join(root, os.readlink(link))
            dev_abs = os.path.join(root, dev_rel)
            device = os.path.abspath(dev_abs)
            result.append(USBDrive(id, device))
        return result

    @classmethod
    def mounted(cls):
        mounts = set()
        with open('/proc/mounts') as input:
            for line in input.read().split('\n'):
                if line:
                    mounts.add(line.split(None, 1)[0])
        return [ drive for drive in USBDrive._attached()
                 if drive.device in mounts]

    _hexre = re.compile(r'\\x[0-9abcdefABCDEF]{2}')

    @staticmethod
    def _hexsubfn(match):
        return unichr(int(match.group(0).replace('\\', '0'), 16))

    def _unescape(self, s):
        return self._hexre.sub(self._hexsubfn, s)

    @property
    def label(self):
        root = '/dev/disk/by-label'
        if os.path.exists(root):
            for label in os.listdir(root):
                link = os.path.join(root, label)
                dev_rel = os.path.join(root, os.readlink(link))
                dev_abs = os.path.join(root, dev_rel)
                device = os.path.abspath(dev_abs)
                if device == self.device:
                    return self._unescape(label)
        return 'unlabeled'

    def unmount(self):
        call(['pumount', self.device])
        self.device = None
