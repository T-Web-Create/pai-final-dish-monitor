#!/bin/bash
# 起動中の Gazebo にラック・ディッシュ本体・蓋を配置する（1枚分）
source /opt/ros/jazzy/setup.bash
M=$HOME/ros2_ws/src/dish_description/models
X=${1:-0.30}
Y=${2:-0.0}
ros2 run ros_gz_sim create -file $M/rack_plate/model.sdf -name rack_plate -x $X -y $Y -z 0.005
ros2 run ros_gz_sim create -file $M/dish_body/model.sdf -name dish_body -x $X -y $Y -z 0.0185
ros2 run ros_gz_sim create -file $M/dish_lid/model.sdf -name dish_lid -x $X -y $Y -z 0.0295
