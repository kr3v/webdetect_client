from __future__ import annotations

import os
import subprocess
from functools import partial
from typing import List, Tuple, Callable, Optional

import requests

from fetch.async_class import Async, exec_async

zips_path = 'fetch/zips'
extracted_paths = 'fetch/extracted'
flattened_paths = 'fetch/projects'


def caffeine_handler(app: str, version: str, path: str) -> List[Tuple[str, str]]:
    result = []
    for sub_path in ['caffeine', 'jcache', 'simulator']:
        sub_app = '%s-%s/%s' % (app, sub_path, version)
        sub_app_path = '%s/%s' % (flattened_paths, sub_app)
        app_path = '%s/%s' % (path, sub_path)

        mkdir(sub_app_path).wait()
        if os.path.exists(app_path) and os.path.isdir(app_path):
            subprocess.Popen(['sh', '-c', 'mv %s/* %s' % (app_path, sub_app_path)])

        result.append((sub_app, sub_app_path))
    return result


repos = [
    ('ben-manes/caffeine', caffeine_handler)
]


def curl(url: str, to: str) -> Optional[subprocess.Popen]:
    if os.path.exists(to):
        return None
    else:
        return subprocess.Popen(['curl', '-L', url], stdout=open(to, "w"))


def mkdir(dir: str) -> subprocess.Popen:
    return subprocess.Popen(['mkdir', '-p', dir])


def unzip(path_to_zip: str, into: str) -> Optional[subprocess.Popen]:
    if len(os.listdir(into)) > 0:
        return None
    else:
        return subprocess.Popen(['unzip', path_to_zip, '-d', into])


def fix_repo_unzip(dir: str) -> Optional[subprocess.Popen]:
    listdir = os.listdir(dir)
    if len(listdir) is not 1:
        return None
    else:
        return subprocess.Popen(['sh', '-c', 'mv %s/%s/* %s' % (dir, listdir[0], dir)])


def process_repos_list(repositories: List[Tuple[str, Callable[[str], List[Tuple[str, str]]]]]):
    processes: List[Async] = []
    paths: List[Tuple[str, str]] = []

    for (repo, handler) in repositories:
        for response in requests.get('https://api.github.com/repos/%s/releases' % repo).json():
            repo = repo.replace('/', '_')
            version = response['name']
            zip_url = response['zipball_url']
            path_to_zip = '%s/%s_%s.zip' % (zips_path, repo, version)
            zip_dir = '%s/%s/%s' % (extracted_paths, repo, version)

            processes.append(
                Async(
                    partial(lambda zu, ptz: curl(zu, ptz), zip_url, path_to_zip)).and_then(
                    partial(lambda zd: mkdir(zd), zip_dir)).and_then(
                    partial(lambda ptz, zd: unzip(ptz, zd), path_to_zip, zip_dir)).and_then(
                    partial(lambda pd: fix_repo_unzip(pd), zip_dir)).and_then(
                    partial(lambda a, v, p: paths.append(handler(a, v, p)), repo, version, zip_dir)
                )
            )

    exec_async(processes)

    for path in paths:
        print(path)


mkdir(zips_path).wait()
mkdir(flattened_paths).wait()
mkdir(extracted_paths).wait()

process_repos_list(repos)
