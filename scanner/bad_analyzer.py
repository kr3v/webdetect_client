import os
import sys

COMMON_MARKERS_OF_BAD_DIRS = {"branches", "tags"}


def is_bad(path, versions):
    dirs = set([x for (x, _) in list_directories(path)])
    if dirs.intersection(COMMON_MARKERS_OF_BAD_DIRS) == COMMON_MARKERS_OF_BAD_DIRS:
        return True
    else:
        for d in dirs:
            if d in versions:
                return True
    return False


def list_directories(path):
    return [(x, os.path.join(path, x)) for x in os.listdir(path) if os.path.isdir(os.path.join(path, x))]


def scan(path):
    idx = 0
    for (_, app_path) in list_directories(path):

        if idx % 100 == 0:
            print(idx, file=sys.stderr)
        idx += 1

        trunk_path = os.path.join(app_path, 'trunk')
        tags_path = os.path.join(app_path, 'tags')

        versions = set()
        if os.path.isdir(trunk_path):
            versions.add("trunk")
        if os.path.isdir(tags_path):
            for (version, _) in list_directories(tags_path):
                versions.add(version)

        if os.path.isdir(trunk_path):
            if is_bad(trunk_path, versions):
                print(trunk_path)
        if os.path.isdir(tags_path):
            for (_, version_path) in list_directories(tags_path):
                if is_bad(version_path, versions):
                    print(version_path)


if __name__ == '__main__':
    scan(sys.argv[1])
