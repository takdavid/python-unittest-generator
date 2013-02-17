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
        call_enter(id, func.__name__, args, kwargs)
        ret = func(*args, **kwargs)
        # TODO try-except
        call_return(id, ret)
        return ret
    return func2

def call_enter(id, funcname, args, kwargs):
    s_args = Repo.marshal().serialize(args)
    s_kwargs = Repo.marshal().serialize(kwargs)
    log_call_enter(id, funcname, s_args, s_kwargs)
    # TODO Reachability.updatePath()
    for (depth, item) in Repo.stack().items():
        Repo.reachability().update(item[1], funcname, depth)
    Repo.stack().push((id, funcname, s_args, s_kwargs, ))

def log_call_enter(id, funcname, s_args, s_kwargs):
    # TODO generate parsable history, perhaps in the call history class
    print get_indent() + "CALL ", funcname, "(*", s_args, ", **", s_kwargs, ")"

def call_return(id, ret):
    (popid, funcname, s_args, s_kwargs) = Repo.stack().popWhile(lambda item: item[0] != id)
    s_ret = Repo.marshal().serialize(ret)
    log_call_return(id, s_ret)
    append_call_info(id, funcname, s_args, s_kwargs, s_ret)

def log_call_return(id, s_ret):
    print get_indent() + "RETURN ", s_ret

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

# TODO extract call history class
call_info = { }
def append_call_info(id, funcname, args, kwargs, ret):
    global call_info
    key = funcname
    if not key in call_info:
        call_info[key] = []
    call_info[key].append((id, funcname, args, kwargs, ret))

# TODO extract codegen class
def mock_code():
    global call_info
    code = ""
    for key in call_info:
        funcname = key
        code += "  def mock_" + funcname + "(*args, **kwargs):\n"
        for (id, funcname, s_args, s_kwargs, s_ret) in call_info[key]:
            c_args = Repo.marshal().unserialize_code(s_args)
            c_kwargs = Repo.marshal().unserialize_code(s_kwargs)
            c_ret = Repo.marshal().unserialize_code(s_ret)
            code += "    if args == " + c_args + " and kwargs == " + c_kwargs + ":\n"
            code += "      return " + c_ret + "\n\n"
    return code

def test_code():
    global call_info
    code =  "import unittest \n" + \
            "from ent import * \n\n" + \
            "class TestEnt(unittest.TestCase): \n\n"
    for key in call_info:
        for (id, funcname, s_args, s_kwargs, s_ret) in call_info[key]:
            c_args = Repo.marshal().unserialize_code(s_args)
            c_kwargs = Repo.marshal().unserialize_code(s_kwargs)
            c_ret = Repo.marshal().unserialize_code(s_ret)
            code += "  def test_" + key + "_" + str(id) + "(self):\n"
            code += "    actual = " + funcname + "(*" + c_args + ", **" + c_kwargs + ")\n"
            code += "    expected = " + c_ret + "\n"
            code += "    self.assertEqual(expected, actual)\n\n"
    code += "if __name__ == '__main__': \n" + \
            "  unittest.main() \n"
    return code

