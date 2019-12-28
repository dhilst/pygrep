import sys
import os
import mimetypes
from concurrent.futures import ProcessPoolExecutor
from fnmatch import fnmatch
from binaryornot.check import is_binary
import re

from abc import ABC, abstractmethod
from itertools import chain


def recursive_traverse(root):
    for root, dirs, files in os.walk(root):
        for f in chain(dirs, files):
            yield os.path.join(root, f)
        for d in dirs:
            yield from recursive_traverse(os.path.join(root, d))


class IgnoreBase(ABC):
    @abstractmethod
    def ignored(self, file_name: str) -> bool:
        pass


class GitIgnorePatterns(IgnoreBase):
    def __init__(self, fpath):
        try:
            self.patterns = open(fpath).readlines()
        except OSError:
            self.patterns = []

    def ignored(self, file_name):
        for p in self.patterns:
            if p.startwith("#"):
                continue
            if fnmatch(file_name, p):
                return True
        return False


class IgnoreSpecials(IgnoreBase):
    def ignored(self, file_name):
        return False


class IgnoredPatterns:
    def __init__(self):
        self.items = []

    def add(self, item):
        self.items.append(item)

    def __contains__(self, file_name):
        for item in self.items:
            if item.ignored(file_name):
                return True
        return False


ignored_patterns = IgnoredPatterns()
ignored_patterns.add(GitIgnorePatterns(".gitignore"))
ignored_patterns.add(GitIgnorePatterns(".ignore"))


def grep_file(f, pattern):
    try:
        f = open(f)
    except OSError:
        return
    try:
        lines = enumerate(f.readlines())
    except UnicodeDecodeError:
        return
    for i, line in lines:
        if pattern.search(line):
            print("{}:{}:{}".format(f.name, i, line.rstrip()))


def main():
    pattern = sys.argv[1]
    pattern = re.compile(pattern)
    try:
        root = sys.argv[2]
    except IndexError:
        root = "."

    with ProcessPoolExecutor() as executor:
        for f in recursive_traverse(root):
            if f in ignored_patterns:
                continue
            if not os.path.isfile(f):
                continue
            if is_binary(f):
                continue
            executor.submit(grep_file, f, pattern)


if __name__ == "__main__":
    main()
