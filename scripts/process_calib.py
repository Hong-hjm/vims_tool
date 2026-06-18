# 标定结果处理

import os
import re
import sys
import json
import yaml
import logging
import pandas
from datetime import datetime
from typing import Dict, List
from pathlib import Path

# 将项目根目录加入 sys.path，确保直接运行时能导入 utils 模块
# _project_root = Path(__file__).resolve().parent.parent
# if str(_project_root) not in sys.path:
#     sys.path.insert(0, str(_project_root))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import paths, file_utils, table_utils




logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("PROCESS_CALIB")

# 处理本地标定数据，生成 CSV 结果
class CalibProcessor:
    def __init__(self):
        self.table = table_utils.Table()
        self.calib_time_map: Dict[str, dict] = {}  # {rosbag_name: {calib_name: diff_seconds}}
        self.log_dir = None
        # 标定次数，与 calib.sh 中的 CALIB_NUM 保持一致，由 main.py 统一管理
        try:
            with open(paths.calib_tool / "config" / "calib_params.yaml", "r") as f:
                config: dict = yaml.safe_load(f)
                self.expected_calib_count = int(config.get("calib_num"))
        except Exception:
            self.expected_calib_count = 1
        logger.info(f"Expected calib count: {self.expected_calib_count}")

    def process_log(self):
        """处理 self.log_dir 目录下的 calib_*log 文件，解析日志提取标定时间信息"""
        logger.info("="*30)
        logger.info("start to process the log file")

        if not os.path.isdir(self.log_dir):
            logger.warning(f"Log directory not found: {self.log_dir}")
            return

        files = sorted(os.listdir(self.log_dir))
        for f in files:
            file_path = Path(self.log_dir) / f
            if not os.path.isfile(file_path):
                continue
            if not f.startswith("calib_") or not f.endswith("log"):
                continue

            logger.info(f"Processing log file: {f}")

            # 解析日志文件，构建 {包名: {calib_*: [start_time, end_time, diff_seconds]}}
            calib_info: Dict[str, dict] = {}

            pending_start = None  # (bag_name, start_time)

            with open(file_path, "r") as fh:
                for line in fh:

                    # 匹配 Start parsing Bag 开始行
                    m = re.search(r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\].*Start parsing Bag:\s*(\S+)', line)
                    if m:
                        start_time = m.group(1)
                        bag_name = m.group(2)
                        pending_start = (bag_name, start_time)
                        if bag_name not in calib_info:
                            calib_info[bag_name] = {}
                        continue

                    # 匹配 Calibration results saved to 结束行，从路径中提取包名和 calib_*
                    m = re.search(r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\].*Calibration results saved to:.*/(rosbag2_\S+?)/(calib_\d+)/', line)
                    if m:
                        end_time = m.group(1)
                        bag_name = m.group(2)
                        calib_name = m.group(3)
                        # 检查包名是否与上一个 start 一致
                        if pending_start and pending_start[0] == bag_name:
                            st = pending_start[1]
                            fmt = "%Y-%m-%d %H:%M:%S"
                            diff = (datetime.strptime(end_time, fmt) - datetime.strptime(st, fmt)).total_seconds()
                        else:
                            st = None
                            diff = None
                        if bag_name not in calib_info:
                            calib_info[bag_name] = {}
                        calib_info[bag_name][calib_name] = [st, end_time, diff]
                        continue

            # 过滤：每个 calib 必须完整 [start, end, diff]，否则整个包移除
            for bag_name in list(calib_info.keys()):
                bag = calib_info[bag_name]
                incomplete = any(
                    times[0] is None or times[1] is None or times[2] is None
                    for _, times in bag.items()
                )
                if incomplete:
                    logger.warning(f"  Bag {bag_name} has incomplete calib entries, removing")
                    del calib_info[bag_name]
                elif len(bag) < self.expected_calib_count:
                    logger.warning(f"  Bag {bag_name} has only {len(bag)} calib entries (expected {self.expected_calib_count}), removing")
                    del calib_info[bag_name]

            # 保存到 calib_time_map 供后续写入 CSV
            for bag_name, calibs in calib_info.items():
                if bag_name not in self.calib_time_map:
                    self.calib_time_map[bag_name] = {}
                for calib_name, times in calibs.items():
                    self.calib_time_map[bag_name][calib_name] = times[2]  # diff_seconds

            # 输出解析结果
            logger.info(f"--- {f} ---")
            for bag_name, calibs in calib_info.items():
                logger.info(f"  Bag: {bag_name}")
                for calib_name, times in sorted(calibs.items()):
                    logger.info(f"    {calib_name}: {times}")
        logger.info("log file process finished")

    def write_csv(self, json_paths: List[str] = None):
        logger.info("="*30)
        logger.info("start to write data to csv")

        # 若未传入路径列表，则自动扫描本地 calib_data_json_dir 目录
        if json_paths is None:
            json_paths = []
            if file_utils.is_dir_empty(paths.calib_data_json_dir):
                logger.error(f"Data not found: {paths.calib_data_json_dir}")
                return
            # 查找所有 calib 目录
            json_paths = file_utils.find_in_subdirs(paths.calib_data_json_dir, paths.calib_params_file)

        # 按参考视图名分类路径
        view_dict: Dict[str, list] = {}
        for json_file in json_paths:
            if not json_file.startswith(str(paths.calib_data_json_dir)):
                rel_path = json_file.replace(str(paths.RDK_calib_data_dir), "").lstrip("/")
                json_file = paths.calib_data_json_dir / rel_path

            # 读取 JSON 数据
            with open(json_file, "r") as f:
                data: dict = json.load(f)
            translation = [x for x in data.get("translation", [])]
            rotation_deg = [x for x in data.get("rotation_deg", [])]

            # 从相对路径解析 rosbag 和 calib 名
            rel_path = json_file.replace(str(paths.calib_data_json_dir),"").lstrip("/")
            parts = Path(rel_path).parts
            view_name = parts[0]
            rosbag_name = parts[1]
            calib_name = parts[2]

            calib_time = None
            if rosbag_name in self.calib_time_map:
                calib_time = self.calib_time_map[rosbag_name].get(calib_name, None)

            ref_key, label = self.table.view_classfy(view_name)
            if ref_key not in view_dict:
                view_dict[ref_key] = []
                ref_row = self.table.add_ref_row(ref_key, label)
                view_dict[ref_key].append(ref_row)
            view_dict[ref_key].append([rosbag_name, calib_name, *translation, *rotation_deg, calib_time])

        self.table.save_csv(view_dict)
        logger.info("csv writting finished")

    
    # 计算标定结果均值与方差
    def calculate_stats(self):
        logger.info("="*30)
        logger.info("start to calculate stats")

        self.table.calculate()

        logger.info("calculate finished")


if __name__ == "__main__":

    processor = CalibProcessor()
    processor.write_csv()
    # processor.calculate_stats()

