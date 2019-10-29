#!/usr/bin/env bash
set -e

# ARRANGE

function touch_py() { echo '1/1' > $1; }
mkdir -p testproject/importable_package/subpackage
touch_py testproject/importable_package/subpackage/__init__.py
mkdir -p testproject/importable_package/tests
touch_py testproject/importable_package/tests/__init__.py
touch_py testproject/importable_package/__init__.py

mkdir -p testproject/unimportable-dir/burried_package/burried_subpackage/tests
touch_py testproject/unimportable-dir/burried_package/burried_subpackage/tests/__init__.py
touch_py testproject/unimportable-dir/burried_package/__init__.py
touch_py testproject/unimportable-dir/unreachable_script.py

touch testproject/pytest.ini
export COVERAGE_FILE=.coverage
cat >testproject/.coveragerc <<COVERAGERC;
[run]
omit = $VIRTUAL_ENV/*
COVERAGERC

cd testproject
coverage run $(which pytest) || true

# ACT

python ../boil.py

# ASSERT

coverage run $(which pytest)

cd ..
set -e
function assert_f() { test -f $1 || (echo Missing $1; exit 1) }

assert_f testproject/importable_package/tests/subpackage/test_subpackage.py
assert_f testproject/importable_package/tests/test_importable_package.py

assert_f testproject/unimportable-dir/burried_package/burried_subpackage/tests/test_burried_subpackage.py
assert_f testproject/unimportable-dir/test_unreachable_script.py

# CLEANUP

rm -rf testproject
