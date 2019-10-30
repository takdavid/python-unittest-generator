import inspect
import os
from pathlib import Path

from coverage_helper import collect as coverage_collect


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
        return os.path.join(self.relative, str(other))

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

    def __init__(self, dir, name, pivot) -> None:
        self.dir = Directory(dir)
        self.name = name
        self.pivot = pivot

    def is_lambda(self):
        return self.dir.is_lambda() or any(Directory(head).is_lambda() for head in self.pivot.path.parents)

    def has_test_subpackage(self):
        pass  # FIXME


class File(object):
    def __init__(self, path) -> None:
        self.path = Path(path)

    @property
    def dir(self):
        return self.path.parent

    @property
    def name(self):
        return os.path.split(str(self.path))[1]

    def is_test(self):
        return ('test' in self.name.split('_')) or ('tests' in tuple(self.path.parts))

    def find_package(self):
        pass


class Project(object):
    prefer = ProjectPrefences()

    def __init__(self, rootdir) -> None:
        self.root = Directory(rootdir)

    def find_package(self, file):
        relfn = str(file.path)
        extend_syspath = []
        touch_files = []
        module_name = inspect.getmodulename(relfn)
        if module_name == '__init__':
            module_name = ''
        package_dir = ''
        package_name = module_name
        for head in file.path.parents:
            head = str(head)
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

        package = Package(dir=package_dir, name=package_name, pivot=file)
        return package, extend_syspath, touch_files


    def test_module_for_file(self, file):
        project = self
        file_dir, file_name = os.path.split(str(file.path))
        package, _, _ = project.find_package(file)
        test_file_base_name = '.'.join(package.name.split('.')[1:]) if '.' in package.name else package.name

        project_test_dir = project.root + 'tests'
        inside_package_test_dir = package.dir + 'tests'
        if Directory(package.dir) in project.root:
            outside_package_test_dir = os.path.join(os.path.dirname(str(package.dir)), 'tests')
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


def boil(filepaths):
    project = Project(os.getcwd())
    for fn in filepaths:
        file = File(project.root.relative_filepath(fn))
        if file.is_test():
            continue
        else:
            package, extend_syspath, touch_files = project.find_package(file)
            testfn = project.test_module_for_file(file)

            if package.name:
                test_dir = os.path.dirname(testfn)
                if not os.path.isdir(test_dir):
                    os.makedirs(test_dir)
                if package.name and os.path.basename(test_dir) == 'tests' and str(package.dir) not in extend_syspath:
                    touch(os.path.join(test_dir, '__init__.py'))

                code = gen_test_code_template(package.name)
                with open(testfn, 'a') as f:
                    f.write(code)
                for fn in touch_files:
                    touch(fn)

                if extend_syspath:
                    print('Extending PYTHONPATH with %s' % ':'.join(extend_syspath))


if __name__ == '__main__':
    boil(ana[0] for ana in coverage_collect())
