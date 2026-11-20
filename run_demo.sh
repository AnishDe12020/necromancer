#!/usr/bin/env bash
# End to end: fetch claims -> claim chart -> failing evals -> run against the reference
# build (ACCEPT), a generic CRUD app (REJECT), and a cheater that games v0 (v1 REJECT).
set -u
cd "$(dirname "$0")"
PID=${1:-US7669123B2}
OFFLINE=${OFFLINE:+--offline}

echo "=================== unit tests (extractor, HTML parser, judge)"
python3 -m pytest -q tests || exit 1

echo; echo "=================== $PID vs reference feed engine"
python3 -m necro run "$PID" $OFFLINE --impl impls.us7669123.feed_engine
ref=$?

echo; echo "=================== $PID vs generic CRUD app (control, should REJECT)"
python3 -m necro run "$PID" $OFFLINE --impl impls.crud_baseline.app
crud=$?

echo; echo "=================== $PID vs cheater (stuffed docstrings, hollow checks): v0 judge"
python3 -m necro judge "$PID" $OFFLINE --impl impls.cheater.app --judge v0
cheat_v0=$?

echo; echo "=================== $PID vs cheater: v1 judge (tracing + mutation)"
python3 -m necro run "$PID" $OFFLINE --impl impls.cheater.app
cheat_v1=$?

echo
if [ $ref -eq 0 ] && [ $crud -ne 0 ] && [ $cheat_v0 -eq 0 ] && [ $cheat_v1 -ne 0 ]; then
  echo "DEMO OK: reference accepted, CRUD rejected, cheater fools v0 and dies on v1"
else
  echo "DEMO FAILED: reference=$ref crud=$crud cheater_v0=$cheat_v0 cheater_v1=$cheat_v1"; exit 1
fi
