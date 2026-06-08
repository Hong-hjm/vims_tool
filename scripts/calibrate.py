import os
import sys
import subprocess
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import paths, log_utils


def run_script(script_path):
    # 在本地执行 shell 脚本，实时输出日志
    name = os.path.basename(script_path)
    print(f"Running {name}...")

    # 在项目根目录执行，确保脚本中的相对路径正确
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    process = subprocess.Popen(
        ["bash", script_path],
        cwd=project_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    for line in process.stdout:
        print(line, end="")

    ret = process.wait()
    if ret == 0:
        print(f"{name} completed successfully")
    else:
        print(f"{name} failed with exit code {ret}")

    return ret


if __name__ == "__main__":
    log_dir = log_utils.generate_log_path()
    with log_utils.capture_all_output(log_dir):
        run_script(paths.calib_script_1)
        # run_script(paths.calib_script_2)
