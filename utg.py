""" unit test generator """

runmode = "test" # "capture" or "test"

def capture_mode():
    global runmode
    runmode = "capture"

def test_mode():
    global runmode
    runmode = "test"

def capture(func):
    """ Decorator which captures the args and the return values of the function. """
    global runmode
    if runmode != "capture":
        return func
    def func2(*args, **kwargs):
        key = func.__module__ + "." + func.__name__ # TODO generate a unique, unambiguous key for the functions
        serialize = Repo.marshal().serialize
        id = call_enter(key, serialize(args), serialize(kwargs))
        try:
            ret = func(*args, **kwargs)
            call_result(id, serialize(ret), serialize(None))
            return ret
        except Exception, exc:
            call_result(id, serialize(None), serialize(exc))
            raise exc
    return func2

def call_enter(key, s_args, s_kwargs):
    id = Repo.callhistory().get_next_id()
    Repo.callhistory().call_enter(id, key, s_args, s_kwargs)
    return id

def call_result(id, s_res, s_exc):
    Repo.callhistory().call_result(id, s_res, s_exc)

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

class Repo:

    _marshal = None
    @staticmethod
    def marshal():
        if not isinstance(Repo._marshal, AbstractMarshal):
            Repo._marshal = ReprMarshal()
        return Repo._marshal;

    _stack = None
    @staticmethod
    def stack():
        if not isinstance(Repo._stack, Stack):
            Repo._stack = Stack()
        return Repo._stack;

    _reachability = None
    @staticmethod
    def reachability():
        if not isinstance(Repo._reachability, Reachability):
            Repo._reachability = Reachability()
        return Repo._reachability;

    _callhistory = None
    @staticmethod
    def callhistory():
        if not isinstance(Repo._callhistory, CallHistory):
            Repo._callhistory = CallHistory()
        return Repo._callhistory;

def capture_log():
    hw = CallHistoryWriter()
    Repo.callhistory().replay(hw)
    return hw.log

input_lines = []

def parse_log_line(line):
    input_lines.append(line)

def parse_close():
    pass

class CallHistoryBuilder(object):

    def __init__(self):
        self.next_id = 0
        self.calls = {}
        self.results = {}
        self.linear = []
        self.log = []
        self.indent = ""

    def replay(self, that):
        for (indent, what, id) in self.linear:
            that.indent = indent
            if what == 'enter':
                that.call_enter(id, * self.calls[id])
            elif what == 'result':
                that.call_result(id, * self.results[id])

    def get_next_id(self):
        id = self.next_id
        self.next_id += 1
        return id

    def get_indent(self):
        return self.indent

    def call_enter(self, id, key, s_args, s_kwargs):
        self.calls[id] = [key, s_args, s_kwargs]
        self.linear.append((self.get_indent(), 'enter', id, ))

    def call_result(self, id, s_res, s_exc):
        self.results[id] = [s_res, s_exc]
        self.linear.append((self.get_indent(), 'result', id, ))

class CallHistoryWriter(CallHistoryBuilder):

    def __init__(self):
        super(CallHistoryWriter, self).__init__()

    def write(self, str):
        self.log.append(str)

    def call_enter(self, id, key, s_args, s_kwargs):
        self.write(self.get_indent() + "CALL " + key)
        self.write(self.get_indent() + "ARGS " + s_args)
        self.write(self.get_indent() + "KWARGS " + s_kwargs)

    def call_result(self, id, s_res, s_exc):
        if s_exc == "None":
            self.write(self.get_indent() + "RETURN " + s_res)
        else:
            self.write(self.get_indent() + "RAISE " + s_exc)

class CallHistoryParser(CallHistoryBuilder):

    def __init__(self):
        super(CallHistoryParser, self).__init__()
        self._parse_directives = {}
        self.directive = {}

    def isTestable(self, id):
        return "TEST" in self.directive[id] or not "SKIP" in self.directive[id]

    def isMockable(self, id):
        return "MOCK" in self.directive[id]

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

    def readCalls(self):
        """ parse annotated call history """
        import re
        id_for_indent = {}
        lines = iter(self.log)
        for line in lines:
            m = re.match("^(\s*)((?:SKIP|TEST)?) *?CALL (.*?)\s*$", line)
            if m:
                (indent, direct, key) = (m.group(1), m.group(2), m.group(3))
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

    def get_indent(self):
        return Repo.stack().get_indent()

    def call_enter(self, id, key, s_args, s_kwargs):
        # TODO eliminate this indent thing -- use own stack or something
        self.linear.append((self.get_indent(), 'enter', id, ))
        self.calls[id] = [key, s_args, s_kwargs]
        try:
            self.caller[id] = Repo.stack().top()[0]
        except TypeError:
            self.caller[id] = None
        Repo.reachability().updatePathTo(key, enumerate(reversed(Repo.stack())))
        Repo.stack().append((id, key, s_args, s_kwargs, ))

    def call_result(self, id, s_res, s_exc):
        self.results[id] = [s_res, s_exc]
        Repo.stack().popWhile(lambda item: item[0] != id)
        self.linear.append((self.get_indent(), 'result', id, ))

    def keys(self):
        return set([item[0] for item in self.calls.itervalues()])

    def iterCalls(self, keyFilter=None):
        for (id, (key, s_args, s_kwargs)) in self.calls.iteritems():
            if keyFilter and key != keyFilter:
                continue
            (s_res, s_exc) = self.results[id]
            yield (id, key, s_args, s_kwargs, s_res, s_exc)

def test_code():
    global input_lines
    hr = CallHistoryParser()
    hr.log = input_lines
    input_lines = []
    hr.readCalls()
    hr.replay(Repo.callhistory())
    g = TestCodegen(Repo.callhistory(), hr)
    return g.test_code()

class TestCodegen:

    def __init__(self, callhistory, historyreader):
        self.callhistory = callhistory
        self.historyreader = historyreader

    def gen_func_name(self, *parts):
        return "_".join(map(lambda str: str.replace('.', '_'), parts))

    def unserialize_code(self, serialized):
        return serialized

    # TODO extract codegen class
    def mock_code(self, something):
        code = ""
        marshal = Repo.marshal()
        for key in self.callhistory.keys():
            mock_func_name = self.gen_func_name("mock", key)
            code += "def " + mock_func_name + "(*args, **kwargs):\n"
            for (id, key, s_args, s_kwargs, s_res, s_exc) in self.callhistory.iterCalls(keyFilter=key):
                c_args = self.unserialize_code(s_args or marshal.empty_list())
                c_kwargs = self.unserialize_code(s_kwargs or marshal.empty_dict())
                c_ret = self.unserialize_code(s_res or marshal.none())
                code += "  if args == " + c_args + " and kwargs == " + c_kwargs + ":\n"
                if marshal.is_exception(s_exc):
                    code += "    raise " + s_exc + "\n"
                else:
                    code += "    return " + c_ret + "\n"
            code += "\n"
        return code

    def mock_setup_code(self, functions_to_mock):
        code = ""
        marshal = Repo.marshal()
        for orig_func_name in functions_to_mock:
            old_func_name = self.gen_func_name("old", orig_func_name)
            mock_func_name = self.gen_func_name("mock", orig_func_name)
            code += "    " + old_func_name + " = " + orig_func_name + "\n"
            code += "    " + orig_func_name + " = " + mock_func_name + "\n"
        return code

    def mock_teardown_code(self, functions_to_mock):
        code = ""
        marshal = Repo.marshal()
        for orig_func_name in functions_to_mock:
            old_func_name = self.gen_func_name("old", orig_func_name)
            code += "    " + orig_func_name + " = " + old_func_name + "\n"
        return code

    def c_call_function(self, marshal, key, s_args, s_kwargs):
        code = ""
        has_args = not marshal.is_empty(s_args)
        if has_args:
            code += s_args[1:-2] # FIX hack
        has_kwargs = not marshal.is_empty(s_kwargs)
        if has_args and has_kwargs:
            code += ", "
        if has_kwargs:
            code += "**" + self.unserialize_code(s_kwargs)
        return key + "(" + code + ")"

    def test_code(self):
        marshal = Repo.marshal()
        code =  "import unittest \n" + \
                "from ent import * \n\n" + \
                "import ent \n\n"
        mockmap = {}
        for (id, key, s_args, s_kwargs, s_res, s_exc) in self.callhistory.iterCalls():
            if self.historyreader.isMockable(id):
                try:
                    mockmap[self.callhistory.caller[id]].append(id)
                except KeyError:
                    mockmap[self.callhistory.caller[id]] = [id]
        code += self.mock_code(set())
        code += "class TestEnt(unittest.TestCase): \n\n"
        for (id, key, s_args, s_kwargs, s_res, s_exc) in self.callhistory.iterCalls():
            if not self.historyreader.isTestable(id):
                continue
            code += "  def " + self.gen_func_name("test", key, str(id)) + "(self):\n"
            functions_to_mock = set([self.callhistory.calls[mockid][0] for mockid in mockmap[id]]) if id in mockmap else set()
            code += self.mock_setup_code(functions_to_mock)
            if marshal.is_exception(s_exc):
                code += "    try:\n"
                code += "      " + self.c_call_function(marshal, key, s_args, s_kwargs) + "\n"
                code += "      self.fail('An exception should have been thrown.')\n"
                code += "    except Exception, e:\n"
                code += "      # expected: " + s_exc + "\n"
                code += "      pass\n"
            else:
                code += "    actual = " + self.c_call_function(marshal, key, s_args, s_kwargs) + "\n"
                code += "    expected = " + self.unserialize_code(s_res) + "\n"
                code += "    self.assertEqual(expected, actual)\n"
            code += self.mock_teardown_code(functions_to_mock)
            code += "\n"
        code += "if __name__ == '__main__': \n" + \
                "  unittest.main() \n"
        return code

