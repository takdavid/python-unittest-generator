import utg
utg.test_mode()

import ent

l = open('capture.log', 'r')
for line in l.readlines():
    utg.Repo.callhistory().log.append(line)
l.close()
utg.Repo.callhistory().readCalls()

f = open('test_ent.py', 'w')
f.write(utg.test_code())
f.close()

print repr(utg.Repo.reachability().matrix())

