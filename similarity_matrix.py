from __future__ import annotations

import heapq
from collections import Iterator
from functools import total_ordering
from typing import Tuple, List

from sortedcontainers import SortedSet

from graph import AppVersion, Checksum


@total_ordering
class SequencedEntry(Iterator):
    current: Checksum
    entries: SortedSet[Checksum]
    current_set_index: int
    av_index: int

    def __init__(self, iterator: SortedSet[Checksum], idx: int):
        self.current = None
        self.entries = iterator
        self.index = idx
        self.current_set_index = 0

    def __next__(self) -> SequencedEntry:
        try:
            self.current = self.entries[self.current_set_index]
            self.current_set_index += 1
            return self
        except IndexError:
            raise StopIteration

    def __eq__(self, other: SequencedEntry):
        return self.current == other.current

    def __lt__(self, other: SequencedEntry):
        return self.current < other.current


def similarity_matrix(
        av_dict: List[Tuple[str, AppVersion]]
) -> List[List[int]]:
    matrix = [[0 for _ in range(0, len(av_dict))] for _ in range(0, len(av_dict))]

    pq: List[SequencedEntry] = []
    index = 0
    for (version, av) in av_dict:
        try:
            heapq.heappush(pq, next(SequencedEntry(av.value, index)))
        except StopIteration:
            pass
        index += 1

    while len(pq) > 0:
        current: SequencedEntry = heapq.heappop(pq)
        same_entries = [current]
        while len(pq) > 0 and pq[0] == current:
            same: SequencedEntry = heapq.heappop(pq)
            same_entries.append(same)
        for entry_i in same_entries:
            for entry_j in same_entries:
                matrix[entry_i.index][entry_j.index] += 1
            try:
                heapq.heappush(pq, next(entry_i))
            except StopIteration:
                pass
    return matrix
