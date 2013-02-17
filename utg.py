""" unit test generator """

runmode = "test" # "capture" or "test"

def capture_mode():
    global runmode
    runmode = "capture"

def test_mode():
    global runmode
    runmode = "test"

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

def get_next_id():
    global next_id
    id = next_id
    next_id += 1
    return id

def get_indent():
    global indent_unit
    return "".join([ indent_unit for i in range(Repo.stack().len())])

def capture(func):
    """ Decorator which captures the args and the return values of the function. """
    global runmode
    if runmode != "capture":
        return func
    def func2(*args, **kwargs):
        id = get_next_id()
        call_enter(id, func.__name__, args, kwargs)
        ret = func(*args, **kwargs)
        # TODO try-except
        call_return(id, ret)
        return ret
    return func2

mocks = { }
def append_mocks(id, funcname, args, kwargs, ret):
    global mocks
    key = funcname
    if not key in mocks:
        mocks[key] = []
    mocks[key].append((args, kwargs, ret))

def mock_code():
    global mocks
    code = ""
    for key in mocks:
        funcname = key
        code += "  def mock_"+funcname+"(*args, **kwargs):\n"
        for (args, kwargs, ret) in mocks[key]:
            code += "    if args == "+Repo.marshal().freeze(args)+" and kwargs == "+Repo.marshal().freeze(kwargs)+":\n"
            code += "      return "+Repo.marshal().freeze(ret)+"\n\n"
    return code

tests = { }
def append_test(funcname, id, code):
    global tests
    key = funcname + "_" + str(id)
    if not key in tests:
        tests[key] = []
    tests[key].append(code)

def append_tests(id, funcname, args, kwargs, ret):
    append_test(funcname, id, "    actual = " + funcname + "(*" + Repo.marshal().freeze(args) + ", **" + Repo.marshal().freeze(kwargs) + ")")
    append_test(funcname, id, "    expected = " + Repo.marshal().freeze(ret))

def test_code():
    global tests
    code =  "import unittest \n" + \
            "from ent import * \n\n" + \
            "class TestEnt(unittest.TestCase): \n\n"
    for key in tests:
        code += "  def test_" + key + "(self):\n" + \
                "\n".join(tests[key]) + "\n" + \
                "    self.assertEqual(expected, actual)\n\n"
    code += "if __name__ == '__main__': \n" + \
            "  unittest.main() \n"
    return code

def call_enter(id, funcname, args, kwargs):
    log_call_enter(id, funcname, args, kwargs)
    for (depth, item) in Repo.stack().items():
        Repo.reachability().update(item[1], funcname, depth)
    Repo.stack().push((id, funcname, args, kwargs))

def log_call_enter(id, funcname, args, kwargs):
    print get_indent() + "CALL ", funcname, "(*", Repo.marshal().serialize(args), ", **", Repo.marshal().serialize(kwargs), ")"

def call_return(id, ret):
    (popid, funcname, args, kwargs) = Repo.stack().popWhile(lambda item: item[0] != id)
    log_call_return(id, ret)
    append_tests(id, funcname, args, kwargs, ret)
    append_mocks(id, funcname, args, kwargs, ret)

def log_call_return(id, ret):
    print get_indent() + "RETURN ", Repo.marshal().serialize(ret)

