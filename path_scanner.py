import csv
import hashlib
import os
from typing import Dict, Tuple, Set

BLOCK_SIZE = 65536


def scan_csv(
        path: str
) -> Tuple[Dict[str, Set[Tuple[str, str]]], Dict[Tuple[str, str], Set[str]]]:
    checksum_to_app_version: Dict[str, Set[Tuple[str, str]]] = {}
    app_version_to_checksum: Dict[Tuple[str, str], Set[str]] = {}

    with open(path) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        for line in csv_reader:
            checksum = line[2]
            app_version = (line[0], line[1])
            checksum_to_app_version.setdefault(checksum, set()).add(app_version)
            app_version_to_checksum.setdefault(app_version, set()).add(checksum)

    return checksum_to_app_version, app_version_to_checksum


def scan_csv_light(
        path: str
) -> Tuple[Dict[str, Set[Tuple[str, str]]], Set[Tuple[str, str]]]:
    checksum_to_app_version: Dict[str, Set[Tuple[str, str]]] = {}
    app_versions: Set[Tuple[str, str]] = set()

    with open(path) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        for line in csv_reader:
            checksum = line[2]
            app_version = (line[0], line[1])
            checksum_to_app_version.setdefault(checksum, set()).add(app_version)
            app_versions.add(app_version)

    return checksum_to_app_version, app_versions


def scan_path(
        dir: str
) -> Tuple[Dict[str, Set[Tuple[str, str]]], Dict[Tuple[str, str], Set[str]]]:
    checksum_to_app_version: Dict[str, Set[Tuple[str, str]]] = {}
    app_version_to_checksum: Dict[Tuple[str, str], Set[str]] = {}

    for app in os.listdir(dir):
        app_path = dir + '/' + app
        for version in os.listdir(app_path):
            version_path = app_path + '/' + version
            app_version = (app, version)
            app_version_to_checksum[app_version] = scan_app_version(checksum_to_app_version, app_version, version_path)

    return checksum_to_app_version, app_version_to_checksum


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


def scan_app_version(
        checksum_to_app_version: Dict[str, Set[Tuple[str, str]]],
        app_version: Tuple[str, str],
        path: str
) -> Set[str]:
    pq = set()
    for root, dirs, files in os.walk(path):
        for file_name in files:
            try:
                path = os.path.join(root, file_name)
                # cs = db.get_by_path(path)
                # if cs is None:
                cs = byte_arr_to_hex_string(hash(path).digest())
                # db.insert(path, cs)
                checksum_to_app_version.setdefault(cs, set()).add(app_version)
                pq.add(cs)
            except Exception as e:
                print(e)
                raise e
    return pq
