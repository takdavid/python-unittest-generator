import utg
from utg import capture
utg.capture_mode()

import ent

n = 2313
ent.factor(n)

n = 2311
ent.primitive_root(n)

@capture
def raising_func():
    raise Exception("This should be raised")
try:
    raising_func()
except:
    pass

f = open('capture.log', 'w')
for line in utg.capture_log():
    f.write(line + "\n")
f.close()

