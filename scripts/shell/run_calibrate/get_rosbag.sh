#!/bin/bash
# 获取rosbag

# 检查 yq
if ! command -v yq &> /dev/null; then
    echo "error: yq is not installed, please install yq first."
    echo "install automatically"
    sudo wget https://github.com/mikefarah/yq/releases/latest/download/yq_linux_amd64 -O /usr/bin/yq
    sudo chmod +x /usr/bin/yq
    if ! command -v yq &> /dev/null; then
        echo "error: failed to install yq, please check the installation."
        exit 1
    fi
fi

PROJECT_DIR="$(cd "$(dirname "$0")/../../.." && pwd)"

# 修正：使用 mapfile 读成数组
mapfile -t BAGS < <(yq -r '.RDK.paths.rosbag_dir[]' "$PROJECT_DIR/config/paths.yaml")

WAIT_CALIB_YAML="$PROJECT_DIR/scripts/shell/run_calibrate/wait_to_calib.yaml"

if [ ! -f "$WAIT_CALIB_YAML" ]; then
    mkdir -p "$(dirname "$WAIT_CALIB_YAML")"
    cat > "$WAIT_CALIB_YAML" << 'EOF'
RDK:
  paths:
    rosbag_dir: []
EOF
fi

# 清空并重新写入
yq -i '.RDK.paths.rosbag_dir = []' "$WAIT_CALIB_YAML"

# 逐个添加（现在 BAGS 是数组了）
for bag_dir in "${BAGS[@]}"; do
    yq -i '.RDK.paths.rosbag_dir += ["'$bag_dir'"]' "$WAIT_CALIB_YAML"
done
