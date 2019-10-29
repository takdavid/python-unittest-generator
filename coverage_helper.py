import os
from pathlib import Path

from coverage import Coverage


def redo_collect():
    raise NotImplementedError()


def has_uncovered_lines(ana):
    return ana[3] and ana[4]


def collect():
    cov = Coverage()
    dat = cov.get_data()
    dat.read_file(os.getenv('COVERAGE_FILE', '.coverage'))  # this is necessary for some reason
    for p in Path().rglob('*.py'):
        fn = str(p.absolute())
        if not (cov.omit_match and cov.omit_match.match(fn)):
            dat.touch_file(fn)
    for fn in sorted(dat.measured_files()):
        ana = cov.analysis2(fn)
        if has_uncovered_lines(ana):
            yield ana


if __name__ == '__main__':
    for item in collect():
        print(*item)
