import hashlib
import os

BLOCK_SIZE = 65536


def scan_for_cs(path):
    pq = set()
    for root, dirs, files in os.walk(path):
        for file_name in files:
            try:
                path = os.path.join(root, file_name)
                hsh = evaluate_hash(path)
                print('%s -> %s' % (path, hsh))
                pq.add(hsh)
            except Exception as e:
                print(e)
                raise e
    return pq


def evaluate_hash(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()
