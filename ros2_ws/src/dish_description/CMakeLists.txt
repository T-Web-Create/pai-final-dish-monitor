cmake_minimum_required(VERSION 3.8)
project(dish_description)

find_package(ament_cmake REQUIRED)

install(DIRECTORY urdf models config
  DESTINATION share/${PROJECT_NAME})

ament_package()
