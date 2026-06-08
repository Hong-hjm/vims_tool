import os
from . import calibrate, process_calib, scp_data
from utils import log_utils, paths

log_dir = log_utils.generate_log_path()

for script in paths.calib_script:
    name = os.path.basename(script)
    with log_utils.capture_all_output(log_dir, f"{name}_calib.log"):
        calibrate.run_script(script)
        
    with log_utils.capture_all_output(log_dir, f"{name}_process.log"):
        transfer = scp_data.ScpTransfer()
        transfer.transfer_calib_json()
        transfer.transfer_calib()
        # transfer.transfer_log()
        calibrate.run_script(paths.remove_script)

# 2. 处理数据，计算标定结果
processor = process_calib.CalibProcessor()
processor.calculate_stats()

transfer.transfer_rosbag()