#!/usr/bin/python
from __future__ import print_function

"""
This script collects all checksums and their paths for given directory.

It's supposed to be run client's server, so there are commented sections to ensure that this script starts
only on selected time and runs only if LA is higher than some constant.
"""

import datetime
import hashlib
import os
import sys
import time
import traceback

BLOCK_SIZE = 4 * (2 ** 10)
# HOUR_TO_START = 1
# LOAD_AVERAGE_MAXIMUM = 15


def scan_for_cs(path):
    for root, dirs, files in os.walk(path):
        for file_name in files:
            # try:
            #     while os.getloadavg()[0] >= LOAD_AVERAGE_MAXIMUM:
            #         print("%s load average > 15: %s" % (str(datetime.datetime.now()), str(os.getloadavg())),
            #               file=sys.stderr)
            #         time.sleep(60)
            # except:
            #     pass
            try:
                path = os.path.join(root, file_name)
                hsh = evaluate_hash(path)
                print('%s\t%s' % (hsh, path))
            except:
                print(datetime.datetime.utcnow())
                for e in sys.exc_info():
                    print(e, file=sys.stderr)
                traceback.print_exc(file=sys.stderr)
                sys.stderr.flush()


def evaluate_hash(path):
    sha256_hash = hashlib.sha256()
    with open(path, 'rb') as f:
        for byte_block in iter(lambda: f.read(BLOCK_SIZE), b""):
            sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()


if __name__ == '__main__':
    # while not datetime.datetime.now().hour == HOUR_TO_START:
    #     print("time().hour != 1: %s" % str(datetime.datetime.now()), file=sys.stderr)
    #     time.sleep(60)
    scan_for_cs(sys.argv[1])
