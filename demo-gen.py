import utg
utg.test_mode()
parser = utg.CallHistoryParser()

import ent

l = open('capture.log', 'r')
parser.parse(l.readlines())
l.close()

f = open('test_ent.py', 'w')
f.write(utg.test_code(parser))
f.close()

