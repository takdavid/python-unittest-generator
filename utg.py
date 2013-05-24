""" unit test generator """

""" The default run mode is non-capture. """
runmode = "test" # "capture" or "test"

# module API

def capture_mode():
    """ Switch to capture mode. """
    global runmode
    runmode = "capture"

def test_mode():
    """ Switch to non-capture mode. """
    global runmode
    runmode = "test"

def callablesOf(obj):
    """ Return all callable attributes of the argument. """
    return [getattr(obj, method) for method in dir(obj) if callable(getattr(obj, method))]

import re

def capture_module_functions(mod, exclude=None):
    """ Decorates all functions of the module, except the imported and the explicitely excluded ones. """
    for fun in callablesOf(mod):
        if fun.__module__ == mod.__name__ and (not exclude or not re.match(exclude, fun.__name__)):
            setattr(mod, fun.__name__, capture(fun))

def capture_object_methods(obj, re_exclude=None):
    """ Decorates all functions of the module, except the imported and the explicitely excluded ones. """
    for fun in callablesOf(obj):
        if (not re_exclude or not re.match(re_exclude, fun.__name__)):
            setattr(obj, fun.__name__, capture(fun))

def capture(function):
    """ Decorator which captures the args and the return values or the exception of the function. """
    global runmode
    if runmode != "capture":
        return function
    def wrapper(*args, **kwargs):
        serialize = Repo.marshal().serialize
        callhistory = Repo.callhistory()
        callid = callhistory.get_next_id()
        if is_instance_method(function):
            key = function.im_self.__module__ + "." + function.im_self.__class__.__name__ + "." + function.__name__
            callhistory.call_object(callid, id(function.im_self))
        else:
            key = function.__module__ + "." + function.__name__
        callhistory.call_enter(callid, key, serialize(args), serialize(kwargs))
        try:
            ret = function(*args, **kwargs)
            callhistory.call_result(callid, serialize(ret), serialize(None))
            return ret
        except Exception, exc:
            callhistory.call_result(callid, serialize(None), serialize(exc))
            raise exc
    wrapper.__name__ = function.__name__
    wrapper.__doc__ = function.__doc__
    try:
        wrapper.__dict__.update(function.__dict__)
    except:
        pass
    return wrapper

def gen_capture_log():
    """ Generate the capture log line by line. """
    hw = CallHistoryWriter()
    Repo.callhistory().replay(hw)
    return hw.log

def write_capture_log(filename):
    """ Write out the capture log to a file. """
    f = open(filename, 'w')
    for line in gen_capture_log():
        f.write(line + "\n")
    f.close()

def read_capture_log(filename):
    """ Read in the capture log from a file. """
    parser = CallHistoryParser()
    l = open(filename, 'r')
    parser.parse(l.readlines())
    l.close()
    parser.replay(Repo.callhistory())

def gen_test_code():
    """ Generate the test code in a string. """
    return TestCodegen(Repo.callhistory(), Repo.marshal()).test_code()

def write_test_code(filename):
    """ Write out the test code to a file. """
    f = open(filename, 'w')
    f.write(gen_test_code())
    f.close()

# classes

class Repo:
    """ Factory and repository. """

    _marshal = None
    @staticmethod
    def marshal():
        if not isinstance(Repo._marshal, AbstractMarshal):
            Repo._marshal = ReprMarshal()
        return Repo._marshal;

    _callhistory = None
    @staticmethod
    def callhistory():
        if not isinstance(Repo._callhistory, CallHistory):
            Repo._callhistory = CallHistory()
        return Repo._callhistory;

class AbstractMarshal:
    def serialize(self, obj): pass
    def unserialize(self, obj): pass

class ReprMarshal (AbstractMarshal):
    def serialize(self, obj):
        return repr(obj)

    def unserialize(self, obj):
        return eval(obj)

    def empty_list(self, obj):
        return "[]"

    def empty_dict(self, obj):
        return "{}"

    def none(self):
        return "None"

    def default_exception(self):
        return "Exception()"

    def is_empty(self, code):
        return not code or code in ("()", "[]", "{}", "''", '""', self.none())

    def is_exception(self, s_exc):
        return s_exc and s_exc != self.none()


class Stack(list):

    def top(self):
        try:
            return self[-1]
        except IndexError:
            return None

    def popWhile(self, callback):
        item = self.pop()
        while len(self) > 0 and callback(item):
            item = self.pop()
        if callback(item):
            raise Exception("Stack item not found")
        return item

    def get_indent(self):
        return "".join([ "    " for i in range(len(self))])

class Reachability:

    def __init__(self):
        self._reachability = {}

    def update(self, id_from, id_to, distance):
        if not id_from in self._reachability:
            self._reachability[id_from] = {}
        if not id_to in self._reachability[id_from]:
            self._reachability[id_from][id_to] = distance;
        else:
            self._reachability[id_from][id_to] = min(distance, self._reachability[id_from][id_to])

    def updatePathTo(self, key, path):
        for (depth, item) in path:
            self.update(item[1], key, depth)

    def matrix(self):
        return self._reachability

class CallHistoryBuilder(object):

    def __init__(self):
        self.next_id = 0
        self.calls = {}
        self.results = {}
        self.linear = []
        self.log = []
        self.indent = ""
        self.directive = {}
        self.object_calls = {}

    def replay(self, that):
        for (indent, what, id) in self.linear:
            that.indent = indent
            if what == 'enter':
                if self.object_calls.get(id):
                    that.call_object(id, self.object_calls[id])
                that.call_enter(id, * self.calls[id])
            elif what == 'result':
                that.call_result(id, * self.results[id])
        for id in self.directive:
            that.directive[id] = self.directive[id]

    def get_next_id(self):
        id = self.next_id
        self.next_id += 1
        return id

    def get_indent(self):
        return self.indent

    def call_object(self, callid, objid):
        self.object_calls[callid] = objid

    def call_enter(self, id, key, s_args, s_kwargs):
        self.calls[id] = [key, s_args, s_kwargs]
        self.linear.append((self.get_indent(), 'enter', id, ))

    def call_result(self, id, s_res, s_exc):
        self.results[id] = [s_res, s_exc]
        self.linear.append((self.get_indent(), 'result', id, ))

    def isTestable(self, id):
        return id not in self.directive or "TEST" in self.directive[id] or not "SKIP" in self.directive[id]

    def isMockable(self, id):
        return id in self.directive and "MOCK" in self.directive[id]

class CallHistoryWriter(CallHistoryBuilder):

    def __init__(self):
        super(CallHistoryWriter, self).__init__()

    def write(self, str):
        self.log.append(str)

    def call_enter(self, id, key, s_args, s_kwargs):
        if self.object_calls.get(id):
            objidpart = "$" + str(self.object_calls[id]) + "$"
        else:
            objidpart = ""
        self.write(self.get_indent() + "CALL " + key + " " + objidpart)
        self.write(self.get_indent() + "ARGS " + s_args)
        self.write(self.get_indent() + "KWARGS " + s_kwargs)

    def call_result(self, id, s_res, s_exc):
        if s_exc == "None":
            self.write(self.get_indent() + "RETURN " + s_res)
        else:
            self.write(self.get_indent() + "RAISE " + s_exc)

import re

class CallHistoryParser(CallHistoryBuilder):

    def __init__(self):
        super(CallHistoryParser, self).__init__()
        self._parse_directives = {}

    def setDirective(self, indent, key, directive):
        if not directive:
            return
        if not key in self._parse_directives:
            self._parse_directives[key] = {}
        if not directive in self._parse_directives[key]:
            self._parse_directives[key][directive] = set()
        self._parse_directives[key][directive].add(indent)
        if directive == "TEST":
            self.unsetDirective(indent, key, "SKIP")
        elif directive == "SKIP":
            self.unsetDirective(indent, key, "TEST")

    def unsetDirective(self, indent, key, directive):
        if key in self._parse_directives and directive in self._parse_directives[key]:
            self._parse_directives[key][directive].remove(indent)

    def getDirectives(self, indent, key):
        dirs = set() 
        if key in self._parse_directives:
            for directive in self._parse_directives[key]:
                for ind in self._parse_directives[key][directive]:
                    if ind <= indent:
                        dirs.add(directive)
        return dirs

    def invalidateDirectives(self, indent, keyFilter=None):
        for key in self._parse_directives.keys():
            if not keyFilter or key == keyFilter:
                for directive in self._parse_directives[key].keys():
                    for ind in self._parse_directives[key][directive]:
                        if ind >= indent:
                            self._parse_directives[key][directive] = set()

    def parse(self, log):
        """ parse annotated call history """
        id_for_indent = {}
        lines = iter(log)
        for line in lines:
            m = re.match("^(\s*)((?:SKIP|TEST)?) *?CALL (.*?) ((\$(.*)\$)?)\s*$", line)
            if m:
                (indent, direct, key, objidpart) = (m.group(1), m.group(2), m.group(3), m.group(6))
                objid = int(objidpart) if objidpart else None
                id = id_for_indent[indent] = self.get_next_id()
                self.setDirective(indent, key, direct)
                self.directive[id] = self.getDirectives(indent, key)
                call = [ id, key, None, None ]
                line = lines.next()
                m = re.match("^(\s*)ARGS (.*?)\s*$", line)
                if m:
                    call[2] = m.group(2)
                line = lines.next()
                m = re.match("^(\s*)KWARGS (.*?)\s*$", line)
                if m:
                    call[3] = m.group(2)
                self.indent = indent
                if objid:
                    self.call_object(id, objid)
                self.call_enter(*call)
                continue
            m = re.match("^(\s*)(MOCK|SKIP|TEST) (.*?)\s*$", line)
            if m:
                (indent, directive, key) = (m.group(1), m.group(2), m.group(3))
                self.setDirective(indent, key, directive)
                continue
            m = re.match("^(\s*)(RETURN|RAISE) (.*?)\s*$", line)
            if m:
                indent = m.group(1)
                self.indent = indent
                id = id_for_indent[indent]
                if m.group(2) == "RETURN":
                    self.call_result(id, m.group(3), None)
                elif m.group(2) == "RAISE":
                    self.call_result(id, None, m.group(3))
                id_for_indent[indent] = None
                self.invalidateDirectives(indent)
                continue
            raise Exception("ERROR INVALID LINE " + line)

class CallHistory(CallHistoryBuilder):

    def __init__(self):
        super(CallHistory, self).__init__()
        self.caller = {}
        self.stack = Stack()
        self.reachability = Reachability()

    def get_indent(self):
        return self.stack.get_indent()

    def call_enter(self, id, key, s_args, s_kwargs):
        # TODO eliminate this indent thing -- use own stack or something
        self.linear.append((self.get_indent(), 'enter', id, ))
        self.calls[id] = [key, s_args, s_kwargs]
        try:
            self.caller[id] = self.stack.top()[0]
        except TypeError:
            self.caller[id] = None
        self.reachability.updatePathTo(key, enumerate(reversed(self.stack)))
        self.stack.append((id, key, s_args, s_kwargs, ))

    def call_result(self, id, s_res, s_exc):
        self.results[id] = [s_res, s_exc]
        self.stack.popWhile(lambda item: item[0] != id)
        self.linear.append((self.get_indent(), 'result', id, ))

    def iterCalls(self, keyFilter=None):
        for (id, (key, s_args, s_kwargs)) in self.calls.iteritems():
            if keyFilter and key != keyFilter:
                continue
            (s_res, s_exc) = self.results[id]
            yield (id, key, s_args, s_kwargs, s_res, s_exc)

class TestCodegen:

    def __init__(self, callhistory, marshal):
        self.callhistory = callhistory
        self.marshal = marshal

    def gen_func_name(self, *parts):
        return "_".join(map(lambda str: str.replace('.', '_'), parts))

    def unserialize_code(self, serialized):
        return serialized

    def mock_code(self, something):
        code = ""
        for key in set([item[0] for item in self.callhistory.calls.itervalues()]):
            mock_func_name = self.gen_func_name("mock", key)
            code += "def " + mock_func_name + "(*args, **kwargs):\n"
            for (id, key, s_args, s_kwargs, s_res, s_exc) in self.callhistory.iterCalls(keyFilter=key):
                c_args = self.unserialize_code(s_args or self.marshal.empty_list())
                c_kwargs = self.unserialize_code(s_kwargs or self.marshal.empty_dict())
                c_ret = self.unserialize_code(s_res or self.marshal.none())
                code += "  if args == " + c_args + " and kwargs == " + c_kwargs + ":\n"
                if self.marshal.is_exception(s_exc):
                    code += "    raise " + s_exc + "\n"
                else:
                    code += "    return " + c_ret + "\n"
            code += "\n"
        return code

    def mock_setup_code(self, functions_to_mock):
        code = ""
        for orig_func_name in functions_to_mock:
            old_func_name = self.gen_func_name("old", orig_func_name)
            mock_func_name = self.gen_func_name("mock", orig_func_name)
            code += "    " + old_func_name + " = " + orig_func_name + "\n"
            code += "    " + orig_func_name + " = " + mock_func_name + "\n"
        return code

    def mock_teardown_code(self, functions_to_mock):
        code = ""
        for orig_func_name in functions_to_mock:
            old_func_name = self.gen_func_name("old", orig_func_name)
            code += "    " + orig_func_name + " = " + old_func_name + "\n"
        return code

    def c_call_function(self, key, s_args, s_kwargs):
        args_code = ""
        has_args = not self.marshal.is_empty(s_args)
        if has_args:
            s_args_code = s_args[1:-1] # FIX hack
            if s_args_code[-1] == ",":
                s_args_code = s_args_code[:-1]
            args_code += s_args_code
        has_kwargs = not self.marshal.is_empty(s_kwargs)
        if has_args and has_kwargs:
            args_code += ", "
        if has_kwargs:
            args_code += "**" + self.unserialize_code(s_kwargs)
        return self.c_funcref_by_key(key) + "(" + args_code + ")"

    def c_funcref_by_key(self, key):
        kk = key.split(".")
        if self.is_object_method(key):
            return self.gen_obj_name(key) + "." + kk[2]
        if self.is_module_function(key):
            return key
        assert False, "Unknown key type: " + key

    def is_object_method(self, key):
        kk = key.split(".")
        return len(kk) == 3

    def is_module_function(self, key):
        kk = key.split(".")
        return len(kk) == 2

    def gen_obj_name(self, key):
        kk = key.split(".")
        return "instanceof" + kk[1]

    def get_object_info(self, id, key):
        object_name = self.gen_obj_name(key)
        kk = key.split(".")
        module_name = kk[0]
        class_name = kk[1]
        consructor_args = None
        return (object_name, class_name, module_name, consructor_args)

    def c_replay_object(self, id, key):
        (object_name, class_name, module_name, consructor_args) = self.get_object_info(id, key)
        code = ""
        code += "    import " + module_name + "\n"
        code += "    " + object_name + " = " + module_name + "." + class_name + "(" + ( repr(consructor_args) if consructor_args else "") + ")\n"
        if self.callhistory.object_calls.get(id):
            objid = self.callhistory.object_calls[id]
            code += "    # object id " + str(objid) + "\n"
            for (old_id, old_key, old_s_args, old_s_kwargs, old_s_res, old_s_exc) in self.get_object_history_until(id, objid):
                code += "    " + self.c_call_function(old_key, old_s_args, old_s_kwargs) + "\n"
        return code

    def get_object_history_until(self, callid, objid):
        for tupl in self.callhistory.iterCalls():
            if tupl[0] >= callid:
                break
            if self.callhistory.object_calls.get(tupl[0], None):
                yield tupl

    def test_code(self):
        code =  "import unittest \n" + \
                "from ent import * \n\n" + \
                "import ent \n\n"
                # TODO generate import code
        mockmap = {}
        for (id, key, s_args, s_kwargs, s_res, s_exc) in self.callhistory.iterCalls():
            if self.callhistory.isMockable(id):
                try:
                    mockmap[self.callhistory.caller[id]].append(id)
                except KeyError:
                    mockmap[self.callhistory.caller[id]] = [id]
        code += self.mock_code(set())
        code += "class TestEnt(unittest.TestCase): \n\n" # TODO generate classname
        for (id, key, s_args, s_kwargs, s_res, s_exc) in self.callhistory.iterCalls():
            if not self.callhistory.isTestable(id):
                continue
            code += "  def " + self.gen_func_name("test", key, str(id)) + "(self):\n"
            # Arrange
            functions_to_mock = set([self.callhistory.calls[mockid][0] for mockid in mockmap[id]]) if id in mockmap else set()
            code += self.mock_setup_code(functions_to_mock)
            if self.marshal.is_exception(s_exc):
                code += "    try:\n"
                # Act
                code += "      " + self.c_call_function(key, s_args, s_kwargs) + "\n"
                # Assert
                code += "      self.fail('An exception should have been thrown.')\n"
                code += "    except Exception, e:\n"
                code += "      # expected: " + s_exc + "\n"
                code += "      pass\n"
            else:
                if self.is_object_method(key):
                    code += self.c_replay_object(id, key)
                # Act
                code += "    actual = " + self.c_call_function(key, s_args, s_kwargs) + "\n"
                # Assert
                code += "    expected = " + self.unserialize_code(s_res) + "\n"
                code += "    self.assertEqual(expected, actual)\n"
            code += self.mock_teardown_code(functions_to_mock)
            code += "\n"
        code += "if __name__ == '__main__': \n" + \
                "  unittest.main() \n"
        return code

import types
def is_instance_method(obj):
    """Checks if an object is a bound method on an instance.
       @author http://stackoverflow.com/users/107366/ants-aasma
    """
    if not isinstance(obj, types.MethodType):
        return False # Not a method
    if obj.im_self is None:
        return False # Method is not bound
    if issubclass(obj.im_class, type) or obj.im_class is types.ClassType:
        return False # Method is a classmethod
    return True

