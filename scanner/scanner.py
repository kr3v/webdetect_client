#!/usr/bin/python
import csv
import os
import sys
from hashlib import sha256

idx = 1

IGNORED_DIRECTORIES = {'.git', '.svn'}


def walk(version_root, app, version):
    if type(version) == type(bytes):
        version = version.decode("utf8")
    if version in IGNORED_DIRECTORIES:
        return
    global idx
    print('av %d %s' % (idx, version_root), file=sys.stderr)
    idx += 1
    for root, d_names, f_names in os.walk(version_root):
        for ignored_directory in IGNORED_DIRECTORIES:
            if ignored_directory in d_names:
                d_names.remove(ignored_directory)
        for f in f_names:
            try:
                file_path = os.path.join(root, f)
                hsh = sha256(open(file_path, 'rb').read()).hexdigest()
                print('%s\t%s\t%s\t%s\t%s' % (
                app, version, hsh, file_path, remove_prefix(file_path, version_root).count('/')))
            except:
                print('err: %s' % str(sys.exc_info()), file=sys.stderr)


def remove_prefix(string, prefix):
    return string[len(prefix):] if string.startswith(prefix) else string


def subdirectories(path):
    return [(x, os.path.join(path, x)) for x in os.listdir(path) if os.path.isdir(os.path.join(path, x))]


def main(root, db):
    already_parsed_avs = set()
    if db is not None:
        with open(db, 'r') as db_file:
            for row in csv.reader(db_file, delimiter='\t'):
                already_parsed_avs.add((row[0], row[1]))

    def filtered_walk(vp, a, v):
        if not ((a, v) in already_parsed_avs):
            walk(vp, a, v)

    for (directory, path) in subdirectories(root):
        app = directory
        if app.endswith('-cores'):
            for (version, version_path) in subdirectories(path):
                filtered_walk(version_path, app, version)
        elif app.endswith('-themes'):
            for (app, app_path) in subdirectories(path):
                app = 'wp.t' + app
                for (version, version_path) in subdirectories(app_path):
                    filtered_walk(version_path, app, version)
        elif app.endswith('-plugins'):
            for (app, app_path) in subdirectories(path):
                app = 'wp.p' + app
                trunk_path = os.path.join(app_path, 'trunk')
                tags_path = os.path.join(app_path, 'tags')
                if os.path.isdir(trunk_path):
                    filtered_walk(trunk_path, app, 'trunk')
                if os.path.isdir(tags_path):
                    for (version, version_path) in subdirectories(tags_path):
                        filtered_walk(version_path, app, version)
        # local testing only branch!
        # else:
        #     for (version, version_path) in subdirectories(path):
        #         filtered_walk(version_path, app, version)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('scanner.py path_to_scan [already_scanned_av_csv]', file=sys.stderr)
    elif len(sys.argv) == 2:
        main(sys.argv[1], None)
    elif len(sys.argv) > 2:
        main(sys.argv[1], sys.argv[2])
