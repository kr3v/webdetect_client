from __future__ import annotations

from collections import deque
from functools import total_ordering
from typing import Tuple, Dict, Set, List, Deque

from sortedcontainers import SortedSet

SUFFICIENT_CHECK_SUMS = 3


class AppVersion:
    key: Tuple[str, str]
    value: SortedSet[Checksum]
    depends_on: Dict[Checksum, List[AppVersion]]
    exclusive_cs: int

    def __init__(self, key: Tuple[str, str], value: SortedSet[Checksum]):
        self.key = key
        self.value = value
        self.exclusive_cs = 0
        self.depends_on = dict()

    def __hash__(self):
        return hash(self.key)

    def __eq__(self, other: AppVersion):
        return self.key == other.key

    # can be cached with visitors
    def calc_exclusive_cs(self):
        own_cs_dict = 0
        for cs in self.value:
            if len(cs.value) == 1:
                own_cs_dict += 1
        self.exclusive_cs = own_cs_dict

    def is_defined(self) -> bool:
        return self.exclusive_cs >= SUFFICIENT_CHECK_SUMS

    def remove_non_exclusive_cs(self) -> List[Checksum]:
        removed_cs_dict: List[Checksum] = []
        for cs in self.value:
            if len(cs.value) > 1:
                cs.value.remove(self)
                removed_cs_dict.append(cs)
                for av in cs.value:
                    av.depends_on.setdefault(cs, list()).append(self)
                    if len(cs.value) == 1:
                        av.exclusive_cs += 1

        for cs in removed_cs_dict:
            self.value.remove(cs)
            try:
                del self.depends_on[cs]
            except KeyError:
                pass
        return removed_cs_dict

    def __str__(self) -> str:
        return str(self.key)


@total_ordering
class Checksum:
    key: str
    value: Set[AppVersion]

    def __init__(self, key: str, value: Set[AppVersion]):
        self.key = key
        self.value = value

    def __hash__(self):
        return hash(self.key)

    def __eq__(self, other: Checksum):
        return self.key == other.key

    def __lt__(self, other: Checksum):
        return self.key < other.key

    def __str__(self) -> str:
        return str(self.key)


def verify_consistency(cs_dict: Dict[str, Checksum], av_dict: Dict[Tuple[str, str], AppVersion]):
    for cs in cs_dict.values():
        for av in cs.value:
            if not (cs in av.value):
                raise Exception(str(cs) + " <-> " + str(av))

    for av in av_dict.values():
        if av.is_defined():
            for cs in av.value:
                if len(cs.value) != 1 and cs.value[0] != av:
                    raise Exception(str(cs) + " <-> " + str(av))

        for cs in av.value:
            if not (av in cs.value):
                raise Exception(str(cs) + " <-> " + str(av))


def create_graph(
        cs_to_av: Dict[str, Set[Tuple[str, str]]],
        av_to_cs: Dict[Tuple[str, str], Set[str]]
) -> Tuple[Dict[Tuple[str, str], AppVersion], Dict[str, Checksum]]:
    av_dict: Dict[Tuple[str, str], AppVersion] = {}
    for av_tuple, _ in av_to_cs.items():
        av_dict[av_tuple] = AppVersion(av_tuple, SortedSet())
    av_to_cs.clear()

    cs_dict: Dict[str, Checksum] = {}
    for cs_str, av_dict_tuples in cs_to_av.items():
        cs = Checksum(cs_str, set())
        cs_dict[cs_str] = cs
        for av_tuple in av_dict_tuples:
            av = av_dict[av_tuple]
            cs.value.add(av)
            av.value.add(cs)
    return av_dict, cs_dict


def create_graph_light(
        cs_to_av: Dict[str, Set[Tuple[str, str]]],
        avs: Set[Tuple[str, str]]
) -> Tuple[Dict[Tuple[str, str], AppVersion], Dict[str, Checksum]]:
    av_dict: Dict[Tuple[str, str], AppVersion] = {}
    for av_tuple in avs:
        av_dict[av_tuple] = AppVersion(av_tuple, SortedSet())
    avs.clear()

    cs_dict: Dict[str, Checksum] = {}
    for cs_str, av_dict_tuples in cs_to_av.items():
        cs = Checksum(cs_str, set())
        cs_dict[cs_str] = cs
        for av_tuple in av_dict_tuples:
            av = av_dict[av_tuple]
            cs.value.add(av)
            av.value.add(cs)
    return av_dict, cs_dict


def find_defined_av_dict(
        av_dict: Dict[Tuple[str, str], AppVersion]
) -> Dict[Tuple[str, str], AppVersion]:
    bfs_queue: Deque[AppVersion] = deque()
    for av in av_dict.values():
        av.calc_exclusive_cs()
        if av.is_defined():
            bfs_queue.append(av)

    well_defined_av_dict: Dict[Tuple[str, str], AppVersion] = {}
    while len(bfs_queue) > 0:
        av = bfs_queue.popleft()
        if not (av.key in well_defined_av_dict) and av.is_defined():
            well_defined_av_dict[av.key] = av
            for cs in av.remove_non_exclusive_cs():
                for av_to_be_checked in cs.value:
                    bfs_queue.append(av_to_be_checked)
    return well_defined_av_dict
