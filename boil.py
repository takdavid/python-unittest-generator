import inspect
import os
import sys
from pathlib import Path

import py

from .coverage_helper import collect as coverage_collect
from .pytest_helper import collect as pytest_collect


PROJECT_ROOT = os.getcwd()  # FIXME ?


def relative_filepath(fn):
    if fn.startswith(PROJECT_ROOT):
        return fn[len(PROJECT_ROOT):].lstrip('/\\')
    else:
        return fn


test_locations = pytest_collect()
test_files = list(sorted(set(filenam for filenam, lineno, funam in test_locations)))
from _pytest.config.findpaths import get_common_ancestor
test_root = str(get_common_ancestor([py.path.local(path) for path in test_files]))
test_root = os.path.commonpath(test_files)


def every_binary_split(head, tail=''):
    while os.path.splitdrive(head)[1] not in {'', '/'}:
        head2, tail2 = os.path.split(head)
        tail = os.path.join(tail2, tail) if tail else tail2
        yield (head2, tail)
        head = head2


def bush(paths):
    d = {}
    for path in paths:
        for head, tail in every_binary_split(path):
            if head in d:
                d[head].add(tail)
            else:
                d[head] = {tail,}
    return d


test_file_bush = bush(test_files)

lambda_layer_roots = [str(p) for p in Path(PROJECT_ROOT).rglob('python')]
lambda_layer_roots = [relative_filepath(p) for p in lambda_layer_roots if os.path.isdir(p)]
lambda_function_files = [str(p) for p in Path(PROJECT_ROOT).rglob('lambda_function*')]
lambda_function_roots = [relative_filepath(os.path.dirname(str(p))) for p in lambda_function_files if os.path.isfile(p)]
init_files = [str(p) for p in Path(PROJECT_ROOT).rglob('__init__.py')]
package_roots = [relative_filepath(os.path.dirname(str(p))) for p in init_files if os.path.isfile(p)]
package_roots = set([p for p in package_roots if str(p)[0] != '.'])


def suggest_test_filename(package_name, suggested_dir, file_name):
    if file_name == '__init__.py':
        file_name = package_name + '.py'
    if suggested_dir in test_file_bush:
        prefixed_package = 'test_' + package_name + '.py'
        if prefixed_package in test_file_bush[suggested_dir]:
            return prefixed_package
        suffixed_package = package_name + '_test.py'
        if suffixed_package in test_file_bush[suggested_dir]:
            return suffixed_package
        elif any(fn.endswith('_test.py') for fn in test_file_bush[suggested_dir]):
            return file_name.replace('.py', '_test.py')
    return 'test_' + file_name


def suggest_path(package_name, suggested_dir, file_name):
    suggested_filename = suggest_test_filename(package_name, suggested_dir, file_name)
    return os.path.join(suggested_dir, suggested_filename)


def find_package(relfn):
    package_dir = ''
    package_name = ''
    for head, tail in every_binary_split(relfn):
        if head in lambda_layer_roots:
            package_dir = head
            package_name = os.path.basename(os.path.dirname(package_dir))
            break
        if head in package_roots:
            package_dir = head
            package_name = os.path.basename(package_dir)
            break
    if not package_dir:
        package_dir = os.path.dirname(relfn)
        package_name = os.path.basename(package_dir)
        if package_dir not in sys.path:
            print('Warning: unimportable module %s' % relfn)

    return package_dir, package_name


def find_module_name(relfn):
    return os.path.splitext(os.path.split(relfn)[1])[0]


def test_module_for_file(relfn):
    file_dir, file_name = os.path.split(relfn)
    package_dir, package_name = find_package(relfn)

    package_local_test_dir = os.path.join(package_dir, 'tests')

    if file_dir in test_file_bush and not package_local_test_dir in test_file_bush:
        # 'there is already a test file next to the file':
        return suggest_path(package_name, file_dir, file_name)

    if package_local_test_dir in test_file_bush:
        # 'there is a test directory in the package, next to or above the file, then use that':
        return suggest_path(package_name, package_local_test_dir, file_name)

    project_test_dir = relative_filepath(os.path.join(PROJECT_ROOT, 'tests'))

    if project_test_dir in test_file_bush:
        # 'there is a test directory outside of the package and an optional src/ dir, than use that':
        return suggest_path(package_name, project_test_dir, file_name)

    is_lambda_package = any((head in lambda_function_roots or head in lambda_layer_roots)
                            for head, tail in every_binary_split(relfn))

    if is_lambda_package:
        return suggest_path(package_name, package_local_test_dir, file_name)
        # return suggest_path(package_name, project_test_dir, file_name)
    else:
        return suggest_path(package_name, file_dir, file_name)


TEST_CODE_TEMPLATE = """
from {package_name} import {module_name}

def test_{func_name}():
    pass
"""

for ana in coverage_collect():
    relfn = relative_filepath(ana[0])
    if relfn in test_files:
        print('Unused code in test %s lines %s' % (relfn, ana[4]))
    else:
        print('Missing tests for %s lines %s' % (relfn, ana[4]))
        testfn = test_module_for_file(relfn)
        print('Suggested place %s %s' % (testfn, 'EXISTS' if os.path.isfile(testfn) else 'NEW'))
        _, package_name = find_package(relfn)
        module_name = find_module_name(relfn)
        code = TEST_CODE_TEMPLATE.format(package_name=package_name, module_name=module_name, func_name='some_func')
        if not os.path.isdir(os.path.dirname(testfn)):
            os.makedirs(os.path.dirname(testfn))
        with open(testfn, 'a') as f:
            f.write(code)
