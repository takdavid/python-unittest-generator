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
    id = get_next_id()
    Repo.callhistory().write_enter(id, key, s_args, s_kwargs)
    Repo.callhistory().call_enter(id, key, s_args, s_kwargs)
    return id

def call_result(id, s_res, s_exc):
    Repo.callhistory().call_result(id, s_res, s_exc)
    Repo.callhistory().write_result(id, s_res, s_exc)

next_id = 1
indent_unit = "    "

class AbstractMarshal:
    def serialize(self, obj): pass
    def unserialize(self, obj): pass
    def unserialize_code(self, serialized): pass

class ReprMarshal (AbstractMarshal):
    def serialize(self, obj):
        return repr(obj)

    def unserialize(self, obj):
        return eval(obj)

    def unserialize_code(self, serialized):
        return serialized

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

def get_next_id():
    global next_id
    id = next_id
    next_id += 1
    return id

def get_indent():
    global indent_unit
    return "".join([ indent_unit for i in range(len(Repo.stack()))])

def set2d(ref, x, dx, y, value):
    if x not in ref:
        ref[x] = dx
    ref[x][y] = value

class CallHistory:

    def __init__(self):
        self.calls = {}
        self.caller = {}
        self.results = {}
        self.log = []
        self.directive = {}
        self._parse_directives = {}

    def call_enter(self, id, key, s_args, s_kwargs):
        self.calls[id] = [key, s_args, s_kwargs]
        try:
            self.caller[id] = Repo.stack().top()[0]
        except TypeError:
            self.caller[id] = None
        Repo.reachability().updatePathTo(key, enumerate(reversed(Repo.stack())))
        Repo.stack().append((id, key, s_args, s_kwargs, ))

    def write_enter(self, id, key, s_args, s_kwargs):
        self.write(get_indent() + "CALL " + key)
        self.write(get_indent() + "ARGS " + s_args)
        self.write(get_indent() + "KWARGS " + s_kwargs)

    def call_result(self, id, s_res, s_exc):
        self.results[id] = [s_res, s_exc]
        Repo.stack().popWhile(lambda item: item[0] != id)

    def write_result(self, id, s_res, s_exc):
        if s_exc == "None":
            self.write(get_indent() + "RETURN " + s_res)
        else:
            self.write(get_indent() + "RAISE " + s_exc)

    def keys(self):
        return set([item[0] for item in self.calls.itervalues()])

    def iterCalls(self, keyFilter=None):
        for (id, (key, s_args, s_kwargs)) in self.calls.iteritems():
            if keyFilter and key != keyFilter:
                continue
            (s_res, s_exc) = self.results[id]
            yield (id, key, s_args, s_kwargs, s_res, s_exc)

    def write(self, str):
        self.log.append(str)

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

    def readCalls(self, keyFilter=None):
        """ parse annotated call history """
        import re
        id_for_indent = {}
        lines = iter(self.log)
        for line in lines:
            m = re.match("^(\s*)((?:SKIP|TEST)?) *?CALL (.*?)\s*$", line)
            if m:
                (indent, direct, key) = (m.group(1), m.group(2), m.group(3))
                id = id_for_indent[indent] = get_next_id()
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
                id = id_for_indent[indent]
                if m.group(2) == "RETURN":
                    self.call_result(id, m.group(3), None)
                elif m.group(2) == "RAISE":
                    self.call_result(id, None, m.group(3))
                id_for_indent[indent] = None
                self.invalidateDirectives(indent)
                continue
            raise Exception("ERROR INVALID LINE " + line)

    def isTestable(self, id):
        return "TEST" in self.directive[id] or not "SKIP" in self.directive[id]

    def isMockable(self, id):
        return "MOCK" in self.directive[id]

def sanitize(key):
    return key.replace('.', '_')

# TODO extract codegen class
def mock_code(something):
    code = ""
    unserialize_code = Repo.marshal().unserialize_code
    for key in Repo.callhistory().keys():
        code += "def mock_" + sanitize(key) + "(*args, **kwargs):\n"
        for (id, key, s_args, s_kwargs, s_res, s_exc) in Repo.callhistory().iterCalls(keyFilter=key):
            (key, s_args, s_kwargs) = Repo.callhistory().calls[id]
            (s_res, s_exc) = Repo.callhistory().results[id]
            c_args = unserialize_code(s_args)
            c_kwargs = unserialize_code(s_kwargs)
            c_ret = unserialize_code(s_res)
            c_exc = unserialize_code(s_exc)
            code += "  if args == " + (c_args if c_args else "[]") + " and kwargs == " + (c_kwargs if c_kwargs else "{}") + ":\n"
            if not c_exc or c_exc == "None":
                code += "    return " + c_ret + "\n"
            else:
                code += "    raise " + c_exc + "\n"
        code += "\n"
    return code

def call_func_code(c_key, c_args, c_kwargs):
    code = c_key + "("
    has_args = (c_args and c_args != "()")
    if has_args:
        code += c_args[1:-2]
    has_kwargs = (c_kwargs and c_kwargs != "{}")
    if has_args and has_kwargs:
        code += ", "
    if has_kwargs:
        code += "**" + c_kwargs
    return code

def test_code():
    code =  "import unittest \n" + \
            "from ent import * \n\n" + \
            "import ent \n\n"
    unserialize_code = Repo.marshal().unserialize_code
    mockmap = {}
    callhistory = Repo.callhistory()
    for (id, key, s_args, s_kwargs, s_res, s_exc) in callhistory.iterCalls():
        if callhistory.isMockable(id):
            try:
                mockmap[callhistory.caller[id]].append(id)
            except KeyError:
                mockmap[callhistory.caller[id]] = [id]
    code += mock_code(set())
    code += "class TestEnt(unittest.TestCase): \n\n"
    for (id, key, s_args, s_kwargs, s_res, s_exc) in callhistory.iterCalls():
        if not callhistory.isTestable(id):
            continue
        c_args = unserialize_code(s_args)
        c_kwargs = unserialize_code(s_kwargs)
        c_ret = unserialize_code(s_res)
        c_exc = unserialize_code(s_exc)
        code += "  def test_" + sanitize(key) + "_" + str(id) + "(self):\n"
        if id in mockmap:
            for mockkey in set([callhistory.calls[mockid][0] for mockid in mockmap[id]]):
                code += "    old_" + sanitize(mockkey) + " = " + mockkey + "\n"
                code += "    " + mockkey + " = mock_" + sanitize(mockkey) + "\n"
        if not c_exc or c_exc == "None":
            code += "    actual = " + call_func_code(key, c_args, c_kwargs) + ")\n"
            code += "    expected = " + c_ret + "\n"
            code += "    self.assertEqual(expected, actual)\n"
        else:
            code += "    try:\n"
            code += "      " + call_func_code(key, c_args, c_kwargs) + ")\n"
            code += "      self.fail('An exception should have been thrown.')\n"
            code += "    except Exception, e:\n"
            code += "      # expected: " + s_exc + "\n"
            code += "      pass\n"
        if id in mockmap:
            for mockkey in set([callhistory.calls[mockid][0] for mockid in mockmap[id]]):
                code += "    " + mockkey + " = old_" + sanitize(mockkey) + "\n"
        code += "\n"
    code += "if __name__ == '__main__': \n" + \
            "  unittest.main() \n"
    return code

