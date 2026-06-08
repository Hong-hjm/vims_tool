import os
import yaml
import logging
import pandas

logger = logging.getLogger(__name__)

_config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "config", "calib_params.yaml")
try:
    with open(_config_path, "r") as f:
        _calib_config = yaml.safe_load(f)

        _calib_params = _calib_config.get("calibration", {})
except:
    raise RuntimeError(f"Failed to load calibration parameters from {_config_path}")

class Table:
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
        self.rows = []
        self._ref_added = set()

    def add_ref_row(self, view_name):
        """根据 view_name 添加一行预设参考行（同类型参考行只添加一次）"""
        if "pingshi" in view_name:
            ref_key = "frontal_view"
            label = "Frontal View"
        elif "fushi" in view_name:
            ref_key = "overhead_view"
            label = "Overhead View"
        elif "yangshi" in view_name:
            ref_key = "upward_view"
            label = "Upward View"
        else:
            ref_key = None
            label = ""

        if ref_key is None or ref_key in self._ref_added:
            return
        self._ref_added.add(ref_key)

        params = _calib_params.get(ref_key, [])

        ref_row = [
            label,
            "",
            params[3] if len(params) > 3 else "",  # X Translation(m)
            params[4] if len(params) > 4 else "",  # Y Translation(m)
            params[5] if len(params) > 5 else "",  # Z Translation(m)
            params[0] if len(params) > 0 else "",  # roll(deg)
            params[1] if len(params) > 1 else "",  # pitch(deg)
            params[2] if len(params) > 2 else "",  # yaw(deg)
        ]
        self.rows.append(ref_row)

    def add_data_row(self, rosbag, calib, translation, rotation_deg, calib_time=None):
        """添加一行实际标定数据"""
        data_row = [
            rosbag,
            calib,
            translation[0] if len(translation) > 0 else "",
            translation[1] if len(translation) > 1 else "",
            translation[2] if len(translation) > 2 else "",
            rotation_deg[0] if len(rotation_deg) > 0 else "",
            rotation_deg[1] if len(rotation_deg) > 1 else "",
            rotation_deg[2] if len(rotation_deg) > 2 else "",
            calib_time if calib_time is not None else "",
        ]
        self.rows.append(data_row)

    def save_csv(self, file_path):
        """将表格写入 CSV 文件"""
        
        # 转换为 DataFrame
        df = pandas.DataFrame(self.rows, columns=self.headers)
        
        # 处理参考行和数据行
        # 找出参考行（calib 列为空的行）
        ref_rows = df[df['calib'] == '']
        data_rows = df[df['calib'] != '']
        
        # 数据行排序
        data_rows = data_rows.sort_values(['rosbag', 'calib'])
        
        # 合并相同 rosbag（将 rosbag 列置空）
        data_rows['rosbag'] = data_rows['rosbag'].mask(data_rows['rosbag'].duplicated(), '')
        
        # 合并并保存
        result = pandas.concat([ref_rows, data_rows], ignore_index=True)
        result.to_csv(file_path, index=False)