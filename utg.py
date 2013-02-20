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
        id = get_next_id()
        s_args = Repo.marshal().serialize(args)
        s_kwargs = Repo.marshal().serialize(kwargs)
        key = func.__name__ # TODO generate a unique, unambiguous key for the functions
        Repo.callhistory().log_call_enter(id, key, s_args if args else None, s_kwargs if kwargs else None)
        Repo.reachability().updatePathTo(key, Repo.stack().items())
        Repo.stack().push((id, key, s_args, s_kwargs, ))
        try:
            ret = func(*args, **kwargs)
            s_ret = Repo.marshal().serialize(ret)
            s_e = None
            Repo.callhistory().log_call_return(id, s_ret)
        except Exception, e:
            s_ret = None
            s_e = Repo.marshal().serialize(e)
            Repo.callhistory().log_call_raise(id, s_e)
        (popid, popkey, s_args, s_kwargs) = Repo.stack().popWhile(lambda item: item[0] != id)
        Repo.callhistory().append(id, popkey, s_args, s_kwargs, s_ret, s_e)
        return ret
    return func2

next_id = 1
indent_unit = "    "

class AbstractMarshal:
    def serialize(self, obj): pass
    def unserialize(self, obj): pass
    def unserialize_code(self, serialized): pass
    def freeze(self, obj):
        return self.unserialize_code(self.serialize(obj))

class ReprMarshal (AbstractMarshal):
    def serialize(self, obj):
        return repr(obj)

    def unserialize(self, obj):
        return eval(obj)

    def unserialize_code(self, serialized):
        return serialized

class Stack:
    def __init__(self):
        self._list = []

    def push(self, obj):
        self._list.append(obj)

    def pop(self):
        return self._list.pop()

    def popWhile(self, callback):
        item = self.pop()
        while self.len() > 0 and callback(item):
            item = self.pop()
        if callback(item):
            raise Error("Stack item not found")
        return item

    def len(self):
        return len(self._list)

    def items(self):
        i = self.len()
        for item in self._list:
            yield (i, item)
            i -= 1

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
    return "".join([ indent_unit for i in range(Repo.stack().len())])

class CallHistory:

    def __init__(self):
        self.call_info = {}

    def log_call_enter(self, id, key, s_args, s_kwargs):
        print get_indent() + "CALL " + key
        if (s_args):
            print get_indent() + "ARGS " + s_args
        if (s_kwargs):
            print get_indent() + "KWARGS " + s_kwargs

    def log_call_return(self, id, s_ret):
        print get_indent() + "RETURN " + s_ret

    def log_call_raise(self, s_e):
        print get_indent() + "RAISE " + s_e

    def keys(self):
        return self.call_info.keys()

    def append(self, id, key, args, kwargs, ret=None, exc=None):
        if not key in self.keys():
            self.call_info[key] = []
        self.call_info[key].append((id, key, args, kwargs, ret, exc))

    def iterCalls(self, keyFilter=None):
        for key in self.call_info:
            if keyFilter and key != keyFilter:
                continue
            for (id, key, s_args, s_kwargs, s_ret, s_exc) in self.call_info[key]:
                yield (key, id, key, s_args, s_kwargs, s_ret, s_exc)

# TODO extract codegen class
def mock_code():
    code = ""
    for key in Repo.callhistory().keys():
        funcname = key
        code += "  def mock_" + key + "(*args, **kwargs):\n"
        for (akey, id, key, s_args, s_kwargs, s_ret, s_exc) in Repo.callhistory().iterCalls(keyFilter=key):
            c_args = Repo.marshal().unserialize_code(s_args)
            c_kwargs = Repo.marshal().unserialize_code(s_kwargs)
            c_ret = Repo.marshal().unserialize_code(s_ret)
            code += "    if args == " + c_args + " and kwargs == " + c_kwargs + ":\n"
            code += "      return " + c_ret + "\n\n"
    return code

def call_func_code(c_key, c_args, c_kwargs):
    code = c_key + "("
    has_args = c_args != "()"
    if has_args:
        code += c_args[1:-2]
    has_kwargs = (c_kwargs != "{}")
    if has_args and has_kwargs:
        code += ", "
    if has_kwargs:
        code += "**" + c_kwargs
    return code

def test_code():
    code =  "import unittest \n" + \
            "from ent import * \n\n" + \
            "class TestEnt(unittest.TestCase): \n\n"
    for (key, id, key, s_args, s_kwargs, s_ret, s_exc) in Repo.callhistory().iterCalls():
        c_args = Repo.marshal().unserialize_code(s_args)
        c_kwargs = Repo.marshal().unserialize_code(s_kwargs)
        c_ret = Repo.marshal().unserialize_code(s_ret)
        code += "  def test_" + key + "_" + str(id) + "(self):\n"
        code += "    actual = " + call_func_code(key, c_args, c_kwargs) + ")\n"
        code += "    expected = " + c_ret + "\n"
        code += "    self.assertEqual(expected, actual)\n\n"
    code += "if __name__ == '__main__': \n" + \
            "  unittest.main() \n"
    return code

