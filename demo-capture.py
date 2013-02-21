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

# write out the capture log
utg.write_capture_log('capture.log')

