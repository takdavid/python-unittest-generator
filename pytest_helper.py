import json
import os

from _pytest.config import _prepareconfig
from _pytest.main import Session, ExitCode


def redo_collect():
    config = _prepareconfig()
    session = Session(config)
    config.hook.pytest_sessionstart(session=session)
    items = session.perform_collect()
    config.hook.pytest_sessionfinish(session=session, exitstatus=ExitCode.OK)
    return [item.location for item in items]


def collect():
    fn = '.pytest'
    if os.path.isfile(fn):
        with open(fn, 'r') as f:
            data = json.load(f)
    else:
        with open(fn, 'w') as f:
            data = redo_collect()
            json.dump(data, f, indent=4)
    return data


collect = redo_collect


if __name__ == '__main__':
    for item in collect():
        print(*item)
