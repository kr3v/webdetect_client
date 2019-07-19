import json


def do(path_to_db, check_sums, db_type):
    if db_type == 'leveldb':
        do_leveldb_impl(path_to_db, check_sums)
    elif db_type == 'json':
        do_json_impl(path_to_db, check_sums)
    elif db_type == 'json_old':
        do_json_old_impl(path_to_db, check_sums)


def format_version(s):
    j = json.loads(s)
    if j["type"] == 'SINGLE':
        return j["app"] + ":" + j["version"]
    elif j["type"] == 'MERGED_WITHIN_SINGLE_APP':
        app = j["app"]
        return str(["%s:%s" % (app, x) for x in j["versions"]])
    else:
        return s


def do_json_impl(path_to_db, check_sums):
    with open(path_to_db, 'r') as db_file:
        db = json.load(db_file)

    def get_entry(key):
        # return format_version(json.dumps(db[str(key)]))
        return format_version(str(key))

    matched_avs = set()
    dependencies = {}

    msgs = []

    print()
    for (cs, path) in check_sums:
        cs = cs.hexdigest().rstrip('\n')
        if cs not in db:
            continue
        entry = db[cs]
        av = entry[0]
        matched_avs.add(av)
        deps = dependencies.setdefault(av, [])
        for dep in entry[1:]:
            deps.append(dep)
        m1 = 'path: %s\ncs: %s\nav: %s\ndeps: %s' % (path, cs, get_entry(av), [get_entry(x) for x in deps])
        m2 = 'av: %s\ndeps: %s' % (str(av), str(deps))
        msgs.append('%s\n%s\n' % (m1, m2))
    for msg in sorted(msgs):
        print(msg)

    msgs1 = []
    msgs2 = []

    for av in matched_avs:
        is_dependant = False
        for dep in dependencies[av]:
            if dep in matched_avs:
                msgs2.append(
                    '%s discarded, as it depends on AV %s, which is also present' % (get_entry(av), get_entry(dep)))
                is_dependant = True
                break
        if not is_dependant:
            msgs1.append('%s found!' % get_entry(av))

    for msg in msgs1:
        print(msg)
    print()
    for msg in msgs2:
        print(msg)
    print()


def do_leveldb_impl(path_to_db, check_sums):
    import plyvel
    db = plyvel.DB(path_to_db)

    def get_entry(key):
        return db.get(key).decode("utf-8")

    matched_avs = set()
    dependencies = {}

    msgs = []

    print()
    for (cs, path) in check_sums:
        entry = db.get(cs.digest())
        if entry is None:
            continue
        if len(entry) % 4 != 0:
            raise Warning("Not array of integers? %s" % cs.hexdigest())
        if len(entry) < 4:
            raise Warning("There always should be one integer in entry. %s" % cs.hexdigest())

        ids = []
        for i in range(0, len(entry), 4):
            ids.append(entry[i:(i + 4)])
        found_av = ids[0]
        found_deps = ids[1:]

        msgs.append(
            'path: %s\nav: %s\ndeps: %s\n' % (
                path,
                get_entry(found_av),
                [get_entry(x) for x in found_deps]
            )
        )

        matched_avs.add(found_av)
        deps = dependencies.setdefault(found_av, [])
        for dep in found_deps:
            deps.append(dep)

    msgs1 = []
    msgs2 = []

    for found_av in matched_avs:
        is_dependant = False
        for dep in dependencies[found_av]:
            if dep in matched_avs:
                msgs2.append('%s discarded, as it depends on AV %s, which is also present' % (
                    get_entry(found_av), get_entry(dep)))
                is_dependant = True
                break
        if not is_dependant:
            msgs1.append('%s found!' % get_entry(found_av))

    for msg in msgs1:
        print(msg)
    print()
    # for msg in msgs2:
    #     print(msg)
    # print()


def do_json_old_impl(path_to_db, check_sums):
    import json
    with open(path_to_db, 'r') as db_file:
        db = json.load(db_file)

    matched_avs = set()
    dependencies = {}

    msgs = []

    print()
    for (cs, path) in check_sums:
        cs = cs.hexdigest().rstrip('\n')
        if cs in db:
            msgs.append('path: %s\nav: %s\ndeps: %s\n' % (str(db[cs]["av"]), path, str(db[cs]["deps"])))

            entry = db[cs]
            av = entry["av"]
            av = str(av)
            matched_avs.add(av)
            deps = dependencies.setdefault(av, [])
            for dep in entry["deps"]:
                dep = str(dep)
                deps.append(dep)

    for msg in sorted(msgs):
        print(msg)

    msgs1 = []
    msgs2 = []

    for av in matched_avs:
        is_dependant = False
        for dep in dependencies[av]:
            if dep in matched_avs:
                msgs2.append('%s discarded, as it depends on AV %s, which is also present' % (str(av), str(dep)))
                is_dependant = True
                break
        if not is_dependant:
            msgs1.append('%s found!' % str(av))

    for msg in msgs1:
        print(msg)
    print()
    for msg in msgs2:
        print(msg)
    print()
