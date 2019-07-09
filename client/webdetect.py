import json

def do(path_to_db, check_sums):
    with open(path_to_db, 'r') as db_file:
        db = json.load(db_file)

    matched_avs = set()
    dependencies = {}

    msgs = []

    print()
    for cs in check_sums:
        cs = cs.rstrip('\n')
        if cs in db:
            msgs.append('Match! %s' % str(db[cs]))

            entry = db[cs]
            av = entry["av"]
            av = (av["app"], av["version"])
            matched_avs.add(av)
            deps = dependencies.setdefault(av, [])
            for dep in entry["deps"]:
                dep = (dep["app"], dep["version"])
                deps.append(dep)

    for msg in sorted(msgs):
        print(msg)

    print()
    print("Matched (not filtered) AVs: %s" % str(matched_avs))
    print("Dependecies for matched AVs: %s" % str(dependencies))
    print()

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