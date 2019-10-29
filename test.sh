#!/usr/bin/env bash
set -e

# ARRANGE

OLDDIR=$(pwd)
mkdir testproject
cd testproject

function touch_py() { echo '1/1' > $1; }
mkdir -p importable_package/subpackage
touch_py importable_package/subpackage/__init__.py
mkdir -p importable_package/tests
touch_py importable_package/tests/__init__.py
touch_py importable_package/__init__.py

mkdir -p non-importable-dir/burried_package/burried_subpackage/
touch_py non-importable-dir/burried_package/burried_subpackage/__init__.py
touch_py non-importable-dir/burried_package/__init__.py
touch_py non-importable-dir/unreachable_script.py

# TODO this is only to fake the update of pytest.ini/PYTHONPATH
cat >> pytest.ini <<PYTESTINI;
[pytest]
python_paths =
    non-importable-dir
PYTESTINI

cat >.coveragerc <<COVERAGERC;
[run]
omit = $VIRTUAL_ENV/*
COVERAGERC

export COVERAGE_FILE=.coverage

coverage run $(which pytest) || true

# ACT

python ../boil.py

# ASSERT

function assert_f() { test -f $1 || (echo Missing $1; exit 1) }

assert_f importable_package/tests/test_subpackage.py
assert_f importable_package/tests/test_importable_package.py

assert_f non-importable-dir/burried_package/tests/test_burried_subpackage.py
assert_f non-importable-dir/tests/test_unreachable_script.py

coverage run $(which pytest)

# CLEANUP

cd $OLDDIR
rm -rf testproject
