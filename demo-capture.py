# set up the tool
import utg
utg.capture_mode()

# instrumentalize the target module
import ent
utg.capture_module_functions(ent)

# run example cases
ent.factor(2313)
ent.primitive_root(2311)

# instrumentalize one function here
from utg import capture
@capture
def raising_func():
    raise Exception("This should be raised")

# run the example
try:
    raising_func()
except:
    pass

# class method capture
import ent_class
E = ent_class.Ent()
utg.capture_object_methods(E)
# TODO utg.capture_object_properties(E)
# E.the_answer = 42
# TODO:
X = ent_class.InsideEnt()
utg.capture_object_methods(X)
X.x("X")
# E.x(X)
E.enable()
E.factor(2313)
E.primitive_root(2311)

# write out the capture log
utg.write_capture_log('capture.log')

