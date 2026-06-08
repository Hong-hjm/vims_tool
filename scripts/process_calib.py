import os
import re
import json
import logging
import pandas
from typing import Dict, List
from utils import paths, file_utils, table_utils, log_utils

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("PROCESS_CALIB")

# sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 处理本地标定数据，生成 CSV 结果
class CalibProcessor:
    def __init__(self):
        self.table = table_utils.Table()
        self.calib_time_map = {}  # {rosbag_name: {calib_name: diff_seconds}}

    def process_log(self):
        """处理 log 目录下的 log_* 子目录，解析日志提取标定时间信息"""
        if not os.path.isdir(paths.log_dir):
            logger.warning(f"Log directory not found: {paths.log_dir}")
            return

        log_subdirs = sorted(os.listdir(paths.log_dir))
        for subdir in log_subdirs:
            if not subdir.startswith("log_"):
                continue
            subdir_path = os.path.join(paths.log_dir, subdir)
            if not os.path.isdir(subdir_path):
                continue

            logger.info(f"Processing log directory: {subdir}")
            files = sorted(os.listdir(subdir_path))
            for f in files:
                file_path = os.path.join(subdir_path, f)
                if not os.path.isfile(file_path):
                    continue

                # 解析日志文件，构建 {包名: {calib_*: [start_time, end_time, diff_seconds]}}
                # 顺序匹配：遇到 Start parsing Bag 记录 start，再遇到 Calibration results saved to
                # 检查包名是否与上一个 start 一致，一致则配对
                calib_info = {}
                from datetime import datetime

                pending_start = None  # (bag_name, start_time)

                with open(file_path, "r") as fh:
                    for line in fh:
                        # 匹配 Start parsing Bag 行
                        m = re.search(r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\].*Start parsing Bag:\s*(\S+)', line)
                        if m:
                            start_time = m.group(1)
                            bag_name = m.group(2)
                            pending_start = (bag_name, start_time)
                            if bag_name not in calib_info:
                                calib_info[bag_name] = {}
                            continue

                        # 匹配 Calibration results saved to 行，从路径中提取包名和 calib_*
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
                EXPECTED_CALIB_COUNT = 5
                for bag_name in list(calib_info.keys()):
                    bag = calib_info[bag_name]
                    incomplete = any(
                        times[0] is None or times[1] is None or times[2] is None
                        for calib_name, times in bag.items()
                    )
                    if incomplete:
                        logger.warning(f"  Bag {bag_name} has incomplete calib entries, removing")
                        del calib_info[bag_name]
                    elif len(bag) < EXPECTED_CALIB_COUNT:
                        logger.warning(f"  Bag {bag_name} has only {len(bag)} calib entries (expected {EXPECTED_CALIB_COUNT}), removing")
                        del calib_info[bag_name]

                # 保存到 calib_time_map 供后续写入 CSV
                for bag_name, calibs in calib_info.items():
                    if bag_name not in self.calib_time_map:
                        self.calib_time_map[bag_name] = {}
                    for calib_name, times in calibs.items():
                        self.calib_time_map[bag_name][calib_name] = times[2]  # diff_seconds

                # 输出解析结果
                logger.info(f"--- {subdir}/{f} ---")
                for bag_name, calibs in calib_info.items():
                    logger.info(f"  Bag: {bag_name}")
                    for calib_name, times in sorted(calibs.items()):
                        logger.info(f"    {calib_name}: {times}")

    def _read_json(self, calib_dir):
        """读取 calib 目录下的 calibration_result.json，返回 (translation, rotation_deg)"""
        json_path = os.path.join(calib_dir, paths.calib_params_file)
        if not os.path.isfile(json_path):
            return None
        with open(json_path, "r") as f:
            data = json.load(f)
        translation = [round(x, 3) for x in data.get("translation", [])]
        rotation_deg = [round(x, 3) for x in data.get("rotation_deg", [])]
        return translation, rotation_deg

    def _process_rosbag(self, rosbag_dir):
        """处理单个 rosbag 目录下的所有 calib 子目录"""
        rd = os.path.basename(rosbag_dir)
        logger.info(f"Found rosbag2 directory: {rd}")

        calibs = file_utils.find_in_subdirs(rosbag_dir, "calib")
        for calib_dir in calibs:
            calib = os.path.basename(calib_dir)
            logger.info(f"Found calib directory: {calib}")

            result = self._read_json(calib_dir)
            if result is None:
                continue
            translation, rotation_deg = result
            # 从 calib_time_map 中获取时间差值
            calib_time = self.calib_time_map.get(rd, {}).get(calib, None)
            self.table.add_data_row(rd, calib, translation, rotation_deg, calib_time)
            logger.info(f"translation: {translation}, rotation_deg: {rotation_deg}, calib_time: {calib_time}")

    def _process_view(self, view_dir):
        """处理单个视图目录下的所有 rosbag 目录"""
        v = os.path.basename(view_dir)
        self.table.add_ref_row(v)

        rosbag_dirs = file_utils.find_in_subdirs(view_dir, "rosbag2")
        for rosbag_dir in rosbag_dirs:
            self._process_rosbag(rosbag_dir)

    def run(self):
        if not os.path.isdir(paths.calib_data_json_dir):
            return
        views = os.listdir(paths.calib_data_json_dir)


        for v in sorted(views):
            view_dir = os.path.join(paths.calib_data_json_dir, v)

            if os.path.isdir(view_dir):
                self._process_view(view_dir)

        self.table.save_csv(paths.calib_params_path)
    
    # 计算标定结果均值与方差
    def calculate_stats(self):
        if not os.path.exists(paths.calib_params_path):
            logger.error(f"CSV file not found: {paths.calib_params_path}")
            return
        csv = pandas.read_csv(paths.calib_params_path)

        # 需进行计算的列
        calculate_cols = ['X Translation(m)', 'Y Translation(m)', 'Z Translation(m)', 'roll(deg)', 'pitch(deg)', 'yaw(deg)']

        csv['rosbag'] = csv['rosbag'].ffill()

        # 视图rosbag分类
        view_tab: Dict[str, List] = {}
        view_bag_tab: Dict[str, List] = {}
        view_reference: Dict[str, pandas.DataFrame] = {}     # 参考数据行
        for row in csv["rosbag"]:
            row: str
            if row.endswith("View"):
                view = row
                view_bag_tab[view] = []
                view_reference[view] = csv[csv["rosbag"] == view]
                continue
            if row not in view_bag_tab[view]:
                view_bag_tab[view].append(row)
        
        for view_name in view_bag_tab.keys():
            for i in range(len(csv)):
                row = csv.iloc[i]
                if row["rosbag"] in view_bag_tab[view_name]:
                    if view_name not in view_tab:
                        view_tab[view_name] = []
                    view_tab[view_name].append(row)

        # 对每个包进行计算
        csv = csv[csv['rosbag'].str.startswith('rosbag2_', na=False)]
        bag_tab: Dict[str, pandas.DataFrame] = {}
        for rosbag, group in csv.groupby('rosbag'):
            tab = group.copy()
            mean_vals = tab[calculate_cols].mean()
            var_vals = tab[calculate_cols].var(ddof=0)

            mean_row = {'rosbag': rosbag, 'calib': 'Mean','calib_time(s)': ''}
            var_row = {'rosbag': rosbag, 'calib': 'Variance','calib_time(s)': ''}
            for col in calculate_cols:
                mean_row[col] = mean_vals[col]
                var_row[col] = var_vals[col]

            tab = pandas.concat([tab, pandas.DataFrame([mean_row, var_row])], ignore_index=True)
            bag_tab[rosbag] = tab

        # 重新写入表格
        final_list: List[pandas.DataFrame] = []
        for view_name, rows in view_tab.items():
            view_df = pandas.DataFrame(rows)

            mean_vals = view_df[calculate_cols].mean()
            var_vals = view_df[calculate_cols].var(ddof=0)

            mean_row = {'rosbag': f"{view_name} mean", 'calib': '','calib_time(s)': ''}
            var_row = {'rosbag': f"{view_name} Variance", 'calib': '','calib_time(s)': ''}
            # 计算视图的均值和方差
            for col in calculate_cols:
                mean_row[col] = mean_vals[col]
                var_row[col] = var_vals[col]
            # 写入表格
            view_csv = []
            view_csv.append(view_reference[view_name])
            for rosbag, bag_df in bag_tab.items():
                if rosbag in view_bag_tab[view_name]:
                    view_csv.append(bag_df)
            result_df = pandas.concat(view_csv, ignore_index=True)
            result_df = pandas.concat([result_df, pandas.DataFrame([mean_row, var_row])], ignore_index=True)

            final_list.append(result_df)
        final_df = pandas.concat(final_list, ignore_index=True)
        final_df['rosbag'] = final_df['rosbag'].mask(final_df['rosbag'].duplicated(), '')
        final_df.to_csv(paths.calculate_calib_params_csv, index=False,float_format="%.6f")


if __name__ == "__main__":
    with log_utils.capture_all_output(log_utils.generate_log_path()):
        processor = CalibProcessor()
        processor.calculate_stats()

