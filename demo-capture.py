import utg
utg.capture_mode()

import ent

n = 2313
ent.factor(n)

n = 2311
ent.primitive_root(n)

f = open('capture.log', 'w')
for line in utg.Repo.callhistory().log:
    f.write(line + "\n")
f.close()

# TODO save reachability matrix if needed
print repr(utg.Repo.reachability().matrix())
