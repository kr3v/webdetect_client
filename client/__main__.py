import sys

import webdetect
from path_scanner import scan_for_cs


def main():
    if len(sys.argv) < 3:
        print('Webdetect requires path to scan and path to db.json as parameters')
        raise FileNotFoundError
    else:
        path = sys.argv[1]
        db = sys.argv[2]
    print("Walking through %s" % path)

    check_sums = scan_for_cs(path)
    webdetect.do(db, check_sums)


if __name__ == '__main__':
    main()
