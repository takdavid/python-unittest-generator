# set up the tool
import utg
utg.capture_mode()

# instrumentalize the target module
import ent
utg.capture_module_functions(ent)

# run example cases
ent.powermod(2,25,30)
ent.powermod(19,12345,100)

# write out the capture log, without generating and annotating the capture log
utg.write_test_code('test_ent2.py')

# run the generated test case
from test_ent2 import TestEnt
import unittest
unittest.TextTestRunner().run(unittest.TestLoader().loadTestsFromTestCase(TestEnt))

