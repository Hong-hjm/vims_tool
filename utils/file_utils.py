#!/usr/bin/env python3
# 文件工具：列出目录内容、匹配固定文件名
import os
import logging

logger = logging.getLogger(__name__)

# 检查目录下是否存在该文件
def match_file(target_dir, filename):
    file_path = os.path.join(target_dir, filename)
    return os.path.isfile(file_path)

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
# def find_in_subdirs(target_dir, keyword):
#     if not os.path.isdir(target_dir):
#         return []
#     results = []
#     for item in os.listdir(target_dir):
#         item_path = os.path.join(target_dir, item)
#         if keyword in item:
#             results.append(item_path)
#         if os.path.isdir(item_path):
#             for sub in os.listdir(item_path):
#                 if keyword in sub:
#                     results.append(os.path.join(item_path, sub))
#     return results
