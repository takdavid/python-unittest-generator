#!/usr/bin/env bash
set -e

# ARRANGE

function touch_py() { echo '1/1' > $1; }
mkdir -p testproject/importable_package/subpackage
touch_py testproject/importable_package/subpackage/__init__.py
mkdir -p testproject/importable_package/tests
touch_py testproject/importable_package/tests/__init__.py
touch_py testproject/importable_package/__init__.py

mkdir -p testproject/non-importable-dir/burried_package/burried_subpackage/tests
touch_py testproject/non-importable-dir/burried_package/burried_subpackage/tests/__init__.py
touch_py testproject/non-importable-dir/burried_package/burried_subpackage/__init__.py
touch_py testproject/non-importable-dir/burried_package/__init__.py
touch_py testproject/non-importable-dir/unreachable_script.py

cat >> testproject/pytest.ini <<PYTESTINI;
[pytest]
python_paths =
    non-importable-dir
PYTESTINI

cat >testproject/.coveragerc <<COVERAGERC;
[run]
omit = $VIRTUAL_ENV/*
COVERAGERC

export COVERAGE_FILE=.coverage

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

assert_f testproject/non-importable-dir/burried_package/burried_subpackage/tests/test_burried_subpackage.py
assert_f testproject/non-importable-dir/test_unreachable_script.py

# CLEANUP

rm -rf testproject
