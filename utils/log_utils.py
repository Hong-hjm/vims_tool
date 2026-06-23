# 上下文管理器，日志获取
import sys
import logging
import contextlib
from utils import file_utils, paths
import datetime
from pathlib import Path
import re
from typing import Literal

class _Tee:
    def __init__(self, *s): self.s = s
    def write(self, t, **kwargs):
        for x in self.s: x.write(t, **kwargs); x.flush()
    def flush(self):
        for x in self.s: x.flush()

def generate_log_path():
    """生成标定日志文件目录"""
    file_utils.check_path(paths.log_dir)
    log_dir = paths.log_dir / f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    file_utils.check_path(log_dir)
    return log_dir

@contextlib.contextmanager
def capture_all_output(log_dir, log_mask: Literal["calib", "process"]):
    """
        获取输出保存至日志
        params: 
            log_dir: 日志保存路径
            log_mask： 日志类型（"calib"，"process"）     
    """
    calib_num = 0
    files = list(Path(log_dir).glob(f"{log_mask}_*.log"))
    for f in files:
        match = re.search(rf'{log_mask}_(\d+)\.log$', f.name)
        if match:
            n = int(match.group(1))
            if n > calib_num:
                calib_num = n
    calib_num += 1
    log_file = Path(log_dir) / f"{log_mask}_{calib_num}.log"

    # 给 root logger 添加文件 handler，捕获 logging 输出
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S"
    ))
    logging.getLogger().addHandler(file_handler)

    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"\n{'='*60}\n")
        f.write(f"Session started at: {datetime.datetime.now()}\n")
        f.write(f"{'='*60}\n\n")

        with contextlib.redirect_stdout(_Tee(sys.stdout, f)), \
             contextlib.redirect_stderr(_Tee(sys.stderr, f)):
            yield

    # 退出时移除文件 handler，避免重复
    logging.getLogger().removeHandler(file_handler)
    file_handler.close()

if __name__ == "__main__":
    print(generate_log_path())