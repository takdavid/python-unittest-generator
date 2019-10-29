import inspect
import os
from pathlib import Path

from coverage_helper import collect as coverage_collect

PROJECT_ROOT = os.getcwd()  # FIXME ?


def relative_filepath(fn):
    if fn.startswith(PROJECT_ROOT):
        return fn[len(PROJECT_ROOT):].lstrip('/\\')
    else:
        return fn


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


lambda_layer_roots = [str(p) for p in Path(PROJECT_ROOT).rglob('python')]
lambda_layer_roots = [relative_filepath(p) for p in lambda_layer_roots if os.path.isdir(p)]
lambda_function_files = [str(p) for p in Path(PROJECT_ROOT).rglob('lambda_function*')]
lambda_function_roots = [relative_filepath(os.path.dirname(str(p))) for p in lambda_function_files if os.path.isfile(p)]
init_files = [str(p) for p in Path(PROJECT_ROOT).rglob('__init__.py')]
package_roots = [relative_filepath(os.path.dirname(str(p))) for p in init_files if os.path.isfile(p)]
package_roots = set([p for p in package_roots if str(p)[0] != '.'])


def suggest_path(package_name, suggested_dir, file_name):
    if file_name == '__init__.py':
        suggested_filename = 'test_' + package_name + '.py'
    else:
        suggested_filename = 'test_' + file_name
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


class ProjectPrefences(object):
    def adjacent_test_files(self):
        pass  # FIXME

    def one_test_subpackage(self):
        pass  # FIXME


class Package(object):
    prefer = ProjectPrefences()

    def __init__(self, relfn) -> None:
        self.relfn = relfn

    def is_lambda(self):
        return any((head in lambda_function_roots or head in lambda_layer_roots)
                   for head, tail in every_binary_split(self.relfn))

    def has_test_subpackage(self):
        pass  # FIXME


class File(object):
    def __init__(self, relfn) -> None:
        self.relfn = relfn

    def is_test(self):
        return ('test' in inspect.getmodulename(self.relfn).split('_')) or ('tests' in self.relfn.split(os.sep))


class Project(object):
    prefer = ProjectPrefences()


def test_module_for_file(relfn):
    package = Package(relfn)
    project = Project()
    file_dir, file_name = os.path.split(relfn)
    package_dir, package_name, _, _ = find_package(relfn)
    test_file_base_name = '.'.join(package_name.split('.')[1:]) if '.' in package_name else package_name

    project_test_dir = relative_filepath(os.path.join(PROJECT_ROOT, 'tests'))
    inside_package_test_dir = os.path.join(package_dir, 'tests')
    if PROJECT_ROOT < package_dir:
        outside_package_test_dir = os.path.join(os.path.dirname(package_dir), 'tests')
    else:
        outside_package_test_dir = project_test_dir

    if package.prefer.adjacent_test_files() and not package.has_test_subpackage():
        return suggest_path(test_file_base_name, file_dir, file_name)

    if package.prefer.one_test_subpackage():
        return suggest_path(test_file_base_name, inside_package_test_dir, file_name)

    if project.prefer.one_test_subpackage():
        # 'there is a test directory outside of the package and an optional src/ dir, than use that':
        return suggest_path(test_file_base_name, project_test_dir, file_name)

    if package.is_lambda():
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
    file = File(relfn)
    if file.is_test():
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
