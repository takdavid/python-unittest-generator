import pytest


def collect():
    from _pytest.config import _prepareconfig
    from _pytest.main import Session, ExitCode
    config = _prepareconfig()
    session = Session(config)
    config.hook.pytest_sessionstart(session=session)
    items = session.perform_collect()
    config.hook.pytest_sessionfinish(session=session, exitstatus=ExitCode.OK)
    return [item.location for item in items]


if __name__ == '__main__':
    for item in collect():
        print(*item)
