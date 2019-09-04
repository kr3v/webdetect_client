import json
import struct
import sys
from typing import List, Callable, Set, Dict, Tuple, Optional

import plyvel


class AppVersion:
    app: str
    version: str

    def __init__(self, json_node):
        self.app = json_node["app"]
        self.version = json_node["version"]

    def is_wordpress_theme(self):
        return self.app.startswith("wp.t")

    def is_wordpress_plugin(self):
        return self.app.startswith("wp.p")

    # same for joomla, drupal, ...
    def is_wordpress(self):
        return self.app == "wordpress-cores"

    def __str__(self):
        return 'AppVersion(app=%s, version=%s)' % (self.app, self.version)


class AppVersionEntry:
    # if some app-versions have same list of checksums on avtest.corp, then they all are listed in :av
    av: List[AppVersion]
    impl: List[int]
    total: int

    def __init__(self, json_node):
        self.av = [AppVersion(x) for x in json_node["av"]]
        self.impl = json_node["impl"]
        self.total = json_node["total"]


class WebdetectLevelDb:

    def __init__(self, path_to_db: str):
        self.db = plyvel.DB(path_to_db)

    def get_by_key(self, key: bytes) -> Optional[bytes]:
        return self.db.get(key)

    # checksums are valued with an array of 32-bit integers; format:
    # [app-version id detected by this checksum, ...app-versions on which checksum 'depends-on']
    @staticmethod
    def parse_checksum_value(value: bytes) -> Tuple[bytes, List[bytes]]:
        if len(value) % 4 != 0 or len(value) < 4:
            raise Exception("db is invalid: invalid value size")
        ids = []
        for i in range(0, len(value), 4):
            ids.append(value[i:(i + 4)])
        return ids[0], ids[1:]

    # app-version ids are valued with string containing AppVersionEntry in json
    @staticmethod
    def parse_app_version_value(value: bytes) -> AppVersionEntry:
        parsed = json.loads(value.decode("utf-8"))
        return AppVersionEntry(parsed)


class WebdetectClient:
    avs_having_enough_checksums: Set[bytes]
    memoized_is_valid_cache: Dict[bytes, bool]
    matching_result: Set[bytes]

    def __init__(self,
                 get_by_key: Callable[[bytes], Optional[bytes]],
                 parse_checksum_value: Callable[[bytes], Tuple[bytes, List[bytes]]],
                 parse_app_version_value: Callable[[bytes], AppVersionEntry],
                 local_checksums: List[bytes],
                 checksums_bound: float):
        self.checksums_bound = checksums_bound
        self.memoized_is_valid_cache = {}

        self.found_avs: Dict[bytes, Set[bytes]] = {}
        self.depends_on_cache: Dict[bytes, List[bytes]] = {}
        self.checksums_cache: Dict[bytes, Tuple[bytes, List[bytes]]] = {}
        self.app_versions_cache: Dict[bytes, AppVersionEntry] = {}

        for cs in local_checksums:
            cs_entry = get_by_key(cs)
            if cs_entry is None:
                continue
            av, depends_on = parse_checksum_value(cs_entry)
            self.found_avs.setdefault(av, set()).add(cs)
            self.checksums_cache[cs] = (av, depends_on)
            self.depends_on_cache[av] = depends_on
            av_entry = get_by_key(av)
            if av_entry is None:
                raise Exception("db is invalid: app-version cannot be found")
            self.app_versions_cache[av] = parse_app_version_value(av_entry)

    def process(self) -> List[List[AppVersion]]:
        self.avs_having_enough_checksums = \
            set(x for x in self.found_avs.keys() if self.has_enough_checksums(x))
        self.matching_result = set(x for x in self.avs_having_enough_checksums if self.is_valid_by_depends_on(x))
        for impl in self.find_by_implies():
            self.matching_result.add(impl)
        return [self.app_versions_cache[av].av for av in self.matching_result]

    def has_enough_checksums(self, av: bytes) -> bool:
        return av in self.found_avs and \
               float(len(self.found_avs[av])) / self.app_versions_cache[av].total >= self.checksums_bound

    def is_valid_by_depends_on(self, av: bytes) -> bool:
        if av in self.memoized_is_valid_cache:
            return self.memoized_is_valid_cache[av]
        else:
            if av in self.avs_having_enough_checksums:
                result = any(
                    all(not self.is_valid_by_depends_on(dependent_av) for dependent_av in self.checksums_cache[cs][1])
                    for cs in self.found_avs[av])
            else:
                result = False
            self.memoized_is_valid_cache[av] = result
            return result

    def find_by_implies(self):
        implies = set()
        for av_key in self.found_avs.keys():
            av = self.app_versions_cache[av_key]
            for impl in av.impl:
                implies.add(struct.pack('>i', impl))
        return [x for x in implies
                if x in self.found_avs and not self.is_valid_by_depends_on(x) and self.has_enough_checksums(x)]


def lookup(path_to_webdetect_leveldb: str,
           path_to_rapiddb_leveldb: str):
    rapiddb_leveldb = plyvel.DB(path_to_rapiddb_leveldb)
    webdetect_leveldb = WebdetectLevelDb(path_to_webdetect_leveldb)
    result = WebdetectClient(
        get_by_key=webdetect_leveldb.get_by_key,
        parse_checksum_value=webdetect_leveldb.parse_checksum_value,
        parse_app_version_value=webdetect_leveldb.parse_app_version_value,
        local_checksums=[v[9:][:32] for (_, v) in rapiddb_leveldb],
        checksums_bound=0.5
    ).process()
    webdetect_leveldb.db.close()
    rapiddb_leveldb.close()
    return result


if __name__ == '__main__':
    # list of all found AppVersions
    all_detected_app_versions = lookup(
        path_to_webdetect_leveldb=sys.argv[1],
        path_to_rapiddb_leveldb=sys.argv[2]
    )

    # list of all distinct apps
    all_detected_apps = set()
    for avs in all_detected_app_versions:
        for av in avs:
            all_detected_apps.add(av.app)
