import shutil
import subprocess
import tarfile
from os.path import join
from shutil import copyfile

import os


def read_file(path: str) -> str:
    with open(path, 'r') as f:
        return f.read()


def copy_file(src: str, dst: str):
    print('copy ' + src + ' to ' + dst)
    copyfile(src, dst)


def copy_to(src: str, dst: str):
    if os.path.exists(src):
        shutil.copytree(src, join(dst, src))


def tar(path: str, dirs: list, dst: str):
    with tarfile.open(dst, 'w') as archive:
        for d in dirs:
            archive.add(join(path, d), arcname=d)


# TODO catch read errors
def read_file_lines(path: str) -> list:
    with open(path, 'r') as f:
        return f.readlines()


def write_file_lines(file_lines: list, path: str):
    with open(path, 'w') as f:
        f.writelines(file_lines)


# TODO catch write errors
def write_file(path: str, content: str, binary=False) -> str:
    if binary:
        mode = 'wb'
    else:
        mode = 'w'
    with open(path, mode) as f:
        f.write(content)
    return path


def if_dir_exists(path: str, dir_to_check: str) -> str or None:
    full = join(path, dir_to_check)
    if not os.path.exists(full):
        return None
    else:
        return full


# link include_src -> include_dst
# if link exists and it is not as include_src - remove old link and place new one.
# Return True in this case as possibly dep was updated
# if there is a directory instead of link - remove it and set link.
# Return True in this case also
def link_if_needed(include_src: str, include_dst: str) -> bool:
    if os.path.exists(include_src):
        if os.path.islink(include_dst) and os.readlink(include_dst) == include_src:  # link up to date
            print('already linked: ' + include_src)
            return False
        elif os.path.islink(include_dst):  # link outdated or broken
            print('update link: ' + include_src)
            os.remove(include_dst)  # TODO we can return False here if only erl version was changed.
            os.symlink(include_src, include_dst)
            return True
        elif not os.path.exists(include_dst):  # there was no link. Should add it but return false - there was no update
            print('link ' + include_src + ' -> ' + include_dst)
            os.symlink(include_src, include_dst)
            return False
        else:  # not a link. May be file
            print('overwrite ' + include_src + ' -> ' + include_dst)
            remove_dir(include_dst)
            os.symlink(include_src, include_dst)
            return True


def ensure_dir(path: str):
    if not os.path.exists(path):
        os.makedirs(path)


# Get path to cmd or None if not found in system
def get_cmd(path: str, cmd) -> str or None:
    if ensure_programm(cmd):  # check cmd in system
        return cmd
    else:
        if os.path.isfile(join(path, cmd)):  # check cmd in current dir
            return './' + cmd
    return None


# Check if program installed in system
def ensure_programm(name: str) -> bool:
    try:
        subprocess.call([name])
        return True
    except OSError as e:
        if e.errno == os.errno.ENOENT:
            return False
        else:
            raise


# If dir exists delete and and create again
def ensure_empty(path: str):
    remove_dir(path)
    ensure_dir(path)


def remove_dir(path: str):
    if os.path.exists(path):
        shutil.rmtree(path)
