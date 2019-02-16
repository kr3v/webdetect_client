import hashlib
import os
from functools import total_ordering
from typing import List, Dict, Tuple

BLOCK_SIZE = 65536


def hash(path):
    sha = hashlib.sha256()
    with open(path, 'rb') as file:
        file_buffer = file.read(BLOCK_SIZE)
        while len(file_buffer) > 0:
            sha.update(file_buffer)
            file_buffer = file.read(BLOCK_SIZE)
    return sha


@total_ordering
class Checksum:
    def __init__(self, sha256, app, version):
        self.sha256 = sha256
        self.app = app
        self.version = version

    def checksum(self):
        return ''.join(format(byte, '02x') for byte in self.sha256)

    def __lt__(self, o) -> bool:
        return self.sha256 < o.sha256

    def __eq__(self, o) -> bool:
        return self.sha256 == o.sha256

    def __str__(self) -> str:
        return "Checksum(%s, %s, %s)" % (self.app, self.version, self.checksum())


# returns heap of checksum
def scan_path(app, version, path) -> List[str]:
    pq = []
    for root, dirs, files in os.walk(path):
        for file_name in files:
            try:
                byte_arr = hash(os.path.join(root, file_name)).digest()
                pq.append(Checksum(byte_arr, app, version).checksum())
                # heapq.heappush(pq, Checksum(byte_arr, app, version).checksum())
            except:
                pass
    return pq


checksumToAppVersion: Dict[str, List[Tuple[str, str]]] = {}
appVersionToChecksum: Dict[Tuple[str, str], List[str]] = {}
pqs: List[Tuple[str, str, List[str]]] = []

dir = "fetch/projects"
for app in os.listdir(dir):
    app_path = dir + '/' + app
    for version in os.listdir(app_path):
        version_path = app_path + '/' + version
        pqs.append((app, version, scan_path(app, version, version_path)))
        appVersionToChecksum[(app, version)] = []

for (app, version, pq) in pqs:
    appVersion = (app, version)
    for checksum in pq:
        checksumToAppVersion.setdefault(checksum, []).append(appVersion)

for key, values in checksumToAppVersion.items():
    if len(values) == 1:
        appVersion = values[0]
        appVersionToChecksum[appVersion].append(key)

for key, values in appVersionToChecksum.items():
    print(str(key) + ' ' + str(values))
