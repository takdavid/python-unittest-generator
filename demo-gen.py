import utg
utg.test_mode()

import ent

l = open('capture.log', 'r')
for line in l.readlines():
    utg.parse_log_line(line)
l.close()
utg.parse_close()

f = open('test_ent.py', 'w')
f.write(utg.test_code())
f.close()

print repr(utg.Repo.reachability().matrix())

