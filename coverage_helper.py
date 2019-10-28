from coverage import Coverage


def has_uncovered_lines(ana):
    return ana[3] and ana[4]


def collect():
    cov = Coverage()
    dat = cov.get_data()
    dat.read_file('.coverage.linux')  # this is necessary for some reason
    for fn in sorted(dat.measured_files()):
        ana = cov.analysis2(fn)
        if has_uncovered_lines(ana):
            yield ana


if __name__ == '__main__':
    for item in collect():
        print(*item)
