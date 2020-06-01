import os
import struct
import sys
from typing import List, Callable, Set, Dict, Tuple, Optional

import plyvel

OTHER_APPS_TAG = 'other_apps'
TAGS_MAP = {
    'wordpress-cores': 'wp_core',
    'drupal-cores': 'drupal_core',
    'joomla-cores': 'joomla_core'
}


def remove_prefix(string, prefix):
    return string[len(prefix):] if string.startswith(prefix) else string


def app_as_tag(app: str) -> Optional[str]:
    if app.startswith("wp.p"):
        return 'wp_plugin_' + remove_prefix(app, 'wp.p').replace('-', '_')
    if app.startswith("wp.t"):
        return 'wp_theme_' + remove_prefix(app, 'wp.t').replace('-', '_')
    if app.endswith('-cores'):
        if app in TAGS_MAP:
            return TAGS_MAP[app]
        else:
            return OTHER_APPS_TAG


class AppVersion:
    app: str
    version: str

    def __init__(self, app: str, version: str):
        self.app = app
        self.version = version

    def is_wordpress_theme(self):
        return self.app.startswith("wp.t")

    def is_wordpress_plugin(self):
        return self.app.startswith("wp.p")

    # same for joomla, drupal, ...
    def is_wordpress(self):
        return self.app == "wordpress-cores"

    def is_core(self):
        return self.app.endswith("-cores")

    def __str__(self):
        return '%s %s' % (self.app, self.version)

    def __repr__(self):
        return str(self)


class AppVersionEntry:
    # if some app-versions have same list of checksums, then they all are listed in :av
    av: List[AppVersion]
    # checksums used to detect this app-versions
    used_cs: List[bytes]
    # which app-version ids this app-version 'implies'
    impl: List[bytes]
    # total count of checksums
    total: int

    def __init__(self, av: List[AppVersion], impl: List[bytes], total: int):
        self.av = av
        self.impl = impl
        self.total = total

    def __str__(self):
        if len(self.av) == 1:
            return str(self.av[0])
        else:
            return str(self.av)

    def __repr__(self):
        return str(self)


AVE_Path = Tuple[AppVersionEntry, str]
BARRIER_BYTE = struct.pack('b', -1)
BARRIER_SIGNED = -1
BARRIER_UNSIGNED = 255


class WebdetectLevelDb:

    def __init__(self, path_to_db: str):
        self.db = plyvel.DB(path_to_db)

    def get_by_key(self, key: bytes) -> Optional[bytes]:
        return self.db.get(key)

    # checksums are valued with an array of 32-bit integers; format:
    # [app-version id for this checksum, ...app-version ids on which checksum depends-on, BARRIER_BYTE, ...depth levels]
    @staticmethod
    def parse_checksum_value(value: bytes) -> Tuple[bytes, List[bytes], bytes]:
        ids = list()
        barrier = None
        for i in range(0, len(value), 4):
            if value[i] == BARRIER_UNSIGNED or value[i] == BARRIER_SIGNED:
                barrier = i
                break
        if barrier is None:
            raise Exception("db is invalid")
        for i in range(0, barrier, 4):
            ids.append(value[i:(i + 4)])
        return ids[0], ids[1:], value[barrier + 1:]

    # [[...<app name>\0<version name>\0]\0<1-byte 'total'>[...<4-byte implies>]
    # detailed:
    # - app-version value is list of 2n 0-terminated strings; (2i-1, 2i) strings form (app, version), i=1,n
    #   - this list itself is 0-terminated, i.e. there are two \0 at end of list (from version string and from list)
    #   - strings are utf-8
    # - 1-byte total (contains count of checksums which represent given app-version within current DB)
    # - list of 4-byte integers containing list of implied app-version ids
    @staticmethod
    def parse_app_version_value(value: bytes) -> AppVersionEntry:
        def zero_terminations():
            indices: List[int] = []
            list_end_index = None
            prev_byte = -1
            for idx in range(len(value)):
                byte = value[idx]
                if byte == 0:
                    if prev_byte == byte:
                        list_end_index = idx
                        break
                    indices.append(idx)
                prev_byte = byte
            if list_end_index is None:
                raise Exception("db is invalid")
            return indices, list_end_index

        def parse_app_versions(indices: List[int]) -> List[AppVersion]:
            strings: List[str] = []
            previous_index = 0
            for index in indices:
                strings.append(value[previous_index:index].decode("utf8"))
                previous_index = index + 1
            if len(strings) % 2 != 0:
                raise Exception("db is invalid")
            app_versions = []
            for index in range(0, len(strings), 2):
                app_versions.append(AppVersion(strings[index], strings[index + 1]))
            return app_versions

        zeros_indices, list_end_idx = zero_terminations()
        avs = parse_app_versions(zeros_indices)
        total: int = value[list_end_idx + 1]
        impl: List[bytes] = []
        for i in range(list_end_idx + 2, len(value), 4):
            impl.append(value[i:(i + 4)])

        return AppVersionEntry(avs, impl, total)


WP_CONTENT_DIR = 'wp-content'
WP_PLUGINS_DIR = 'plugins'
WP_THEMES_DIR = 'themes'


class WebdetectClient:
    avs_having_enough_checksums: Set[bytes]
    memoized_is_valid_cache: Dict[bytes, bool]
    matching_result: Set[bytes]

    found_avs: Dict[bytes, Set[bytes]]
    checksums_cache: Dict[bytes, Tuple[bytes, List[bytes], List[bytes]]]
    app_versions_cache: Dict[bytes, AppVersionEntry]
    checksum_to_ldb_key: Dict[bytes, bytes]

    def __init__(self,
                 get_by_key: Callable[[bytes], Optional[bytes]],
                 parse_checksum_value: Callable[[bytes], Tuple[bytes, List[bytes], bytes]],
                 parse_app_version_value: Callable[[bytes], AppVersionEntry],
                 local_checksums: List[Tuple[bytes, bytes]],
                 checksums_bound: float):
        self.checksums_bound = checksums_bound
        self.memoized_is_valid_cache = {}
        self.checksum_to_ldb_key = {}

        self.found_avs: Dict[bytes, Set[bytes]] = {}
        self.checksums_cache: Dict[bytes, Tuple[bytes, List[bytes], bytes]] = {}
        self.app_versions_cache: Dict[bytes, AppVersionEntry] = {}

        for (cs_key, cs) in local_checksums:
            cs_entry = get_by_key(cs)
            if cs_entry is None:
                continue
            self.checksum_to_ldb_key[cs] = cs_key
            av, cs_do, depths = parse_checksum_value(cs_entry)
            self.checksums_cache[cs] = (av, cs_do, depths)
            self.found_avs.setdefault(av, set()).add(cs)
            if av not in self.app_versions_cache:
                av_entry = get_by_key(av)
                if av_entry is None:
                    raise Exception("db is invalid: app-version cannot be found")
                self.app_versions_cache[av] = parse_app_version_value(av_entry)

    def process(self) -> List[AppVersionEntry]:
        self.avs_having_enough_checksums = \
            set(x for x in self.found_avs.keys() if self.has_enough_checksums(x))
        self.matching_result = set(x for x in self.avs_having_enough_checksums if self.is_valid_by_depends_on(x))
        for impl in self.find_by_implies():
            self.matching_result.add(impl)
        for av in self.matching_result:
            self.app_versions_cache[av].used_cs = self.found_avs[av]
        return [self.app_versions_cache[av] for av in self.matching_result]

    # private
    def has_enough_checksums(self, av: bytes) -> bool:
        return av in self.found_avs and \
               float(len(self.found_avs[av])) / self.app_versions_cache[av].total >= self.checksums_bound

    # private
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

    # private
    def find_by_implies(self):
        implies = set()
        for av_key in self.found_avs.keys():
            av = self.app_versions_cache[av_key]
            for impl in av.impl:
                implies.add(impl)
        return [x for x in implies
                if x in self.found_avs and not self.is_valid_by_depends_on(x) and self.has_enough_checksums(x)]

    # return path that is most likely to be path of app-version detected via [cs_with_paths]
    def find_path(self, cs_with_paths: List[Tuple[bytes, List[str]]]):
        def remove_depth(pth: str, dpth: int):
            while dpth > 0:
                dpth -= 1
                pth = os.path.split(pth)[0]
            return pth

        possible = {}
        for cs, paths in cs_with_paths:
            _, _, depths = self.checksums_cache[cs]
            for depth in depths:
                for path in paths:
                    kk = remove_depth(path, int(depth))
                    before = possible.setdefault(kk, 0)
                    possible[kk] = before + 1

        max_matches = max(possible.values())
        paths_with_max_matches = [x[0] for x in filter(lambda a: a[1] == max_matches, possible.items())]
        return paths_with_max_matches

    @staticmethod
    def find_structure(found: List[AVE_Path]) -> Dict[AVE_Path, List[AVE_Path]]:
        wp_cores = [x for x in found if any(y.is_wordpress() for y in x[0].av)]
        inclusions: Dict[AVE_Path, List[AVE_Path]] = {}
        for wp_plugin in [x for x in found if any(y.is_wordpress_plugin() for y in x[0].av)]:
            key = WebdetectClient.find_parent_for_wp_plugin_or_theme(wp_cores, wp_plugin, WP_PLUGINS_DIR)
            if key is not None:
                inclusions.setdefault(key, list()).append(wp_plugin)
        for wp_theme in [x for x in found if any(y.is_wordpress_theme() for y in x[0].av)]:
            key = WebdetectClient.find_parent_for_wp_plugin_or_theme(wp_cores, wp_theme, WP_THEMES_DIR)
            if key is not None:
                inclusions.setdefault(key, list()).append(wp_theme)
        for app in [x for x in found if any(y.is_core() for y in x[0].av)]:
            inclusions.setdefault(app, list())
        return inclusions

    # private
    @staticmethod
    def find_parent_for_wp_plugin_or_theme(cores: List[AVE_Path], app: AVE_Path, type: str) -> Optional[AVE_Path]:
        def is_core_for_app(app_path, core_path):
            path = app_path
            dirs = []
            for i in range(3):
                path, split = os.path.split(path)
                dirs.append(split)
            return path == core_path and dirs[2] == WP_CONTENT_DIR and dirs[1] == type

        _, app_path = app
        max_core = None
        max_core_path = None
        max_core_path_match = -1
        for core, core_path in cores:
            common = os.path.commonpath([core_path, app_path])
            if len(common) > max_core_path_match and common == core_path and is_core_for_app(app_path, core_path):
                max_core_path_match = len(common)
                max_core = core
                max_core_path = core_path
        if max_core is None:
            return None
        return max_core, max_core_path


def layered_avs_to_layered_tags(layered_found_avs):
    tags_to_paths: Dict[Tuple[str, str], Set[Tuple[str, str]]] = {}
    for (core_app, core_path), children in layered_found_avs.items():
        for av in core_app.av:
            av_tag_path = (app_as_tag(av.app), core_path)
            tags_to_paths.setdefault(av_tag_path, set())
            for (children_app, children_path) in children:
                for child_av in children_app.av:
                    child_av_tag_path = (app_as_tag(child_av.app), children_path)
                    tags_to_paths.setdefault(av_tag_path, set()).add(child_av_tag_path)
    return tags_to_paths


def webdetect(path_to_webdetect_leveldb: str,
              path_to_rapidscan_leveldb: str):
    rapidscan_leveldb = plyvel.DB(path_to_rapidscan_leveldb)
    webdetect_leveldb = WebdetectLevelDb(path_to_webdetect_leveldb)
    try:
        client = WebdetectClient(get_by_key=webdetect_leveldb.get_by_key,
                                 parse_checksum_value=webdetect_leveldb.parse_checksum_value,
                                 parse_app_version_value=webdetect_leveldb.parse_app_version_value,
                                 local_checksums=[(k, v[9:][:32]) for (k, v) in rapidscan_leveldb],
                                 checksums_bound=0.5)
        result = client.process()
    finally:
        webdetect_leveldb.db.close()
        rapidscan_leveldb.close()
    return result, client


def rapidscan_db_to_tags_with_paths():
    # performing app versions detection, filtering usable checksums
    all_detected_app_versions, wc = webdetect(
        path_to_webdetect_leveldb=sys.argv[1],
        path_to_rapidscan_leveldb=sys.argv[2]
    )

    # creating a dictionary from used checksums to their app versions
    # used to find app versions for checksums after path lookup
    cs_to_av: Dict[bytes, AppVersionEntry] = {}
    for av in all_detected_app_versions:
        for cs in av.used_cs:
            cs_to_av[cs] = av

    # Each checksum from [cs_to_av] should be mapped with paths where it is present.
    # [WebdetectClient.checksum_to_ldb_key] contains reversed rapidscan leveldb entry
    # (as [AppVersionEntry.used_cs] keeps values), so, by knowing which structure rapidscan leveldb key has,
    # path lookup is expected to be simpler than evaluating SHA-256 hashes again
    # results should be stored here (list of tuples (checksum, list of paths))
    cs_to_paths: List[Tuple[bytes, List[str]]]

    # matching checksums to their app-versions again using [cs_to_av]
    av_to_cs_with_paths: Dict[AppVersionEntry, List[Tuple[bytes, List[str]]]] = {}
    for (cs, paths) in av_to_cs_with_paths.items():
        av_to_cs_with_paths.setdefault(cs_to_av[cs], list()).append((cs, paths))

    # by paths from checksums, deducing path for their app-version
    av_to_paths: List[AVE_Path] = list()
    for av, cs_with_paths in av_to_cs_with_paths.items():
        paths_to_av = wc.find_path(cs_with_paths)
        for path in paths_to_av:
            av_to_paths.append((av, path))

    # [WebdetectClient.find_structure] performs 'nesting' for WP plugins and themes (by looking for WP core for them)
    layered_found_avs = WebdetectClient.find_structure(av_to_paths)

    # transforming [layered_found_avs] into tags
    # Tuple[str, str] here is (tag, path)
    layered_tags_with_paths = layered_avs_to_layered_tags(layered_found_avs)
