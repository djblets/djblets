#!/usr/bin/env python
#
# Performs a release of Review Board. This can only be run by the core
# developers with release permissions.
#

import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from djblets import get_package_version, VERSION


PY_VERSIONS = ["2.4", "2.5", "2.6"]

LATEST_PY_VERSION = PY_VERSIONS[-1]

PACKAGE_NAME = 'Djblets'

RELEASES_URL = \
    'review-board.org:/var/www/downloads.review-board.org/' \
    'htdocs/releases/%s/%s.%s/' % (PACKAGE_NAME, VERSION[0], VERSION[1])


built_files = []


def execute(cmdline):
    print ">>> %s" % cmdline
    if os.system(cmdline) != 0:
        print "!!! Error invoking command."
        sys.exit(1)


def run_setup(target, pyver = LATEST_PY_VERSION):
    execute("python%s ./setup.py release %s" % (pyver, target))


def build_targets():
    for pyver in PY_VERSIONS:
        run_setup("bdist_egg", pyver)
        built_files.append("dist/%s-%s-py%s.egg" %
                           (PACKAGE_NAME, get_package_version(), pyver))

    run_setup("sdist")
    built_files.append("dist/%s-%s.tar.gz" %
                       (PACKAGE_NAME, get_package_version()))


def build_news():
    def linkify_bugs(line):
        return re.sub(r'(Bug #(\d+))',
                      r'<a href="http://www.review-board.org/bug/\2">\1</a>',
                      line)

    content = ""
    html_content = ""

    saw_version = False
    in_list = False
    in_item = False

    fp = open("NEWS", "r")

    for line in fp.xreadlines():
        line = line.rstrip()

        if line.startswith("version "):
            if saw_version:
                # We're done.
                break

            saw_version = True
        elif line.startswith("\t* "):
            if in_item:
                html_content += "</li>\n"
                in_item = False

            if in_list:
                html_content += "</ul>\n"

            html_content += "<p><b>%s</b></p>\n" % line[3:]
            html_content += "<ul>\n"
            in_list = True
        elif line.startswith("\t\t* "):
            if not in_list:
                sys.stderr.write("*** Found a list item without a list!\n")
                continue

            if in_item:
                html_content += "</li>\n"

            html_content += " <li>%s" % linkify_bugs(line[4:])
            in_item = True
        elif line.startswith("\t\t  "):
            if not in_item:
                sys.stderr.write("*** Found list item content without "
                                 "a list item!\n")
                continue

            html_content += " " + linkify_bugs(line[4:])

        content += line + "\n"

    fp.close()

    if in_item:
        html_content += "</li>\n"

    if in_list:
        html_content += "</ul>\n"

    content = content.rstrip()

    filename = "dist/%s-%s.NEWS" % (PACKAGE_NAME, get_package_version())
    built_files.append(filename)
    fp = open(filename, "w")
    fp.write(content)
    fp.close()

    filename = "dist/%s-%s.NEWS.html" % (PACKAGE_NAME, get_package_version())
    fp = open(filename, "w")
    fp.write(html_content)
    fp.close()


def upload_files():
    execute("scp %s %s" % (" ".join(built_files), RELEASES_URL))


def tag_release():
    execute("git tag release-%s" % get_package_version())


def register_release():
    run_setup("register")


def main():
    if not os.path.exists("setup.py"):
        sys.stderr.write("This must be run from the root of the "
                         "Djblets tree.\n")
        sys.exit(1)

    build_targets()
    build_news()
    upload_files()
    tag_release()
    register_release()


if __name__ == "__main__":
    main()
