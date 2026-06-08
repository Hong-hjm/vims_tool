# 从 paths.yaml 读取参数
import sys
import yaml
from pathlib import Path
from typing import Dict, Any

_is_test = "-test" in sys.argv      # 运行时加“-test”,测试ssh连接

calib_tool = Path(__file__).resolve().parent.parent
config_path = calib_tool / "config" / "paths.yaml"


# 从配置文件加载路径参数
try:
    with open(config_path, "r") as f:
        _config: Dict[str, Any] = yaml.safe_load(f)

    _rdk_key = "RDK_test" if _is_test else "RDK"
    _x86_key = "x86_test" if _is_test else "x86"

    _rdk: Dict[str, Dict] = _config.get(_rdk_key)
    RDK_calib_data_dir: str = _rdk.get("paths").get("calib_data_dir")
    RDK_log_dir: str = _rdk.get("paths").get("log_dir")
    RDK_rosbag_dir: str = _rdk.get("paths").get("rosbag_dir")

    _x86: Dict[str, Dict] = _config.get(_x86_key)
    calib_data_dir: str = calib_tool / _x86.get("paths").get("calib_data_dir")
    calib_data_json_dir: str = calib_tool / _x86.get("paths").get("calib_data_json_dir")
    log_dir: str = calib_tool / _x86.get("paths").get("log_dir")
    rosbag_dir: str = calib_tool / _x86.get("paths").get("rosbag_dir")

    # 保存数据csv路径
    calib_params_path = calib_tool / "calib_params.csv"
    calculate_calib_params_csv = calib_tool / "calculate_calib_params.csv"

    calib_params_file = calib_tool / _x86.get("files").get("calib_params_file")
    # 标定命令路径
    _script_base = calib_tool / "scripts" / "shell" / "run_calibrate"
    calib_script = [str(f.absolute()) for f in Path(_script_base).iterdir() if f.is_file()]
    # RDK标定数据删除命令
    remove_script = str(calib_tool / "scripts" / "shell" / "remove" / "rm_data.sh")
except:
    raise RuntimeError(f"Failed to load paths from {config_path}")

if __name__ == "__main__":
    print(calib_tool)