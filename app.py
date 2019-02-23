import hashlib
import os
from functools import total_ordering
from typing import Dict, Tuple, Set

import db
from graph import process

BLOCK_SIZE = 65536


def hash(path):
    sha = hashlib.sha256()
    with open(path, 'rb') as file:
        file_buffer = file.read(BLOCK_SIZE)
        while len(file_buffer) > 0:
            sha.update(file_buffer)
            file_buffer = file.read(BLOCK_SIZE)
    return sha


def byte_arr_to_hex_string(bt_arr: bytearray) -> str:
    return ''.join(format(byte, '02x') for byte in bt_arr)


@total_ordering
class Checksum:
    def __init__(self, sha256, app, version):
        self.sha256 = sha256
        self.app = app
        self.version = version

    def checksum(self):
        return

    def __lt__(self, o) -> bool:
        return self.sha256 < o.sha256

    def __eq__(self, o) -> bool:
        return self.sha256 == o.sha256

    def __str__(self) -> str:
        return "Checksum(%s, %s, %s)" % (self.app, self.version, self.checksum())


checksumToAppVersion: Dict[str, Set[Tuple[str, str]]] = {}
appVersionToChecksum: Dict[Tuple[str, str], Set[str]] = {}


def scan_path(app_version, path) -> Set[str]:
    pq = set()
    for root, dirs, files in os.walk(path):
        for file_name in files:
            try:
                path = os.path.join(root, file_name)
                cs = db.get_by_path(path)
                if cs is None:
                    cs = byte_arr_to_hex_string(hash(os.path.join(root, file_name)).digest())
                    db.insert(path, cs)
                checksumToAppVersion.setdefault(cs, set()).add(app_version)
                pq.add(cs)
            except Exception as e:
                print(e)
                raise e
    return pq


db.init()

dir = "fetch/projects"
for app in os.listdir(dir):
    app_path = dir + '/' + app
    for version in os.listdir(app_path):
        version_path = app_path + '/' + version
        app_version = (app, version)
        appVersionToChecksum[app_version] = scan_path(app_version, version_path)

process(checksumToAppVersion, appVersionToChecksum)
