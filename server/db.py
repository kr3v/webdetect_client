import psycopg2

conn = psycopg2.connect("dbname=webdetect user=webdetect password=webdetectPss")


def init():
    cur = conn.cursor()
    cur.execute("""
    create table if not exists hashes 
    (
        hash char(64) not null,
        path text not null primary key
    );
    
    create unique index if not exists hashes_path_uindex
        on hashes (path);
    """)
    conn.commit()
    cur.close()


def get_by_path(path: str) -> str:
    cur = conn.cursor()
    cur.execute("SELECT hash FROM hashes WHERE path=%s;", (path,))
    one = cur.fetchone()
    if one is None:
        res = None
    else:
        res = str(one[0])
    cur.close()
    return res


def get_by_hash(hash: str) -> str:
    cur = conn.cursor()
    cur.execute("SELECT path FROM hashes WHERE hash=%s;", (hash,))
    one = cur.fetchone()
    if one is None:
        res = None
    else:
        res = str(one[0])
    cur.close()
    return res


def insert(path: str, hash_str: str):
    cur = conn.cursor()
    cur.execute("INSERT INTO hashes(hash, path) VALUES (%s, %s);", (hash_str, path))
    conn.commit()
    cur.close()
