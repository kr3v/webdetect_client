from __future__ import annotations

from typing import Tuple, Dict, Set, List

from graph import create_graph_light, find_defined_av_dict, AppVersion, SUFFICIENT_CHECK_SUMS
from path_scanner import scan_csv_light


def debug_print(
        av_dict: Dict[Tuple[str, str], AppVersion], well_defined_av_dict: Dict[Tuple[str, str], AppVersion]
) -> None:
    for av in sorted(well_defined_av_dict.values(), key=lambda a: a.key):
        versions = set()
        for (key, value) in av.depends_on.items():
            for parent_av in value:
                versions.add(parent_av.key[1])
        print(av, '\t', sorted(versions))
    print('#######################################')
    for av in av_dict.values():
        if not (av in well_defined_av_dict):
            print(av)


def debug_print_matrix(app, matrix, versions):
    print(app)
    print('{:14.8}'.format(''), end='')
    for version in versions:
        print('{:>14.13}'.format('{:>7.7}'.format(version[0]) + ':' + str(len(version[1].value))), end='')
    print()
    idx = 0
    for (version) in versions:
        print('{:14.14}'.format(version[0]), end='')
        count = len(version[1].value)
        if count > 0:
            for value in matrix[idx]:
                if value > 0:
                    # print('{:14}'.formatvalue), end='')
                    print('{:14.3f}'.format(value / count), end='')
                else:
                    print('{:>14.14}'.format('0'), end='')
            print()
        else:
            print("<count = 0>")
        idx += 1
    print('##########')


def main():
    # verify_consistency(cs_dict, av_dict)
    cs_to_av, avs = scan_csv_light('wp.list')

    av_dict, cs_dict = create_graph_light(cs_to_av, avs)

    cs_to_av.clear()

    defined_av_dict: Dict[Tuple[str, str], AppVersion] = find_defined_av_dict(av_dict)

    for (k, v) in defined_av_dict.items():
        v

    # print("Solutions found")
    # verify_consistency(cs_dict, av_dict)

    # not_defined_av_dict: Dict[str, List[Tuple[str, AppVersion]]] = {}
    # for (key, value) in av_dict.items():
    #     if key not in defined_av_dict:
    #         app = key[0]
    #         version = key[1]
    #         not_defined_av_dict.setdefault(app, list()).append((version, value))
    #
    # not_defined_avs: Set[Tuple[str, str]] = set()
    # for key in av_dict.keys():
    #     if key not in defined_av_dict:
    #         not_defined_avs.add(key)

    # print('%d\t%d\t%d' % (SUFFICIENT_CHECK_SUMS, len(defined_av_dict), len(not_defined_avs)))

    # for (app, versions_unsorted) in not_defined_av_dict.items():
    #     versions = [x for x in versions_unsorted if len(x[1].value) > 0]
    #     matrix = similarity_matrix(versions)
    #     debug_print_matrix(app, matrix, versions)


if __name__ == '__main__':
    main()
