# 表格工具
import yaml
import logging
import pandas
from typing import Dict
from utils import paths
logger = logging.getLogger(__name__)

_config_path = paths.calib_tool / "config" / "calib_params.yaml"

try:
    with open(_config_path, "r") as f:
        _calib_config: Dict[str, dict] = yaml.safe_load(f)

        _calib_params = _calib_config.get("calibration")
except:
    raise RuntimeError(f"Failed to load calibration parameters from {_config_path}")

# 列索引映射：_calib_params 中 params 的索引到表格列的映射
# params[0:3] = [roll, pitch, yaw], params[3:6] = [x, y, z]
_TRANSLATION_IDX = [3, 4, 5]  # params 中 X, Y, Z Translation 的索引
_ROTATION_IDX = [0, 1, 2]     # params 中 roll, pitch, yaw 的索引

class Table:
    """表格工具"""
    def __init__(self):
        self.headers = [
            "rosbag",
            "calib",
            "X Translation(m)",
            "Y Translation(m)",
            "Z Translation(m)",
            "roll(deg)",
            "pitch(deg)",
            "yaw(deg)",
            "calib_time(s)",
        ]
        self.ref_df: Dict[str, pandas.DataFrame] = {}
        self.rows_df: Dict[str, pandas.DataFrame] = {}
        self.bag_df: Dict[str, pandas.DataFrame] = {}
        self.csv_df = pandas.DataFrame(columns=self.headers)

    def view_classfy(self, view):
        """视角分类"""
        if "pingshi" in view:
            ref_key = "frontal_view"
            label = "Frontal View"
        elif "fushi" in view:
            ref_key = "overhead_view"
            label = "Overhead View"
        elif "yangshi" in view:
            ref_key = "upward_view"
            label = "Upward View"
        else:
            ref_key = "unknown"
            label = None
        return ref_key, label

    def add_ref_row(self, ref_key, label):
        """
        添加参考数据
        
        :param self: Table 对象
        :param ref_key: 参考名
        :param label: 视角标签
        """
        if label:
            params = _calib_params.get(ref_key)
            # 从 params 中提取 translation 和 rotation
            translation = (
                [params[i] for i in _TRANSLATION_IDX if i < len(params)]
                if len(params) > max(_TRANSLATION_IDX)
                else []
            )
            rotation_deg = (
                [params[i] for i in _ROTATION_IDX if i < len(params)]
                if len(params) > max(_ROTATION_IDX)
                else []
            )
            return [label, "", *translation, *rotation_deg, ""]
        else:
            return [None]*9


    def save_csv(self, view_dict: dict):
        """将表格写入 CSV 文件"""
        self.ref_df: Dict[str, pandas.DataFrame] = {}
        self.rows_df: Dict[str, pandas.DataFrame] = {}
        self.bag_df: Dict[str, pandas.DataFrame] = {}
        self.csv_df = pandas.DataFrame(columns=self.headers)
        for ref_key, value in view_dict.items():
            self.ref_df[ref_key] = pandas.DataFrame([value[0]], columns=self.headers)
            self.rows_df[ref_key] = pandas.DataFrame(value[1:], columns=self.headers).sort_values(["rosbag", "calib"])

            self.csv_df = pandas.concat([self.csv_df, self.ref_df[ref_key]], ignore_index=True)
            self.csv_df = pandas.concat([self.csv_df, self.rows_df[ref_key]], ignore_index=True)

            for i in value[1:]:
                i_df = pandas.DataFrame([i], columns=self.headers)
                rosbag = ref_key + "-" + i[0]
                if not rosbag in self.bag_df:
                    self.bag_df[rosbag] = pandas.DataFrame(columns=self.headers)
                self.bag_df[rosbag] = pandas.concat([self.bag_df[rosbag], i_df], ignore_index=True).sort_values(["rosbag", "calib"])

        self.csv_df.to_csv(paths.calib_params_path, index=False, encoding='utf-8')

    def calculate(self):
        """计算每个包，每个视角的平均值和标准差"""
        self.csv_df = pandas.DataFrame(columns=self.headers)

        calculate_cols = ['X Translation(m)', 'Y Translation(m)', 'Z Translation(m)', 'roll(deg)', 'pitch(deg)', 'yaw(deg)']
        for ref_key, ref_df in self.ref_df.items():
            ref_df: pandas.DataFrame
            self.csv_df = pandas.concat([self.csv_df, ref_df], ignore_index=True)
            for key, rosbag_df in self.bag_df.items():
                rosbag_df: pandas.DataFrame
                view, rosbag= key.split("-", maxsplit=1)
                if view == ref_key:
                    bag_df = rosbag_df.copy()

                    mean_vals = bag_df[calculate_cols].mean()
                    var_vals = bag_df[calculate_cols].var(ddof=0)
                    mean_row = {'rosbag': rosbag, 'calib': 'Mean','calib_time(s)': ''}
                    var_row = {'rosbag': rosbag, 'calib': 'Variance','calib_time(s)': ''}
                    for col in calculate_cols:
                        mean_row[col] = mean_vals[col]
                        var_row[col] = var_vals[col]
                    bag_df = pandas.concat([bag_df, pandas.DataFrame([mean_row, var_row])], ignore_index=True)
                    self.csv_df = pandas.concat([self.csv_df, bag_df], ignore_index=True)

            view_df = self.rows_df[ref_key].copy()
            mean_vals = view_df[calculate_cols].mean()
            var_vals = view_df[calculate_cols].var(ddof=0)
            mean_row = {'rosbag': ref_key, 'calib': 'Mean','calib_time(s)': ''}
            var_row = {'rosbag': ref_key, 'calib': 'Variance','calib_time(s)': ''}
            for col in calculate_cols:
                mean_row[col] = mean_vals[col]
                var_row[col] = var_vals[col]
            view_cal = pandas.DataFrame([mean_row, var_row])
            self.csv_df = pandas.concat([self.csv_df, view_cal], ignore_index=True)

        self.csv_df.to_csv(paths.calculate_calib_params_csv, index=False, encoding='utf-8')
