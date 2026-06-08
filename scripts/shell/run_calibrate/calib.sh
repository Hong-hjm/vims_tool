#!/bin/bash
# 标定脚本

# 检查 sshpass
if ! command -v sshpass &> /dev/null; then
    echo "error: sshpass is not installed, please install sshpass first."
    echo "install automatically"
    sudo apt-get install -y sshpass
    if ! command -v sshpass &> /dev/null; then
        echo "error: failed to install sshpass, please check the installation."
        exit 1
    fi
fi

PROJECT_DIR="$(cd "$(dirname "$0")/../../.." && pwd)"

# ===== 从配置文件读取 =====
BAG_DIR="$(yq '.RDK.paths.rosbag_dir.[0]' "$PROJECT_DIR/scripts/shell/run_calibrate/wait_to_calib.yaml")"
CALIB_DATA_DIR="$(yq '.RDK.paths.calib_data_dir' "$PROJECT_DIR/config/paths.yaml")"
OUTPUT_DIR="${CALIB_DATA_DIR}$(basename $BAG_DIR)"

yq -i 'del(.RDK.paths.rosbag_dir[0])' "$PROJECT_DIR/scripts/shell/run_calibrate/wait_to_calib.yaml"

case "$(basename "$BAG_DIR")" in
    pingshi*) key="frontal_view" ;;
    fushi*)   key="overhead_view" ;;
    yangshi*) key="upward_view" ;;
esac
EXTRINSICS="$(yq ".calibration.$key" "$PROJECT_DIR/config/calib_params.yaml")"
# 标定次数
CALIB_NUM=5

# ===== 从 device.yaml 读取 SSH 连接信息 =====
RDK_HOST="$(yq '.device.host' "$PROJECT_DIR/config/device.yaml")"
RDK_USER="$(yq '.device.user' "$PROJECT_DIR/config/device.yaml")"
RDK_PASS="$(yq '.device.password' "$PROJECT_DIR/config/device.yaml")"
RDK_ROS_DISTRO="$(yq '.device.ros_distro' "$PROJECT_DIR/config/device.yaml")"

echo "========================================"
echo "  Running calibration on RDK ($RDK_HOST)"
echo "  bag_dir: $BAG_DIR"
echo "  output_dir: $OUTPUT_DIR"
echo "  extrinsics: $EXTRINSICS"
echo "========================================"

# 通过 SSH 远程执行 ros2 launch
# ros2 launch 命令组成：
# 1. cd 到目录
# 2. 配置环境
# 3. launch
sshpass -p "$RDK_PASS" ssh -o StrictHostKeyChecking=no "${RDK_USER}@${RDK_HOST}" \
    "source /opt/ros/${RDK_ROS_DISTRO}/setup.bash && \
     source install/setup.bash && \
     ros2 launch camera_extrinsic_calibration camera_extrinsic_calibration.launch.py \
        camera_color_topic:=/StereoNetNode/rectify_left_image \
        camera_pointcloud_topic:=/StereoNetNode/stereonet_pointcloud2 \
        camera_depth_topic:=/StereoNetNode/stereonet_depth \
        camera_info_topic:=/StereoNetNode/stereonet_depth/camera_info \
        bag_datasets_dir:=${BAG_DIR} \
        parser_output_dir:=${OUTPUT_DIR} \
        init_extrinsics:=\"${EXTRINSICS}\" \
        calib_num:=${CALIB_NUM}"
