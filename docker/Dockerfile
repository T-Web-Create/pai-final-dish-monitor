# PAI 最終課題 シミュレーション環境（arm64 / Ubuntu 24.04 / ROS2 Jazzy / Gazebo Harmonic）
FROM ros:jazzy-ros-base

ARG USERNAME=t2o
ARG UID=1000
ARG GID=1000
ENV DEBIAN_FRONTEND=noninteractive

# ROS2 / Gazebo Harmonic / UR / MoveIt2 と描画確認用ツール
RUN apt-get update && apt-get install -y --no-install-recommends \
      ros-jazzy-rviz2 \
      ros-jazzy-ros-gz \
      ros-jazzy-ur \
      ros-jazzy-ur-simulation-gz \
      ros-jazzy-moveit \
      python3-colcon-common-extensions \
      mesa-utils git sudo less vim bash-completion \
    && rm -rf /var/lib/apt/lists/*

# ホストと同じ UID/GID のユーザーを作る（マウント先のファイルが root 所有にならないように）
# Ubuntu 24.04 の基本イメージには UID 1000 の ubuntu ユーザーがいるので先に消す
RUN if id -u ubuntu >/dev/null 2>&1; then userdel -r ubuntu; fi \
 && groupadd -g ${GID} ${USERNAME} \
 && useradd -m -u ${UID} -g ${GID} -s /bin/bash ${USERNAME} \
 && echo "${USERNAME} ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/${USERNAME} \
 && chmod 0440 /etc/sudoers.d/${USERNAME}

ENV NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=all

USER ${USERNAME}
WORKDIR /home/${USERNAME}/ros2_ws
RUN echo 'source /opt/ros/jazzy/setup.bash' >> ~/.bashrc \
 && echo '[ -f ~/ros2_ws/install/setup.bash ] && source ~/ros2_ws/install/setup.bash' >> ~/.bashrc

CMD ["sleep", "infinity"]
