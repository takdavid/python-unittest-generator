""" unit test generator """

runmode = "test" # "capture" or "test"

def capture_mode():
    global runmode
    runmode = "capture"

def test_mode():
    global runmode
    runmode = "test"

next_id = 1
stack = []
indent_unit = "    "
reachability = {}

def get_next_id():
    global next_id
    id = next_id
    next_id += 1
    return id

def get_indent():
    global stack, indent_unit
    return "".join([ indent_unit for i in range(len(stack))])

def capture(func):
    """ Decorator which captures the args and the return values of the function. """
    global runmode
    if runmode != "capture":
        return func
    def func2(*args, **kwargs):
        id = get_next_id()
        call_enter(id, func.__name__, args, kwargs)
        ret = func(*args, **kwargs)
        call_return(id, ret)
        return ret
    return func2

mocks = { }
def append_mocks(funcname, args, kwargs, ret):
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
            code += "    if args == "+repr(args)+" and kwargs == "+repr(kwargs)+":\n"
            code += "      return "+repr(ret)+"\n\n"
    return code

tests = { }
def append_test(funcname, id, code):
    global tests
    key = funcname + "_" + str(id)
    if not key in tests:
        tests[key] = []
    tests[key].append(code)

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
    global stack
    global reachability
    depth = len(stack)
    for (prev_id, prev_funcname, prev_args, prev_kwargs) in stack:
        if not prev_funcname in reachability:
            reachability[prev_funcname] = {}
        if not funcname in reachability[prev_funcname]:
            reachability[prev_funcname][funcname] = depth;
        else:
            reachability[prev_funcname][funcname] = min(depth, reachability[prev_funcname][funcname])
    stack.append((id, funcname, args, kwargs))

def log_call_enter(id, funcname, args, kwargs):
    print get_indent() + "CALL ", funcname, "(*", repr(args), ", **", repr(kwargs), ")"

def call_return(id, ret):
    global stack
    (popid, funcname, args, kwargs) = stack.pop()
    while len(stack) > 0 and popid != id:
        print "WARNING, a return is lost"
        (popid, funcname, args, kwargs) = stack.pop()
    if popid != id:
        raise Error("Call #" + str(id) + " not found")
    log_call_return(id, ret)
    append_test(funcname, id, "    actual = " + funcname + "(*" + repr(args) + ", **" + repr(kwargs) + ")")
    append_test(funcname, id, "    expected = " + repr(ret))
    append_mocks(funcname, args, kwargs, ret)

def log_call_return(id, ret):
    print get_indent() + "RETURN ", repr(ret)

