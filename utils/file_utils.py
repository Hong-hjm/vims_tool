#!/usr/bin/env python3
# 文件工具：列出目录内容、匹配固定文件名
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# 检查目录下是否存在该文件
def match_file(target_dir, filename):
    file_path = Path(target_dir) / filename
    return os.path.isfile(str(file_path))

# 检查目录是否存在，不存在则创建
def check_path(path):
    if os.path.isdir(path):
        return True
    else:
        os.makedirs(path, exist_ok=True)
        return False

# 检查目录是否为空
def is_dir_empty(path):
    if not os.path.isdir(path):
        return True
    with os.scandir(path) as it:
        return not any(it)  # 没有条目返回 True

# 在 target_dir 及其每个子目录中查找包含 keyword 的条目
def find_in_subdirs(target_dir, keyword):
    target_path = Path(target_dir)
    if not target_path.is_dir():
        return []
    
    results = []
    for item in target_path.rglob("*"):  # rglob 递归匹配所有层级
        if keyword in item.name:         # 文件名包含关键字
            results.append(str(item))
    return results

# 在 vio_results 目录下查找所有 vio_result_* 子目录，返回对应子目录列表
def find_rosbag_dirs(vio_results_dir):
    base_path = Path(vio_results_dir)
    if not base_path.exists():
        logger.error(f"vio_results directory not found: {vio_results_dir}")
        return 
    
    rosbag_dirs = [d for d in base_path.iterdir() if d.is_dir() and d.name.startswith("vio_result_")]
    
    if not rosbag_dirs:
        logger.error(f"No vio_result_* directories found under {vio_results_dir}")
        return 
    
    rosbag_dirs.sort()
    
    return rosbag_dirs