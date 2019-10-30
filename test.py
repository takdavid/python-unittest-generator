from boil import File


def test_parents():
    def check(relfn, expected):
        file = File(relfn)
        actual = ['' if str(head) == '.' else str(head) for head in file.path.parents]
        assert expected == actual, 'Difference in lists %r and %r for %s' % (expected, actual, relfn)
    check('utg.py', [''])
    check('utg/boil.py', ['utg', ''])
    check('utg/subpackage/boil.py', ['utg/subpackage', 'utg', ''])
