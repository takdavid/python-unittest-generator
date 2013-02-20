import utg
utg.capture_mode()

import ent

n = 2313
ent.factor(n)

n = 2311
ent.primitive_root(n)

utg.Repo.callhistory().calls = {}
utg.Repo.callhistory().results = {}
utg.Repo.callhistory().readCalls()

f = open('test_ent.py', 'w')
f.write(utg.test_code())
f.close()

print repr(utg.Repo.reachability().matrix())
