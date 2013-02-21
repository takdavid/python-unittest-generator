import utg

# read the annotated capture log
utg.read_capture_log('capture.log')

# generate test code and write out to file
utg.write_test_code('test_ent.py')

