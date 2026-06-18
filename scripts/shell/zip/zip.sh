#!/bin/bash

# 用法：bash zip.sh <父文件夹路径>

if [ -z "$1" ]; then
    echo "用法: $0 <父文件夹路径>"
    echo "示例: $0 ./calib_data"
    exit 1
fi

PARENT_DIR="$1"
PARENT_DIR="${PARENT_DIR%/}"

# 检查文件夹是否存在
if [ ! -d "$PARENT_DIR" ]; then
    echo "错误: 文件夹 '$PARENT_DIR' 不存在"
    exit 1
fi

echo "正在压缩 $PARENT_DIR 下的子文件夹..."

# 遍历所有子文件夹
for subdir in "$PARENT_DIR"/vio_result*/; do
    # 检查是否有子文件夹
    if [ ! -d "$subdir" ]; then
        echo "没有找到子文件夹"
        break
    fi
    
    # 去掉末尾的斜杠
    subdir="${subdir%/}"
    
    # 获取文件夹名称
    dir_name=$(basename "$subdir")
    zip_file="${PARENT_DIR}/${dir_name}.zip"
    
    echo "  压缩: $subdir -> $zip_file"
    zip -r "$zip_file" "$subdir"
done

echo "完成"
