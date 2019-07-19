import sys

from path_scanner import scan_for_cs
from webdetect import do


def main():
    if len(sys.argv) < 4:
        print(
            "main.py: path db db_type\n  path - path to be scanned\n  db - path to db \n  db_type - 'leveldb' or 'json'",
            file=sys.stderr
        )
        exit(-1)
    else:
        path = sys.argv[1]
        db = sys.argv[2]
        dbtype = sys.argv[3]
    print("Walking through %s" % path)

    with open('%s/sha.list.out' % path, 'w') as t:
        check_sums = scan_for_cs(path)
        for (cs, path) in check_sums:
            t.write('%s\t%s\n' % (cs.hexdigest(), path))

    do(db, check_sums, dbtype)


if __name__ == '__main__':
    main()
