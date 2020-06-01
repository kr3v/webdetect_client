import json
import sys
from typing import Optional, Tuple, List, Dict

from webdetect import AppVersionEntry, WebdetectClient, WebdetectLevelDb


class WebdetectJsonDb:
    # impl for JSON DB version for local debugging

    def __init__(self, path_to_db: str):
        with open(path_to_db, mode='r') as file_db:
            self.db = json.load(file_db)

    def get_by_key(self, key: bytes) -> Optional[bytes]:
        k = str(key)
        if k in self.db:
            return self.db[k]
        else:
            return None

    # checksums are valued with an array of 32-bit integers; format:
    # [app-version id for this checksum, ...app-versions on which checksum 'depends-on', barrier, ...depth levels]
    # noinspection PyTypeChecker
    @staticmethod
    def parse_checksum_value(value: bytes) -> Tuple[bytes, List[bytes], List[bytes]]:
        barrier = value.index(-1)
        return value[0], value[1:barrier], value[barrier + 1:]

    # app-version ids are valued with string containing AppVersionEntry in json q
    @staticmethod
    def parse_app_version_value(value: bytes) -> AppVersionEntry:
        parsed = value
        return AppVersionEntry(parsed)


def lookup_json(path_to_webdetect_leveldb: str, checksums: Dict[str, List[str]]):
    wd_db = WebdetectLevelDb(path_to_webdetect_leveldb)
    wc = WebdetectClient(get_by_key=wd_db.get_by_key,
                         parse_checksum_value=wd_db.parse_checksum_value,
                         parse_app_version_value=wd_db.parse_app_version_value,
                         local_checksums=[(None, bytes.fromhex(x)) for x in checksums.keys()],
                         checksums_bound=0.5)

    result: List[AppVersionEntry] = wc.process()

    to_be_layered = []
    for av in result:
        used_checksums = [(x, checksums[x.hex()]) for x in av.used_cs]
        # print(av)
        # for (cs, path) in used_checksums:
        #     print("\t%s\t%s" % (cs.hex(), path))
        paths = wc.find_path(used_checksums)
        for path in paths:
            to_be_layered.append((av, path))

    structure = WebdetectClient.find_structure(to_be_layered)
    for (av, path), children in structure.items():
        print("%s at %s" % (av, path))
        for (dep_av, dep_path) in children:
            print("\t%s at %s" % (dep_av, dep_path))


"""
sys.argv[1] format is (<sha256 checksum>\t<path to file>\n)+ 
"""
if __name__ == '__main__':
    # print(sys.argv[1])
    css: Dict[str, List[str]] = {}
    with open(sys.argv[1], mode='rb') as db:
        for line in db:
            values = [x for x in line.split(b'\t') if len(x) > 0]
            if len(values) == 2:
                (k, v) = values
                css.setdefault(k.decode("utf-8"), list()).append(v.rstrip(b'\n').decode("utf-8", errors="ignore"))

    lookup_json(
        path_to_webdetect_leveldb=sys.argv[2],
        checksums=css
    )
    # print()
