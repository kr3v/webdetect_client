from __future__ import annotations

from collections import deque
from typing import Tuple, Dict, Set, List, Deque

SUFFICIENT_CHECK_SUMS = 2


class AppVersion:
    key: Tuple[str, str]
    value: Set[Checksum]
    exclusive_check_sums: int

    def __init__(self, key: Tuple[str, str], value: Set[Checksum]):
        self.key = key
        self.value = value
        self.exclusive_check_sums = 0

    def __hash__(self):
        return hash(self.key)

    def __eq__(self, other: AppVersion):
        return isinstance(other, AppVersion) and self.key == other.key

    # can be cached with visitors
    def calc_exclusive_check_sums(self):
        own_check_sums = 0
        for checksum in self.value:
            if len(checksum.value) == 1:
                own_check_sums += 1
        self.exclusive_check_sums = own_check_sums

    def is_defined(self) -> bool:
        return self.exclusive_check_sums >= SUFFICIENT_CHECK_SUMS

    def remove_non_exclusive_check_sums(self) -> List[Checksum]:
        removed_check_sums: List[Checksum] = []
        for check_sum in self.value:
            if len(check_sum.value) > 1:
                check_sum.value.remove(self)
                removed_check_sums.append(check_sum)
                if len(check_sum.value) is 1:
                    for app_version in check_sum.value:
                        app_version.exclusive_check_sums += 1

        for check_sum in removed_check_sums:
            self.value.remove(check_sum)
        return removed_check_sums

    def __str__(self) -> str:
        return str(self.key)


class Checksum:
    key: str
    value: Set[AppVersion]

    def __init__(self, key: str, value: Set[AppVersion]):
        self.key = key
        self.value = value

    def __hash__(self):
        return hash(self.key)

    def __eq__(self, other: Checksum):
        return isinstance(other, Checksum) and self.key == other.key

    def __str__(self) -> str:
        return str(self.key)


def verify_consistency(check_sums: Dict[str, Checksum], app_versions: Dict[Tuple[str, str], AppVersion]):
    for cs in check_sums.values():
        for av in cs.value:
            if not (cs in av.value):
                raise Exception(str(cs) + " <-> " + str(av))

    for av in app_versions.values():
        for cs in av.value:
            if not (av in cs.value):
                raise Exception(str(cs) + " <-> " + str(av))


def almost_same(av1: AppVersion, av2: AppVersion):
    return len(av1.value.difference(av2.value)) <= SUFFICIENT_CHECK_SUMS


def process(checksum_to_app_version: Dict[str, Set[Tuple[str, str]]],
            app_version_to_checksum: Dict[Tuple[str, str], Set[str]]):
    check_sums: Dict[str, Checksum] = {}
    app_versions: Dict[Tuple[str, str], AppVersion] = {}

    for app_version_tuple, _ in app_version_to_checksum.items():
        app_versions[app_version_tuple] = AppVersion(app_version_tuple, set())

    for checksum_str, app_versions_tuples in checksum_to_app_version.items():
        check_sum = Checksum(checksum_str, set())
        check_sums[checksum_str] = check_sum
        for app_version_tuple in app_versions_tuples:
            app_version = app_versions[app_version_tuple]
            check_sum.value.add(app_version)
            app_version.value.add(check_sum)

    verify_consistency(check_sums, app_versions)

    bfs_queue: Deque[AppVersion] = deque()
    for app_version in app_versions.values():
        app_version.calc_exclusive_check_sums()
        if app_version.is_defined():
            bfs_queue.append(app_version)

    well_defined_app_versions: Set[AppVersion] = set()
    while len(bfs_queue) > 0:
        app_version = bfs_queue.popleft()

        if not (app_version in well_defined_app_versions) and app_version.is_defined():
            well_defined_app_versions.add(app_version)
            for checksum in app_version.remove_non_exclusive_check_sums():
                for app_version_to_be_checked in checksum.value:
                    bfs_queue.append(app_version_to_be_checked)

    verify_consistency(check_sums, app_versions)

    for app_version in sorted(well_defined_app_versions, key=lambda a: a.key):
        print(app_version)

    print('#######################################')
    print('#######################################')

    for app_version in app_versions.values():
        if not (app_version in well_defined_app_versions):
            print(app_version)
