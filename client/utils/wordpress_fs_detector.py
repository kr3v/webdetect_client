# !/usr/bin/python
from __future__ import print_function

"""
This script detects WP installation for given path.
"""

import datetime
import json
import os
import re
import sys


def now():
    return str(datetime.datetime.utcnow()).replace(' ', 'T') + 'Z'


def log_info(text, **kwargs):
    print(text, **kwargs)
    # print('%s info: %s' % (now(), text), **kwargs)


def log_err(text, **kwargs):
    print('%s error: %s' % (now(), text), file=sys.stderr, **kwargs)


def list_dirs(path):
    return [x for x in os.listdir(path) if os.path.isdir(os.path.join(path, x))]


def pretty_print_wp(result):
    if result is None:
        return

    path, version, (plugins, themes) = result
    log_info('WordPress %s' % version)
    log_info('path: %s' % path)
    log_info('plugins: %d' % len(plugins))
    for t in sorted(plugins, key=lambda a: a[0]):
        log_info('\t%s#%s, path: %s' % t)
    log_info('themes: %d' % len(themes))
    for t in themes:
        log_info('\t%s#%s, path: %s' % t)


def wp(path):
    # TODO list:
    #  1.Deduce version by changelog additionally (does not always work)

    WP_CONTENT_DIR_NAME = 'wp-content'
    WP_INCLUDES_DIR_NAME = 'wp-includes'
    WP_ADMIN_DIR_NAME = 'wp-admin'
    EXPECTED_DIRS = [WP_ADMIN_DIR_NAME, WP_INCLUDES_DIR_NAME, WP_ADMIN_DIR_NAME]

    VERSION_PHP_FILE_NAME = 'version.php'
    WP_VERSION_LINE_MARKER = '$wp_version = '

    WP_PLUGINS_DIR_NAME = 'plugins'
    WP_THEMES_DIR_NAME = 'themes'
    WP_PLUGIN_README_FILE_NAME = 'readme.txt'
    WP_PLUGIN_TAG_MARKER = 'Stable tag: '

    def verify_wp_installation():
        for expected_dir in EXPECTED_DIRS:
            expected_dir_path = os.path.join(path, expected_dir)
            if not os.path.isdir(expected_dir_path):
                log_err('%s not found, %s does not have WP' % (expected_dir_path, path))
                return False
        return True

    def extract_wp_version():
        def extract_version():
            regex = re.compile("[^']+'([^']+)'[^']+")
            return regex.match(line).group(1)

        version_path = os.path.join(path, WP_INCLUDES_DIR_NAME, VERSION_PHP_FILE_NAME)
        try:
            with open(version_path, mode='r') as version_file:
                for line in version_file:
                    if WP_VERSION_LINE_MARKER in line:
                        return extract_version()
        except:
            pass
        log_err('%s not found, cannot extract WP version at %s' % (version_path, path))
        return None

    # Name = Version = Path = str
    # P = T = Tuple[Name, Version, Path]
    # returns Tuple[Optional[List[P]], Optional[List[T]]]
    def list_plugins_and_themes():
        def read_version_from_readme(plugin_path, plugin_name):
            def extract_version():
                return line.lstrip(WP_PLUGIN_TAG_MARKER).rstrip('\n')

            readme_path = os.path.join(plugin_path, WP_PLUGIN_README_FILE_NAME)
            try:
                with open(readme_path, mode='r') as version_file:
                    for line in version_file:
                        if WP_PLUGIN_TAG_MARKER in line:
                            return extract_version()
            except:
                pass
            log_err('not found or absent tag marker: %s, plugin: %s, path: %s' % (
                readme_path, plugin_name, plugin_path))

        def extract(pth):
            result = []
            for plugin_name in list_dirs(pth):
                plugin_path = os.path.join(pth, plugin_name)
                plugin_version = read_version_from_readme(plugin_path, plugin_name)
                if plugin_version is not None:
                    result.append({"name": plugin_name, "version": plugin_version, "path": plugin_path})
            return result

        plugins_dir = os.path.join(path, WP_CONTENT_DIR_NAME, WP_PLUGINS_DIR_NAME)
        plugins = None
        if os.path.isdir(plugins_dir):
            plugins = extract(plugins_dir)
        else:
            log_err('%s plugins directory not found for %s' % (plugins_dir, path))

        themes_dir = os.path.join(path, WP_CONTENT_DIR_NAME, WP_THEMES_DIR_NAME)
        themes = None
        if os.path.isdir(themes_dir):
            themes = extract(themes_dir)
        else:
            log_err('%s themes directory not found for %s' % (themes_dir, path))

        return plugins, themes

    if not verify_wp_installation():
        return None

    sys.stderr.flush()
    sys.stdout.flush()

    plugins, themes = list_plugins_and_themes()
    return {"path": path, "version": extract_wp_version(), "plugins": plugins, "themes": themes}


def main():
    # path_to_wordpress = sys.argv[1]
    # pretty_print_wp(wp(path_to_wordpress))

    path_to_wordpress = '/usr/share/webapps/wordpress'
    p = wp(path_to_wordpress)
    print(json.dumps(p))


if __name__ == '__main__':
    main()
