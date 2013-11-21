#!/usr/bin/env python
#
# Performs a release of Review Board. This can only be run by the core
# developers with release permissions.
#

import os
import re
import shutil
import sys
import tempfile

from fabazon.s3 import S3Bucket

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from djblets import __version__, __version_info__, is_release


PY_VERSIONS = ["2.5", "2.6", "2.7"]

LATEST_PY_VERSION = PY_VERSIONS[-1]

PACKAGE_NAME = 'Djblets'

RELEASES_BUCKET_NAME = 'downloads.reviewboard.org'
RELEASES_BUCKET_KEY = '/releases/%s/%s.%s/' % (PACKAGE_NAME,
                                               __version_info__[0],
                                               __version_info__[1])


built_files = []


def execute(cmdline):
    print ">>> %s" % cmdline
    if os.system(cmdline) != 0:
        sys.stderr.write('!!! Error invoking command.\n')
        sys.exit(1)


def run_setup(target, pyver=LATEST_PY_VERSION):
    execute("python%s ./setup.py release %s" % (pyver, target))


def clone_git_tree(git_dir):
    new_git_dir = tempfile.mkdtemp(prefix='djblets-release.')

    os.chdir(new_git_dir)
    execute('git clone %s .' % git_dir)

    return new_git_dir


def build_targets():
    for pyver in PY_VERSIONS:
        run_setup('bdist_egg', pyver)
        built_files.append(('dist/%s-%s-py%s.egg'
                            % (PACKAGE_NAME, __version__, pyver),
                            'application/octet-stream'))

    run_setup('sdist')
    built_files.append(('dist/%s-%s.tar.gz' % (PACKAGE_NAME, __version__),
                        'application/x-tar'))


def build_news():
    def linkify_bugs(line):
        return re.sub(r'(Bug #(\d+))',
                      r'<a href="http://www.reviewboard.org/bug/\2">\1</a>',
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

    filename = "dist/%s-%s.NEWS" % (PACKAGE_NAME, __version__)
    built_files.append((filename, 'text/plain'))
    fp = open(filename, "w")
    fp.write(content)
    fp.close()

    filename = "dist/%s-%s.NEWS.html" % (PACKAGE_NAME, __version__)
    fp = open(filename, "w")
    fp.write(html_content)
    fp.close()


def upload_files():
    bucket = S3Bucket(RELEASES_BUCKET_NAME)

    for filename, mimetype in built_files:
        bucket.upload(filename,
                      '%s%s' % (RELEASES_BUCKET_KEY,
                                filename.split('/')[-1]),
                      mimetype=mimetype,
                      public=True)

    bucket.upload_directory_index(RELEASES_BUCKET_KEY)

    # This may be a new directory, so rebuild the parent as well.
    parent_key = '/'.join(RELEASES_BUCKET_KEY.split('/')[:-2])
    bucket.upload_directory_index(parent_key)


def tag_release():
    execute("git tag release-%s" % __version__)


def register_release():
    run_setup("register")


def main():
    if not os.path.exists("setup.py"):
        sys.stderr.write("This must be run from the root of the "
                         "Djblets tree.\n")
        sys.exit(1)

    if not is_release():
        sys.stderr.write('This has not been marked as a release in '
                         'djblets/__init__.py\n')
        sys.exit(1)

    cur_dir = os.getcwd()
    git_dir = clone_git_tree(cur_dir)

    build_targets()
    build_news()
    upload_files()

    os.chdir(cur_dir)
    shutil.rmtree(git_dir)

    tag_release()
    register_release()


if __name__ == "__main__":
    main()
