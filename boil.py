import inspect
import os
from pathlib import Path

from coverage_helper import collect as coverage_collect
from pytest_helper import collect as pytest_collect

PROJECT_ROOT = os.getcwd()  # FIXME ?


def relative_filepath(fn):
    if fn.startswith(PROJECT_ROOT):
        return fn[len(PROJECT_ROOT):].lstrip('/\\')
    else:
        return fn


test_locations = pytest_collect()
test_files = set(filenam for filenam, lineno, funam in test_locations)


def every_binary_split(head, tail=''):
    while os.path.splitdrive(head)[1] not in {'', '/', '\\'}:
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
    extend_syspath = []
    touch_files = []
    module_name = inspect.getmodulename(relfn)
    if module_name == '__init__':
        module_name = ''
    package_dir = ''
    package_name = module_name
    for head, tail in every_binary_split(relfn):
        if head in lambda_layer_roots:
            package_dir = head
            extend_syspath.append(package_dir)
            break
        if head in package_roots:
            package_dir = head
            package_name = os.path.basename(package_dir) + '.' + package_name
            continue
        break
    package_name = package_name.strip('.')
    if not package_dir:
        print('Warning: source %s is not in a package' % relfn)
        package_dir = os.path.dirname(relfn)
        package_name = os.path.basename(package_dir)
        if package_name.isidentifier():
            touch_files.append(os.path.join(package_dir, '__init__.py'))
    if not package_name.replace('.', '_').isidentifier():
        if not module_name.isidentifier():
            print('Warning: "%s" is impossible to import' % relfn)
            package_name = ''
        else:
            print('Warning: importing %s as module %s' % (relfn, module_name))
            package_name = module_name
            extend_syspath.append(package_dir)

    return package_dir, package_name, extend_syspath, touch_files


def test_module_for_file(relfn):
    file_dir, file_name = os.path.split(relfn)
    package_dir, package_name, _, _ = find_package(relfn)
    test_file_base_name = '.'.join(package_name.split('.')[1:]) if '.' in package_name else package_name

    project_test_dir = relative_filepath(os.path.join(PROJECT_ROOT, 'tests'))
    inside_package_test_dir = os.path.join(package_dir, 'tests')
    if PROJECT_ROOT < package_dir:
        outside_package_test_dir = os.path.join(os.path.dirname(package_dir), 'tests')
    else:
        outside_package_test_dir = project_test_dir

    if file_dir in test_file_bush and not inside_package_test_dir in test_file_bush:
        # 'there is already a test file next to the file':
        return suggest_path(test_file_base_name, file_dir, file_name)

    if inside_package_test_dir in test_file_bush:
        # 'there is a test directory in the package, next to or above the file, then use that':
        return suggest_path(test_file_base_name, inside_package_test_dir, file_name)

    if project_test_dir in test_file_bush:
        # 'there is a test directory outside of the package and an optional src/ dir, than use that':
        return suggest_path(test_file_base_name, project_test_dir, file_name)

    is_lambda_package = any((head in lambda_function_roots or head in lambda_layer_roots)
                            for head, tail in every_binary_split(relfn))

    if is_lambda_package:
        return suggest_path(test_file_base_name, outside_package_test_dir, file_name)
        # return suggest_path(test_file_base_name, project_test_dir, file_name)
    else:
        return suggest_path(test_file_base_name, inside_package_test_dir, file_name)


def gen_test_code_template(fully_qualified_module_name):
    parts = [None, None] + fully_qualified_module_name.split('.')
    package_name, module_name = parts[-2:]
    c = ''
    if package_name:
        c += "from %s import %s" % (package_name, module_name)
    else:
        c += "import %s" % module_name
    c += "\n"
    c += "def test_%s():\n    pass\n" % module_name
    c += "\n"
    return c


def touch(fn):
    if not os.path.isfile(fn):
        with open(fn, 'a') as f:
            f.flush()


for ana in coverage_collect():
    relfn = relative_filepath(ana[0])
    if (relfn in test_files) or ('tests' in relfn.split(os.sep)):
        continue
    else:
        testfn = test_module_for_file(relfn)
        print('%s %s for %s' % ('Updating' if os.path.isfile(testfn) else 'Creating', testfn, relfn))

        package_dir, package_name, extend_syspath, touch_files = find_package(relfn)

        if package_name:
            test_dir = os.path.dirname(testfn)
            if not os.path.isdir(test_dir):
                os.makedirs(test_dir)
            if package_name and os.path.basename(test_dir) == 'tests' and package_dir not in extend_syspath:
                touch(os.path.join(test_dir, '__init__.py'))

            code = gen_test_code_template(package_name)
            with open(testfn, 'a') as f:
                f.write(code)
            for fn in touch_files:
                touch(fn)

            if extend_syspath:
                print('Extending PYTHONPATH with %s' % ':'.join(extend_syspath))
