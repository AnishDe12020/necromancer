#!/usr/bin/env bash
# End to end: fetch claims -> claim chart -> failing evals -> run against the reference
# build (ACCEPT) and against a generic CRUD app (REJECT).
set -u
cd "$(dirname "$0")"
PID=${1:-US7669123B2}
OFFLINE=${OFFLINE:+--offline}

echo "=================== unit tests (extractor + HTML parser)"
python3 -m pytest -q tests || exit 1

echo; echo "=================== $PID vs reference feed engine"
python3 -m necro run "$PID" $OFFLINE --impl impls.us7669123.feed_engine
ref=$?

echo; echo "=================== $PID vs generic CRUD app (control, should REJECT)"
python3 -m necro run "$PID" $OFFLINE --impl impls.crud_baseline.app
crud=$?

echo
if [ $ref -eq 0 ] && [ $crud -ne 0 ]; then
  echo "DEMO OK: reference accepted, CRUD rejected"
else
  echo "DEMO FAILED: reference=$ref crud=$crud"; exit 1
fi
