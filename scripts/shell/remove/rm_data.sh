#!/bin/bash
# 删除 RDK 上的标定数据

PROJECT_DIR="$(cd "$(dirname "$0")/../../.." && pwd)"

# ===== 从配置文件读取 =====
CALIB_DATA_DIR="$(yq '.RDK.paths.calib_data_dir' "$PROJECT_DIR/config/paths.yaml")"

# ===== 从 device.yaml 读取 SSH 连接信息 =====
RDK_HOST="$(yq '.device.host' "$PROJECT_DIR/config/device.yaml")"
RDK_USER="$(yq '.device.user' "$PROJECT_DIR/config/device.yaml")"
RDK_PASS="$(yq '.device.password' "$PROJECT_DIR/config/device.yaml")"

# 通过 SSH 远程执行删除
sshpass -p "$RDK_PASS" ssh -o StrictHostKeyChecking=no "${RDK_USER}@${RDK_HOST}" \
    "rm -rf ${CALIB_DATA_DIR}*"

echo "remove dir finished"
