# 自动执行标定
import os
import subprocess
import logging
from utils import paths, log_utils
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("CALIBRATE")

def calib():
    """执行标定脚本，返回标定日志路径"""
    calib_log_dir = log_utils.generate_log_path()
    try:
        with log_utils.capture_all_output(calib_log_dir, "calib"):
            scripts = [paths.get_rosbag_sh, paths.calib_sh]
            for script in scripts:
                while True:
                    name = os.path.basename(script)
                    print(f"Running {name}...")

                    process = subprocess.Popen(
                        ["bash", script],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True
                    )

                    for line in process.stdout:
                        print(line, end="")

                    ret = process.wait()
                    if ret == 0:
                        break
        logger.info("calibrate finished")
        return calib_log_dir
    except:
        logger.error("calibrate fialed")
    

if __name__ == "__main__":
    pass
