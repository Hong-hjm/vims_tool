# 传输文件

import logging
import subprocess
from pathlib import Path
from utils import paths, file_utils, ssh_client, log_utils

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("SCP_DATA")

# 从 RDK 设备传输标定数据和日志到本地
class ScpTransfer:
    def __init__(self):
        self.action = ssh_client.SSHAction()
        if not self.action.ssh.client:
            logger.error("SSH connection failed")
            self.action = None

        self.calib_result = []      # 存储标定文件路径的列表

    def ssh_close(self):
        if self.action:
            logger.info("connection closed")
            self.action.close()

    # 只传输标定文件,返回RDK文件路径列表
    def transfer_calib_json(self) -> list:
        logger.info("="*30)
        logger.info("start to transfer calibrate_result.json")
        if not self.action:
            logger.error("connection lost")
            return
        if not self.action.exists(paths.RDK_calib_data_dir):
            logger.error(f"path {paths.RDK_calib_data_dir} does not exist")
            return

        def _scan_rdk_dirs(remote_dir):
            # 扫描 RDK 目录，按目录层级构建嵌套列表，直到目录下存在目标 json 文件才返回路径
            result = []

            # 检查RDK当前目录是否包含目标 json 文件
            dir_list = self.action.list_dir(remote_dir)
            for item in dir_list:
                sub_dir = Path(remote_dir) / item[1]
                if item[0] == 'file' and item[1] == paths.calib_params_file:
                    # print(sub_dir)
                    result.append(str(sub_dir))

                if item[0] == 'dir':
                    result.extend(_scan_rdk_dirs(sub_dir))

            return result

        logger.info(f"Scanning RDK directory finished")
        self.calib_result = _scan_rdk_dirs(paths.RDK_calib_data_dir)

        if not self.calib_result:
            logger.error(f"No calib json file found in {paths.RDK_calib_data_dir}")
            return
        for remote_dir in self.calib_result:
            remote_dir: str
            cut_dir = remote_dir.replace(paths.RDK_calib_data_dir, "").replace(paths.calib_params_file, "")
            local_dir = paths.calib_data_json_dir / cut_dir
            file_utils.check_path(local_dir)
            self.action.rsync_from_rdk(remote_dir, local_dir)
        logger.info("transfer finished")

        return self.calib_result

    #传输整个 calib 目录
    def transfer_calib(self):
        logger.info("="*30)
        logger.info("start to transfer calib_data dir")
        if not self.action:
            logger.error("connection lost")
            return
        if not self.action.exists(paths.RDK_calib_data_dir):
            logger.warning(f"path {paths.RDK_calib_data_dir} does not exist")
            return

        logger.info(f"Directory exists on RDK device: {paths.RDK_calib_data_dir}")
        p = Path(paths.RDK_calib_data_dir) / "*"
        self.action.rsync_from_rdk(p, paths.calib_data_dir)
        logger.info("transfer finished")

    # 删除RDK的calib目录
    def remove_dir(self):
        subprocess.run(["bash", paths.rm_data_sh])
        logger.info("calib_data was removed")

    # 传输 log
    # def transfer_log(self):

    #     if not self.action:
    #         return

    #     if self.action.exists(paths.RDK_log_dir):
    #         logger.info(f"Directory exists on RDK device: {paths.RDK_log_dir}")
    #         self.action.rsync_from_rdk(paths.RDK_log_dir, paths.log_dir)
    #     else:
    #         logger.error(f"path {paths.RDK_log_dir} does not exist")

    # 传输 rosbag，可指定rosbag
    def transfer_rosbag(self, rosbag=None):
        logger.info("="*30)
        logger.info("start to transfer rosbag")
        if not self.action:
            logger.error("connection lost")
            return
        if rosbag is not None and self.action.exists(rosbag):
            logger.info(f"Directory exists on RDK device: {rosbag}")
            self.action.rsync_from_rdk(rosbag, paths.rosbag_dir)
        elif rosbag is not None and not self.action.exists(rosbag):
            logger.error(f"path {rosbag} rosbag does not exist")
        else:
            for p in paths.RDK_rosbag_dir:
                if self.action.exists(p):
                    logger.info(f"Directory exists on RDK device: {p}")
                    self.action.rsync_from_rdk(p, paths.rosbag_dir)
                else:
                    logger.error(f"path {p} rosbag does not exist")
        logger.info("transfer finished")


if __name__ == "__main__":
    log_dir = log_utils.generate_log_path()
    with log_utils.capture_all_output(log_dir):
        transfer = ScpTransfer()
        transfer.transfer_calib_json()
        transfer.transfer_calib()
        transfer.transfer_rosbag()
        transfer.ssh_close()
