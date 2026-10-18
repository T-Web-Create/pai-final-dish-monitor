#!/bin/bash
# Capture 13 times x (lid, open) from the Gazebo camera into ~/recordings/gz_series
source /opt/ros/jazzy/setup.bash
L=$HOME/ros2_ws/src/dish_bringup
OUT=$HOME/recordings/gz_series
mkdir -p $OUT
ros2 run ros_gz_image image_bridge /dish_camera/image > /dev/null 2>&1 &
BR=$!
sleep 3
for COND in lid open; do
  for T in 0 6 12 18 24 30 36 42 48 54 60 66 72; do
    $L/launch/show_img.sh $COND $T
    sleep 1.5
    python3 $L/scripts/save_image.py $OUT/$(printf '%s_t%03d.png' $COND $T)
  done
done
kill $BR; pkill -f "lib/ros_gz_image/image_bridge /dish_camera/image" 2>/dev/null
echo done
