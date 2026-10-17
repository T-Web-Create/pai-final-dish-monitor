#!/bin/bash
# usage: show_img.sh COND T   (COND: lid|open, T: hours)   or   show_img.sh off
source /opt/ros/jazzy/setup.bash
M=$HOME/ros2_ws/src/dish_description/models
gz service -s /world/empty/remove --reqtype gz.msgs.Entity --reptype gz.msgs.Boolean --timeout 2000 --req 'name: "dish_img" type: MODEL' > /dev/null 2>&1
if [ "$1" = "off" ]; then exit 0; fi
COND=$1
T=$2
case $COND in
  lid) Z=0.034 ;;
  open) Z=0.027 ;;
esac
NAME=$(printf 'img_%s_t%03d' $COND $T)
sleep 0.5
ros2 run ros_gz_sim create -file $M/$NAME/model.sdf -name dish_img -x 0.30 -y 0.0 -z $Z > /dev/null 2>&1
