# set up the tool
import utg
utg.capture_mode()

# instrumentalize the target module
# avoid testing functions using random numbers
import ent
utg.capture_module_functions(ent, exclude="rsa_encrypt|random_prime|randcurve|str_to_numlist|elliptic_curve_method|elgamal|_init|sqrtmod|dh_init")

# run example cases
ent.powermod(2,25,30)
ent.powermod(19,12345,100)
import ent_less_examples

# write out the capture log, without generating and annotating the capture log
utg.write_test_code('test_ent_less_examples.py')

# run the generated test case
from test_ent_less_examples import TestEnt
import unittest
unittest.TextTestRunner().run(unittest.TestLoader().loadTestsFromTestCase(TestEnt))

