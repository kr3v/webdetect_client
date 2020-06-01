import json


def do(path_to_db, check_sums, db_type):
    if db_type == 'leveldb':
        do_leveldb_impl(path_to_db, check_sums)
    elif db_type == 'json':
        do_json_impl(path_to_db, check_sums)
    else:
        raise NotImplementedError("unknown db type %s" % db_type)


def do_json_impl(path_to_db, check_sums):
    with open(path_to_db, 'r') as db_file:
        db = json.load(db_file)

    def get_entry(key):
        try:
            if type(key) is str:
                return db[key[:64]]
            else:
                return db[key.hexdigest()]
        except KeyError:
            return None

    def format_entry(key):
        e = db[str(key)]
        return [av["app"] + ":" + av["version"] for av in e["av"]]

    def parse_entry(cs, entry):
        return entry[0], entry[1:]

    return do_impl(check_sums, get_entry, format_entry, parse_entry)


def do_leveldb_impl(path_to_db, check_sums):
    import plyvel
    db = plyvel.DB(path_to_db)

    def get_entry(key):
        return db.get(key.digest())

    def format_entry(key):
        return str([k["app"] + ":" + k["version"] for k in json.loads(db.get(key).decode("utf-8"))["av"]])

    def parse_entry(cs, entry):
        if len(entry) % 4 != 0:
            raise Warning("Not array of integers? %s" % cs.hexdigest())
        if len(entry) < 4:
            raise Warning("There always should be one integer in entry. %s" % cs.hexdigest())
        ids = []
        for i in range(0, len(entry), 4):
            ids.append(entry[i:(i + 4)])
        return ids[0], ids[1:]

    return do_impl(check_sums, get_entry, format_entry, parse_entry)


def do_impl(check_sums, get_entry, format_entry, parse_entry):
    matched_avs = {}
    dependencies = {}
    implied = {}

    files_found_log = []
    discarded_log = []
    av_found_log = []
    implied_log = []

    for (local_cs_sha256, path) in check_sums:
        entry = get_entry(local_cs_sha256)
        if entry is None:
            continue
        found_av, found_deps = parse_entry(local_cs_sha256, entry)

        matched_avs[found_av] = matched_avs.setdefault(found_av, 0) + 1
        deps = dependencies.setdefault(found_av, set())
        for dep in found_deps:
            deps.add(dep)

        files_found_log.append(
            'path: %s\nav: %s\ndeps: %s' % (path, format_entry(found_av), [format_entry(x) for x in found_deps]))

    for (av, cnt) in matched_avs.items():
        t = get_entry(str(av))
        total = t["total"]
        coeff = float(cnt) / float(t["total"])

        if any([dep in matched_avs for dep in dependencies[av]]):
            discarded_log.append('%s discarded, as it depends on AV, which is also present; %d/%d = %f' % (
                format_entry(av), cnt, total, coeff))
            continue
        if coeff < 0.5:
            discarded_log.append(
                "%s discarded, as it does not pass coeff filter; %d/%d = %f" % (format_entry(av), cnt, total, coeff))
            continue

        av_found_log.append('%s found! %d/%d = %f' % (format_entry(av), cnt, total, coeff))
        for i in t["impl"]:
            if i in matched_avs:
                implied.setdefault(i, set()).add(av)

    for (av, v) in implied.items():
        t = get_entry(str(av))
        total = t["total"]
        coeff = float(cnt) / float(t["total"])
        if coeff < 0.5:
            discarded_log.append("%s implication discarded, as it does not pass coeff filter; %d/%d = %f" % (
                format_entry(av), cnt, total, coeff))
        else:
            implied_log.append(
                '%s implied by %s! %d/%d = %f' % (format_entry(av), [format_entry(x) for x in v], cnt, total, coeff))

    print()
    print("Found files:")
    for msg in sorted(files_found_log):
        print(msg)
    print()
    print("Discarded app versions:")
    for msg in sorted(discarded_log):
        print(msg)
    print()
    print("Found app versions:")
    for msg in sorted(av_found_log):
        print(msg)
    print()
    print("Implied app versions:")
    for msg in sorted(implied_log):
        print(msg)


def main():
    import sys
    sha_list_file_path = sys.argv[1]
    path_to_db = sys.argv[2]
    db_type = sys.argv[3]
    print(sys.argv)
    with open(sha_list_file_path) as sha_list_file:
        lines = sha_list_file.readlines()
        do(path_to_db, [(x.rstrip('\n'), x.rstrip('\n')) for x in lines], db_type)


if __name__ == '__main__':
    main()
