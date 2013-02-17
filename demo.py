import utg
utg.capture_mode()

import ent

n = 2313
factors = ent.factor(n)
print repr(factors)

n = 2311
a = ent.primitive_root(n)
print repr(a)

f = open('test_ent.py', 'w')
f.write(utg.test_code())
f.close()

print utg.mock_code()
print repr(utg.reachability)
