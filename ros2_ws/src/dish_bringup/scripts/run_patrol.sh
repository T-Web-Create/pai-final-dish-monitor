#!/bin/bash
# usage: run_patrol.sh T1 T2 ...   Each time runs in its own process with a wall-clock limit.
# On failure or timeout: release suction, go to HIGH, and redo that time (up to 3 tries).
source /opt/ros/jazzy/setup.bash
D=$HOME/ros2_ws/src/dish_bringup/scripts
for T in "$@"; do
  ok=0
  for TRY in 1 2 3; do
    if timeout -k 5 150 python3 $D/${PATROL:-patrol.py} $T; then ok=1; break; fi
    echo "t=${T}h failed or timed out (try $TRY); recovering"
    timeout -k 5 60 python3 $D/recover.py
  done
  [ $ok = 1 ] || echo "t=${T}h gave up"
done
echo "ALL DONE"
