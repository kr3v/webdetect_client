import hashlib
import os
import sys

BLOCK_SIZE = 65536


def scan_for_cs(path):
    for root, dirs, files in os.walk(path):
        for file_name in files:
            try:
                path = os.path.join(root, file_name)
                hsh = evaluate_hash(path)
                print('%s\t%s' % (hsh.digest().hex(), path))
            except Exception as e:
                print(e)
                raise e


def evaluate_hash(path):
    return hashlib.sha256(open(path, 'rb').read())


if __name__ == '__main__':
    scan_for_cs(sys.argv[1])
