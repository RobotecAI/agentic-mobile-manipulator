#!/usr/bin/env bash
# Refuse to run if apt ROS 2 (/opt/ros) is sourced in the shell. It must not be
# mixed with this project's conda/RoboStack ROS 2: at build time apt prefixes get
# baked into the ros2_ws overlay, and at runtime apt's NumPy-1.x cv_bridge is
# loaded into the conda NumPy-2.x env — both break the stack.
#
# Wired as a `depends-on` of build and runtime ROS tasks so a failure is a clean
# task error instead of an activation failure (which makes pixi dump the entire
# environment, secrets included).
case ":${PATH}:${LD_LIBRARY_PATH:-}:${CMAKE_PREFIX_PATH:-}:" in
  *:/opt/ros/*)
    R='\033[1;31m'; Y='\033[33m'; B='\033[1m'; D='\033[2m'; N='\033[0m'
    printf "\n${R}  ✗  apt ROS 2 is sourced — refusing to run.${N}\n\n" >&2
    printf "     This project uses ROS 2 from ${B}RoboStack (conda)${N}; mixing it with\n" >&2
    printf "     apt ROS (${Y}/opt/ros${N}) corrupts the build and crashes the agents.\n\n" >&2
    printf "     ${B}Fix${N}  remove this line from your ${B}~/.bashrc${N}:\n" >&2
    printf "          ${D}source /opt/ros/jazzy/setup.bash${N}\n" >&2
    printf "     then open a fresh shell and re-run.\n\n" >&2
    exit 1
    ;;
esac
