import inspect
import os

from coverage_helper import collect as coverage_collect


def every_binary_split(head, tail=''):
    while os.path.splitdrive(head)[1] not in {'', '/', '\\'}:
        head2, tail2 = os.path.split(head)
        tail = os.path.join(tail2, tail) if tail else tail2
        yield (head2, tail)
        head = head2


def suggest_path(package_name, suggested_dir, file_name):
    if file_name == '__init__.py':
        suggested_filename = 'test_' + package_name + '.py'
    else:
        suggested_filename = 'test_' + file_name
    return os.path.join(suggested_dir, suggested_filename)


class ProjectPrefences(object):
    def adjacent_test_files(self):
        pass  # FIXME

    def one_test_subpackage(self):
        pass  # FIXME


class Directory(object):

    def __init__(self, path) -> None:
        self.absolute = os.path.abspath(str(path))
        self.relative = self.absolute[len(os.getcwd()):].lstrip('/\\')

    def __str__(self) -> str:
        return self.relative

    def __add__(self, other):
        return self.relative + str(other)

    def is_lambda(self):
        return os.path.basename(self.relative) == 'python'

    def is_package_root(self):
        return os.path.isfile(os.path.join(self.relative, '__init__.py'))

    def __contains__(self, other):
        return str(other.absolute).startswith(str(self.absolute))

    def relative_filepath(self, fn):
        a = os.path.abspath(str(fn))
        b = self.absolute
        if a.startswith(b):
            return a[len(b):].lstrip('/\\')


class Package(object):
    prefer = ProjectPrefences()

    def __init__(self, relfn) -> None:
        self.relfn = relfn

    def is_lambda(self):
        return any((Directory(head).is_lambda()) for head, tail in every_binary_split(self.relfn))

    def has_test_subpackage(self):
        pass  # FIXME


class File(object):
    def __init__(self, relfn) -> None:
        self.relfn = relfn

    def is_test(self):
        return ('test' in inspect.getmodulename(self.relfn).split('_')) or ('tests' in self.relfn.split(os.sep))

    def find_package(self):
        pass


class Project(object):
    prefer = ProjectPrefences()

    root = Directory(os.getcwd())  # FIXME

    def find_package(self, relfn):
        extend_syspath = []
        touch_files = []
        module_name = inspect.getmodulename(relfn)
        if module_name == '__init__':
            module_name = ''
        package_dir = ''
        package_name = module_name
        for head, tail in every_binary_split(relfn):
            if Directory(head).is_lambda():
                package_dir = head
                extend_syspath.append(package_dir)
                break
            if Directory(head).is_package_root():
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


    def test_module_for_file(self, relfn):
        package = Package(relfn)
        project = self
        file_dir, file_name = os.path.split(relfn)
        package_dir, package_name, _, _ = project.find_package(relfn)
        test_file_base_name = '.'.join(package_name.split('.')[1:]) if '.' in package_name else package_name

        project_test_dir = project.root + 'tests'
        inside_package_test_dir = os.path.join(package_dir, 'tests')
        if Directory(package_dir) in project.root:
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
    project = Project()
    relfn = project.root.relative_filepath(ana[0])
    file = File(relfn)
    if file.is_test():
        continue
    else:
        testfn = project.test_module_for_file(relfn)
        print('%s %s for %s' % ('Updating' if os.path.isfile(testfn) else 'Creating', testfn, relfn))

        package_dir, package_name, extend_syspath, touch_files = project.find_package(relfn)

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
