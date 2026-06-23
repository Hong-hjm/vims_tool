# 标定main.py
import sys
import yaml
from pathlib import Path
from scripts import calibrate, process_calib, scp_data
from utils import log_utils

# 读取calib_num，设定标定次数，或在配置文件中设置
calib_params_path = Path(__file__).parent / "config" / "calib_params.yaml"
for arg in sys.argv:
    if arg.startswith("calib_num:="):
        try:
            num = int(arg.split(":=")[1])
            with open(calib_params_path, "r") as f:
                config = yaml.safe_load(f)
            config["calib_num"] = num
            with open(calib_params_path, "w") as f:
                yaml.dump(config, f, default_flow_style=False)
            print(f"Set calib_num={num} in config/calib_params.yaml")
        except Exception as e:
            print(f"Failed to set calib_num: {e}")
        break

calib_dir = calibrate.calib()
with log_utils.capture_all_output(calib_dir, "process"):

    transfer = scp_data.ScpTransfer()
    rdk_json_paths = transfer.transfer_calib_json()
    transfer.transfer_calib()
    transfer.remove_dir()

    # 2. 处理数据，计算标定结果
    processor = process_calib.CalibProcessor()
    processor.log_dir=calib_dir
    processor.process_log()
    processor.write_csv()


    transfer.transfer_rosbag()
    transfer.ssh_close()
