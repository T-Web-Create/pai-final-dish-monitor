#!/bin/bash
# usage: show_img.sh COND T   (COND: lid|open, T: hours)
source /opt/ros/jazzy/setup.bash
COND=$1
T=$2
M=$HOME/ros2_ws/src/dish_description/models
NAME=$(printf 'img_%s_t%03d' $COND $T)
for N in dish_img tex_emis tex_test; do
  gz service -s /world/empty/remove --reqtype gz.msgs.Entity --reptype gz.msgs.Boolean --timeout 2000 --req "name: \"$N\" type: MODEL" > /dev/null 2>&1
done
sleep 0.5
ros2 run ros_gz_sim create -file $M/$NAME/model.sdf -name dish_img -x 0.30 -y 0.0 -z 0.034 > /dev/null 2>&1
