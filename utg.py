""" unit test generator """
import re
import types
import simplejson as json
from json import JSONEncoder

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
    return [getattr(obj, method) for method in dir(obj) if callable(getattr(obj, method)) and not method[0:2] == "__"]

def propertiesOf(obj):
    """ Return all properties of the argument. """
    return [(prop, getattr(obj, prop)) for prop in dir(obj) if not callable(getattr(obj, prop)) and not method[0:2] == "__"]

def capture_class(klass, re_exclude=None):
    """ Decorates everything in a class: constructors, static methods, instance methods, and properties (?) """
    capture_class_properties(klass, re_exclude)
    if hasattr(klass, "__init__"):
        originit = klass.__init__
        def initwrapper(self, *args, **kwargs):
            capture_object_methods(self, re_exclude)
            init = types.MethodType(originit, None, klass)
            init(self, *args, **kwargs)
        klass.__init__ = initwrapper
    else:
        def newinit(self):
            capture_object_methods(self, re_exclude)
        klass.__init__ = newinit

def capture_module_functions(mod, exclude=None):
    """ Decorates all functions of the module, except the imported and the explicitely excluded ones. """
    for fun in callablesOf(mod):
        if fun.__module__ == mod.__name__ and (not exclude or not re.match(exclude, fun.__name__)):
            setattr(mod, fun.__name__, capture(fun))

def capture_object_methods(obj, re_exclude=None):
    """ Decorates all functions of the object, except the explicitely excluded ones. """
    # TODO 1 do not decorate already decorated (~inherited) ones - decorator registry dict?
    for fun in callablesOf(obj):
        if (not re_exclude or not re.match(re_exclude, fun.__name__)):
            setattr(obj, fun.__name__, capture(fun))

# TODO this does not capture things like object.property.method(...)
def capture_class_properties(klass, re_exclude=None):
    """ Decorates all properties of the class. """
    # TODO 1 what if class has a __setattr__ already
    # TODO 1 re_exclude
    # TODO do not decorate already decorated ones
    serialize = Repo.marshal().serialize
    callhistory = Repo.callhistory()
    callkey = CallKey(klass.__module__, klass.__name__, "__setattr__")
    key = str(callkey)
    def _setattr_wrapper(self, name, value):
        # TODO lambda, functions
        # TODO generators
        if not callable(value):
            (value2,) = callhistory.replace_args([value])
            tick = callhistory.get_tick()
            callhistory.call_object(tick, id(self), key)
            callhistory.call_enter(tick, key, [name, value2], None)
            callhistory.call_result(tick, None, None)
        self.__dict__[name] = value
    klass.__setattr__ = types.MethodType(_setattr_wrapper, None, klass)

def capture_object_properties(obj, re_exclude=None):
    """ Decorates all properties of the object. """
    capture_class_properties(obj.__class__, re_exclude)

def capture(function):
    """ Decorator which captures the args and the return values or the exception of the function. """
    global runmode
    if runmode != "capture":
        return function
    # TODO do not decorate already decorated ones
    mode = None
    if is_bound_method(function):
        mode = 1
    elif is_module_function(function):
        mode = 2
    else:
        raise Exception("Unknown object to capture " + repr(function))
    serialize = Repo.marshal().serialize
    callhistory = Repo.callhistory()
    def wrapper(*args, **kwargs):
        tick = callhistory.get_tick()
        if mode == 1:
            callkey = CallKey(function.im_self.__module__, function.im_self.__class__.__name__, function.__name__)
            callhistory.call_object(tick, id(function.im_self), str(callkey))
        elif mode == 2:
            callkey = CallKey(function.__module__, None, function.__name__)
        else:
            raise Exception("Unknown object to capture " + repr(function))
            # TODO lambda
            # TODO generators
        args2 = callhistory.replace_args(args)
        kwargs2 = callhistory.replace_kwargs(kwargs)
        callhistory.call_enter(tick, str(callkey), serialize(args2), serialize(kwargs2))
        try:
            ret = function(*args, **kwargs)
            # TODO 1 ? (ret2,) = callhistory.replace_args([ret])
            callhistory.call_result(tick, serialize(ret) if ret is not None else None, None)
            return ret
        except Exception, exc:
            callhistory.call_result(tick, None, serialize(exc))
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
    hw = Repo.writer()
    Repo.callhistory().replay(hw)
    return hw.logLines()

# TODO def set_capture_log_writer(fileobj)

def write_capture_log(filename):
    """ Write out the capture log to a file. """
    f = open(filename, 'w')
    for line in gen_capture_log():
        f.write(line + "\n")
    f.close()

# TODO def read_capture_log(fileobj)

def read_capture_log(filename):
    """ Read in the capture log from a file. """
    parser = Repo.parser()
    l = open(filename, 'r')
    parser.parse(l.readlines())
    l.close()
    parser.replay(Repo.callhistory())

def gen_test_code():
    """ Generate the test code in a string. """
    return TestCodegen(Repo.callhistory(), Repo.marshal()).test_code()

# TODO def write_test_code(fileobj)

def write_test_code(filename):
    """ Write out the test code to a file. """
    f = open(filename, 'w')
    f.write(gen_test_code())
    f.close()


# helpers


def is_bound_method(obj):
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

def is_unbound_method(obj):
    if not isinstance(obj, types.MethodType):
        return False # Not a method
    if getattr(obj, "im_self") is not None:
        return False # Bound method
    return True

def is_module_function(obj):
    if hasattr(obj, "im_self"):
        return False # Bound method
    if hasattr(obj, "im_class") and (issubclass(obj.im_class, type) or obj.im_class is types.ClassType):
        return False # Method is a classmethod
    return True

# classes


class Repo:
    """ Factory and repository. """

    _marshal = None
    @staticmethod
    def marshal():
        if not isinstance(Repo._marshal, AbstractMarshal):
            Repo._marshal = JsonMarshal()
        return Repo._marshal

    _callhistory = None
    @staticmethod
    def callhistory():
        if not isinstance(Repo._callhistory, CallHistory):
            Repo._callhistory = CallHistory()
        return Repo._callhistory

    _writer = None
    @staticmethod
    def writer():
        Repo._writer = CallHistoryWriterJson()
        return Repo._writer

    _parser = None
    @staticmethod
    def parser():
        Repo._parser = CallHistoryParserJson()
        return Repo._parser

class AbstractMarshal:
    def serialize(self, obj): pass
    def unserialize(self, obj): pass


class JsonMarshal (AbstractMarshal, JSONEncoder):

    def encode(self, obj):
        if isinstance(obj, tuple):
            return {'__tuple__': obj}
        if isinstance(obj, list):
            return list([ self.encode(it) for it in obj ])
        return super(JsonMarshal, self).encode(obj)

    def default(self, obj):
        if hasattr(obj, "toJSON"):
            return obj.toJSON()
        else:
            return json.dumps(obj)

    def serialize(self, obj):
        if isinstance(obj, Exception):
            return json.dumps({ "__Exception": str(obj) })
        if obj == True:
            return "True"
        return self.encode(obj)

    def loads_hook(self, obj):
        if isinstance(obj, dict) and '__tuple__' in obj:
            return tuple(obj['__tuple__'])
        return obj

    def unserialize(self, jsonstring):
        # TODO serialize args directly to json as much as possible
        if not isinstance(jsonstring, str):
            return jsonstring
        if jsonstring == "null":
            return None
        obj = json.loads(jsonstring, object_hook=self.loads_hook)
        if isinstance(obj, dict) and "__Exception" in obj:
            return Exception(* obj["__Exception"])
        return obj

    def empty_list(self, obj):
        return "[]"

    def empty_dict(self, obj):
        return "{}"

    def none(self):
        return "null"

    def default_exception(self):
        return "Exception()"

    def is_empty(self, code):
        return not code or code in ("()", "[]", "{}", "''", '""', self.none())

    def is_exception(self, s_exc):
        return s_exc and s_exc != self.none()


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


class VarName(object):

    def __init__(self, name):
        self.name = str(name)

    def __repr__(self):
        return self.name

    def __str__(self):
        return self.name

    def toJSON(self):
        return self.name

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
            self.update(item[1], str(key), depth)

    def matrix(self):
        return self._reachability


class CallHistoryBuilder(object):

    def __init__(self):
        self.tick = 0
        self.calls = {}
        self.results = {}
        self.linear = []
        self.log = []
        self.indent = ""
        self.directive = {}
        self.object_id_for_tick = {}
        self.key_for_object_id = {}

    def replay(self, that):
        for (indent, what, tick) in self.linear:
            that.indent = indent
            if what == 'enter':
                if self.object_id_for_tick.get(tick):
                    objid = self.object_id_for_tick[tick]
                    that.call_object(tick, objid, self.key_for_object_id[objid])
                that.call_enter(tick, * self.calls[tick])
            elif what == 'result':
                that.call_result(tick, * self.results[tick])
        for tick in self.directive:
            that.directive[tick] = self.directive[tick]

    def logLines(self):
        return []

    def get_tick(self):
        tick = self.tick
        self.tick += 1
        return tick

    def get_indent(self):
        return self.indent

    def call_object(self, tick, objid, key):
        self.object_id_for_tick[tick] = objid
        self.key_for_object_id[objid] = key

    def call_enter(self, tick, key, s_args, s_kwargs):
        self.calls[tick] = [str(key), s_args, s_kwargs]
        self.linear.append((self.get_indent(), 'enter', tick, ))

    def call_result(self, tick, s_res, s_exc):
        self.results[tick] = [s_res, s_exc]
        self.linear.append((self.get_indent(), 'result', tick, ))

    def isTestable(self, tick):
        return tick not in self.directive or "TEST" in self.directive[tick] or not "SKIP" in self.directive[tick]

    def isMockable(self, tick):
        return tick in self.directive and "MOCK" in self.directive[tick]

    def is_captured_object(self, arg):
        return id(arg) in self.key_for_object_id

    def replace_args(self, args):
        args2 = []
        for arg in args:
            if isinstance(arg, list):
                arg = self.replace_args(arg)
            # TODO 1 deep replace for dict
            # TODO deep replace for other container types
            if self.is_captured_object(arg):
                args2.append("$" + str(id(arg)) + "$")
            else:
                args2.append(arg)
        if isinstance(args, tuple):
            return tuple(args2)
        return args2

    def replace_kwargs(self, kwargs):
        # TODO 1 deep replace
        kwargs2 = {}
        for (argname, argvalue) in kwargs.iteritems():
            if self.is_captured_object(argvalue):
                kwargs2[argname] = "$" + str(id(argvalue)) + "$"
            else:
                kwargs2[argname] = argvalue
        return kwargs2


class CallHistoryWriterJson(CallHistoryBuilder):

    def __init__(self):
        super(CallHistoryWriterJson, self).__init__()
        self.marshal = Repo.marshal()

    def write(self, str):
        self.log.append(str)

    def logLines(self):
        yield "["
        for line in self.log:
            yield line
        yield "]"

    def call_enter(self, tick, key, s_args, s_kwargs):
        obj = { "key" : str(key) }
        if self.object_id_for_tick.get(tick):
            objidpart = "$" + str(self.object_id_for_tick[tick]) + "$"
            obj["objid"] = objidpart
        if not self.marshal.is_empty(s_args):
            obj["args"] = s_args
        if not self.marshal.is_empty(s_kwargs):
            obj["kwargs"] = s_kwargs
        self.write(self.get_indent() + '"enter", ' + str(tick) + ", " + self.marshal.serialize(obj) + ",")

    def call_result(self, tick, s_res, s_exc):
        obj = { }
        if self.marshal.is_empty(s_exc):
            obj = { "return" : s_res }
        else:
            obj = { "raise" : s_exc }
        self.write(self.get_indent() + '"leave", ' + str(tick) + ", " + self.marshal.serialize(obj) + ",")


class CallHistoryWriter(CallHistoryBuilder):

    def __init__(self):
        super(CallHistoryWriter, self).__init__()
        self.marshal = Repo.marshal()

    def write(self, str):
        self.log.append(str)

    def logLines(self):
        return self.log

    def call_enter(self, tick, key, s_args, s_kwargs):
        if self.object_id_for_tick.get(tick):
            objidpart = "$" + str(self.object_id_for_tick[tick]) + "$"
        else:
            objidpart = ""
        self.write(self.get_indent() + "CALL " + str(key) + " " + objidpart)
        self.write(self.get_indent() + "ARGS " + s_args)
        self.write(self.get_indent() + "KWARGS " + s_kwargs)

    def call_result(self, tick, s_res, s_exc):
        if self.marshal.is_empty(s_exc):
            self.write(self.get_indent() + "RETURN " + s_res)
        else:
            self.write(self.get_indent() + "RAISE " + s_exc)


class CallHistoryParser(CallHistoryBuilder):

    def __init__(self):
        super(CallHistoryParser, self).__init__()
        self._parse_directives = {}
        self.marshal = Repo.marshal()

    def setDirective(self, indent, key, directive):
        if not directive:
            return
        key = str(key)
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
        key = str(key)
        if key in self._parse_directives and directive in self._parse_directives[key]:
            self._parse_directives[key][directive].remove(indent)

    def getDirectives(self, indent, key):
        dirs = set() 
        key = str(key)
        if key in self._parse_directives:
            for directive in self._parse_directives[key]:
                for ind in self._parse_directives[key][directive]:
                    if ind <= indent:
                        dirs.add(directive)
        return dirs

    def invalidateDirectives(self, indent, keyFilter=None):
        for key in self._parse_directives.keys():
            key = str(key)
            if not keyFilter or key == keyFilter:
                for directive in self._parse_directives[key].keys():
                    for ind in self._parse_directives[key][directive]:
                        if ind >= indent:
                            self._parse_directives[key][directive] = set()

    def parse(self, log):
        """ parse annotated call history """
        tick_for_indent = {}
        lines = iter(log)
        for line in lines:
            m = re.match("^(\s*)((?:SKIP|TEST)?) *?CALL (.*?) ((\$(.*)\$)?)\s*$", line)
            if m:
                (indent, direct, key, objidpart) = (m.group(1), m.group(2), m.group(3), m.group(6))
                objid = int(objidpart) if objidpart else None
                tick = tick_for_indent[indent] = self.get_tick()
                self.setDirective(indent, key, direct)
                self.directive[tick] = self.getDirectives(indent, key)
                call = [ tick, key, None, None ]
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
                    self.call_object(tick, objid, key)
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
                tick = tick_for_indent[indent]
                if m.group(2) == "RETURN":
                    self.call_result(tick, m.group(3), None)
                elif m.group(2) == "RAISE":
                    self.call_result(tick, None, m.group(3))
                tick_for_indent[indent] = None
                self.invalidateDirectives(indent)
                continue
            raise Exception("ERROR INVALID LINE " + line)


class CallHistoryParserJson(CallHistoryParser):

    def parse(self, log):
        """ parse annotated call history """
        tick_for_indent = {}
        lines = iter(log)
        for line in lines:
            if line.startswith("[") or line.startswith("]"):
                continue
            m = re.match("^(\s*)", line)
            indent = m.group(1)
            arr = self.marshal.unserialize("[" + line + "null]")
            if arr[0] == "enter":
                tick = arr[1]
                direct = arr[2].get("directive")
                key = arr[2].get("key")
                objidpart = arr[2].get("objid")
                objid = int(objidpart[1:-1]) if objidpart else None
                self.setDirective(indent, key, direct)
                self.directive[tick] = self.getDirectives(indent, key)
                call = [tick, key, arr[2].get("args"), arr[2].get("kwargs")]
                if objid:
                    self.call_object(tick, objid, key)
                self.call_enter(*call)
                continue
            elif arr[0] == "leave":
                tick = arr[1]
                self.call_result(tick, arr[2].get("return"), arr[2].get("raise"))
                tick_for_indent[indent] = None
                self.invalidateDirectives(indent)
                continue
            # TODO test this
            elif arr[0] == "directive":
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

    def call_enter(self, tick, key, s_args, s_kwargs):
        key = str(key)
        # TODO eliminate this indent thing -- use own stack or something
        self.linear.append((self.get_indent(), 'enter', tick, ))
        self.calls[tick] = [key, s_args, s_kwargs]
        try:
            self.caller[tick] = self.stack.top()[0]
        except TypeError:
            self.caller[tick] = None
        self.reachability.updatePathTo(key, enumerate(reversed(self.stack)))
        self.stack.append((tick, key, s_args, s_kwargs, ))

    def call_result(self, tick, s_res, s_exc):
        self.results[tick] = [s_res, s_exc]
        self.stack.popWhile(lambda item: item[0] != tick)
        self.linear.append((self.get_indent(), 'result', tick, ))

    def get_object_history_until(self, tick, objid):
        if not getattr(self, "object_history", False):
            self.build_object_history_cache()
        for tupl in self.object_history[objid]:
            if tupl[0] >= tick:
                break
            if self.object_id_for_tick.get(tupl[0], None) == objid:
                yield tupl

    def build_object_history_cache(self):
        self.object_history = {}
        for tupl in self.iterCalls():
            objid = self.object_id_for_tick.get(tupl[0], None)
            if objid:
                if objid in self.object_history:
                    self.object_history[objid].append(tupl)
                else:
                    self.object_history[objid] = [tupl]

    def iterCalls(self):
        for (tick, (key, s_args, s_kwargs)) in self.calls.iteritems():
            (s_res, s_exc) = self.results[tick]
            yield (tick, key, s_args, s_kwargs, s_res, s_exc)


# TODO 1 move this out to some config data

class TestBuilderInfo:

    def is_insideeffect(self, method_name, class_name, module_name, s_args, s_kwargs):
        if class_name == "Ent":
            if method_name in ["factor", "trial_division", "primitive_root", "powermod"]:
                return False
        return True

    def skip(self, method_name, class_name, module_name, s_args, s_kwargs):
        if method_name in ["setattr", "__setattr__"]:
            return True
        return False


class CallKey:

    def __init__(self, module_name, class_name, function_name):
        self.module_name = module_name
        self.class_name = class_name
        self.function_name = function_name

    @staticmethod
    def unserialize(key):
        kk = key.split(".")
        if len(kk) == 3:
            return CallKey(kk[0], kk[1], kk[2])
        if len(kk) == 2:
            return CallKey(kk[0], None, kk[1])
        assert False, "Unknown key type: " + key

    def serialize(self):
        return str(self)

    def __str__(self):
        return self.module_name + "." + (self.class_name + "." if self.class_name else "") + self.function_name

    def is_object_method(self):
        return self.class_name is not None

    def is_module_function(self):
        return self.class_name is None


class TestCodegen:

    def __init__(self, callhistory, marshal):
        self.callhistory = callhistory
        self.marshal = marshal
        self.import_modules = set()
        self.testbuilderinfo = TestBuilderInfo()

    def gen_func_name(self, *parts):
        return "_".join(map(lambda elem: str(elem).replace('.', '_'), parts))

    def unserialize_code(self, serialized):
        return str(serialized)

    def mock_code(self):
        code = ""
        for key in set([item[0] for item in self.callhistory.calls.itervalues()]):
            mock_func_name = self.gen_func_name("mock", key)
            code += "def " + mock_func_name + "(*args, **kwargs):\n"
            for (tick, _key, s_args, s_kwargs, s_res, s_exc) in self.callhistory.iterCalls():
                if _key != key:
                    continue
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

    def c_call_function(self, full_function_name, s_args, s_kwargs):
        args_code = ""
        has_args = not self.marshal.is_empty(s_args)
        if has_args:
            # TODO something like args_code += repr(self.marshal.unserialize(s_args))
            s_args_code = s_args[1:-1]
            if s_args_code[-1] == ",":
                s_args_code = s_args_code[:-1]
            args_code += s_args_code
        has_kwargs = not self.marshal.is_empty(s_kwargs)
        if has_args and has_kwargs:
            args_code += ", "
        if has_kwargs:
            # TODO something like args_code += repr(self.marshal.unserialize(s_kwargs))
            args_code += self.unserialize_code(s_kwargs)
        fn_parts = full_function_name.split(".")
        if len(fn_parts) == 2 and fn_parts[1] == "__setattr__":
            # TODO 1 switch to more natural x.y = z syntax here
            return "setattr(" + fn_parts[0] + ", " + args_code + ")"
        return full_function_name + "(" + args_code + ")"

    def c_replay_object(self, tick, objid):
        callkey = CallKey.unserialize(self.callhistory.key_for_object_id[objid])
        class_name = callkey.class_name
        module_name = callkey.module_name
        object_name = "instanceof" + class_name + str(objid)
        cache_key = str(objid) + "@" + str(tick)
        if self.replay_cache.get(cache_key):
            return ("", object_name)
        self.replay_cache[cache_key] = True
        constructor_args = None
        code = ""
        self.import_modules.add(module_name)
        code += "    " + object_name + " = " + module_name + "." + class_name + "(" + ( repr(constructor_args) if constructor_args else "") + ")\n"
        self.local_scope.add(object_name)
        # TODO optim: build is_insideeffect cache
        for (old_id, old_key, old_s_args, old_s_kwargs, old_s_res, old_s_exc) in self.callhistory.get_object_history_until(tick, objid):
            old_k = CallKey.unserialize(old_key)
            if self.testbuilderinfo.is_insideeffect(old_k.function_name, old_k.class_name, old_k.module_name, old_s_args, old_s_kwargs):
                (code2, old_s_args2) = self.c_replay_call_args(tick, old_s_args)
                code += code2
                (code2, old_s_kwargs2) = self.c_replay_call_kwargs(tick, old_s_kwargs)
                code += code2
                full_function_name = object_name + "." + old_k.function_name
                code += "    " + self.c_call_function(full_function_name, old_s_args2, old_s_kwargs2) + "\n"
        return (code, object_name)

    def is_object_reference(self, arg):
        return isinstance(arg, str) and len(arg) > 2 and arg[0] == "$" and arg[-1] == "$"

    def unserialize_object_reference(self, arg):
        return int(arg[1:-1])

    def replay_args(self, tick, args):
        code = ""
        args2 = []
        for arg in args:
            if isinstance(arg, list):
                (code2, arg) = self.replay_args(tick, arg)
                code += code2
            if self.is_object_reference(arg):
                objid = self.unserialize_object_reference(arg)
                (code2, object_name) = self.c_replay_object(tick, objid)
                code += code2
                args2.append(VarName(object_name))
            else:
                args2.append(repr(arg))
        return (code, args2)

    def c_replay_call_args(self, tick, old_s_args):
        args = self.marshal.unserialize(old_s_args) if old_s_args else []
        (code, args2) = self.replay_args(tick, args)
        # TODO 2 serialize not here
        return (code, "[" + ", ".join([ str(arg) for arg in args2 ]) + "]")

    def c_replay_call_kwargs(self, tick, old_s_kwargs):
        code = ""
        kwargs = self.marshal.unserialize(old_s_kwargs) if old_s_kwargs else {}
        kwargs2 = {}
        for (argname, argvalue) in kwargs.iteritems():
            if self.is_object_reference(argvalue):
                objid = self.unserialize_object_reference(argvalue)
                (code2, object_name) = self.c_replay_object(tick, objid)
                code += code2
                kwargs2[argname] = VarName(object_name)
            else:
                kwargs2[argname] = argvalue
        # TODO 2 serialize not here
        return (code, ", ".join([ str(argname) + "=" + str(argvalue) for (argname, argvalue) in kwargs2.iteritems() ]))

    def clear_replay_cache(self):
        self.replay_cache = {}

    def c_import_modules(self):
        if "__main__" in self.import_modules:
            self.import_modules.remove("__main__")
        return "\n".join([ "import " + module_name for module_name in self.import_modules ]) + "\n\n"

    def init_mockmap(self):
        self.mockmap = {}
        for tupl in self.callhistory.iterCalls():
            tick = tupl[0]
            if self.callhistory.isMockable(tick):
                try:
                    self.mockmap[self.callhistory.caller[tick]].append(tick)
                except KeyError:
                    self.mockmap[self.callhistory.caller[tick]] = [tick]

    def functions_to_mock(self, tick):
        if tick in self.mockmap:
            return set([self.callhistory.calls[mockid][0] for mockid in self.mockmap[tick]])
        else:
            return set()

    def test_code(self):
        return self.gen_test_file_code()

    def gen_test_file_code(self):
        code =  ""
        self.import_modules.add("unittest")
        self.init_mockmap()
        if len(self.mockmap):
            code += self.mock_code()
        code += self.gen_test_class_code()
        code += "if __name__ == '__main__': \n" + \
                "  unittest.main() \n"
        return self.c_import_modules() + code

    def gen_test_class_code(self):
        methods_code = ""
        # TODO different test cases
        for tupl in self.callhistory.iterCalls():
            (tick, key, s_args, s_kwargs, s_res, s_exc) = tupl
            callkey = CallKey.unserialize(key)
            if not self.callhistory.isTestable(tick):
                continue
            if self.testbuilderinfo.skip(callkey.function_name, callkey.class_name, callkey.module_name, s_args, s_kwargs):
                continue
            methods_code += self.gen_test_method_code(tick, key, s_args, s_kwargs, s_res, s_exc)
        if methods_code:
            code = "class TestAll(unittest.TestCase): \n\n" + methods_code
        else:
            code = ""
        return code

    def gen_test_method_code(self, tick, key, s_args, s_kwargs, s_res, s_exc):
        callkey = CallKey.unserialize(key)
        self.local_scope = set()
        self.clear_replay_cache()
        self.import_modules.add(callkey.module_name)
        code = "  def " + self.gen_func_name("test", callkey, str(tick)) + "(self):\n"
        # Arrange
        code += self.mock_setup_code(self.functions_to_mock(tick))
        # TODO 1 static class methods
        if callkey.is_object_method():
            (code2, object_name) = self.c_replay_object(tick, self.callhistory.object_id_for_tick.get(tick))
            full_function_name = object_name + "." + callkey.function_name
            code += code2
        else:
            full_function_name = callkey.module_name + "." + callkey.function_name
        (code2, s_args2) = self.c_replay_call_args(tick, s_args)
        code += code2
        (code2, s_kwargs2) = self.c_replay_call_kwargs(tick, s_kwargs)
        code += code2
        if self.marshal.is_exception(s_exc):
            code += "    try:\n"
            # Act
            code += "      " + self.c_call_function(full_function_name, s_args2, s_kwargs2) + "\n"
            # Assert
            code += "      self.fail('An exception should have been thrown.')\n"
            code += "    except Exception, e:\n"
            code += "      # expected: " + s_exc + "\n"
            code += "      pass\n"
        else:
            # Act
            code += "    actual = " + self.c_call_function(full_function_name, s_args2, s_kwargs2) + "\n"
            # Assert
            code += "    expected = " + self.unserialize_code(s_res) + "\n"
            code += "    self.assertEqual(expected, actual)\n"
        code += self.mock_teardown_code(self.functions_to_mock(tick))
        code += "\n"
        return code

