#!/usr/bin/env python3
# SSH 连接 RDK 设备，参数从 device.yaml 读取
import os
import sys
import select
import yaml
import paramiko
import subprocess
import logging
import file_utils, paths

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger(__name__)

def _confirm_with_timeout(prompt, timeout=5):
    # 带超时的确认，timeout 秒无输入自动继续
    logger.info(f"{prompt} (y/n, {timeout}s timeout, auto-transfer and overwrite file)")
    if sys.stdin in select.select([sys.stdin], [], [], timeout)[0]:
        choice = sys.stdin.readline().strip().lower()
        if choice == 'y':
            return True
        else:
            return False
    else:
        logger.info(f"Timeout, auto continue")
    return False

config_device = paths.calib_tool / "config" / "device.yaml"
# SSH连接
class SSHClient:
    def __init__(self):
        with open(config_device, "r") as f:
            config: dict = yaml.safe_load(f)
        self.device: dict = config.get("device")

        host = self.device.get("host")
        user = self.device.get("user")
        password = self.device.get("password")
        port = self.device.get("port")

        if not host or not user or not password or not port:
            logger.error("do not have data configured in device.yaml")
            return

        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.client.connect(host, port=port, username=user, password=password)

    def close(self):
        if self.client:
            self.client.close()


class SSHAction:
    def __init__(self):
        self.ssh = SSHClient()

    def close(self):
        self.ssh.close()

    # 是否存在该目录
    def exists(self, path) -> bool:
        if not self.ssh.client:
            logger.error("not connected")
            return False

        cmd = f"ls {path} 2>/dev/null"
        _, stdout, _ = self.ssh.client.exec_command(cmd)
        output = stdout.read().decode().strip()
        
        return bool(output)  # 非空返回 True
    # 删除
    def remove(self, path) -> bool:
        if not self.ssh.client:
            logger.error("not connected")
            return False

        cmd = f"rm -rf {path}"
        _, stdout, stderr = self.ssh.client.exec_command(cmd)
        if stdout.channel.recv_exit_status() == 0:
            logger.info(f"removed {path} on RDK device")
            return True
        else:
            error = stderr.read().decode()
            logger.error(f"failed to remove {path} on RDK device, {error}")
            return False
    
    # 获取目录下的文件列表，区分目录和文件
    def list_dir(self, path) -> list:
        if not self.ssh.client:
            logger.error("not connected")
            return []

        cmd = f"ls -F {path}"
        _, stdout, _ = self.ssh.client.exec_command(cmd)
        if stdout.channel.recv_exit_status() == 0:
            output = stdout.read().decode().strip()
            if not output:
                return []
            items = []
            for item in output.split("\n"):
                if item.endswith("/"):
                    items.append(('dir', item))    # 目录名
                else:
                    items.append(('file', item))   # 文件名
            return items
        else:
            logger.error(f"failed to list directory: {path}")
            return []

    # 传输
    def rsync_from_rdk(self, remote_path, local_path):
        # 是否保存原有文件
        save_flag = False
        if file_utils.check_path(local_path) and not file_utils.is_dir_empty(local_path):
            save_flag = _confirm_with_timeout(f"{local_path} is already exists. Please confirm whether to keep the file")
        
        host = self.ssh.device.get("host")
        user = self.ssh.device.get("user")
        password = self.ssh.device.get("password")
        port = self.ssh.device.get("port")

        env = os.environ.copy()
        env["SSHPASS"] = password

        # 构建 rsync 参数
        if save_flag:
            rsync_opts = [
                'rsync', '-avP',
                '--ignore-existing',    # 保护已存在的文件（不覆盖）
                '--partial',            # 断点续传
                '-e', f'ssh -p {port} -o StrictHostKeyChecking=no',
                f'{user}@{host}:{remote_path}',
                local_path
            ]
        else:
            rsync_opts = [
                'rsync', '-avP',
                '--delete',      # 镜像同步（删除目标目录中多余的文件）
                '--partial',     # 断点续传
                '-e', f'ssh -p {port} -o StrictHostKeyChecking=no',
                f'{user}@{host}:{remote_path}',
                local_path
            ]

        max_retries = 10
        for attempt in range(1, max_retries + 1):
            try:
                process = subprocess.Popen(['sshpass', '-e'] + rsync_opts,
                                           env=env,
                                           stdout=subprocess.PIPE,
                                           stderr=subprocess.STDOUT,
                                           text=True)
                for line in process.stdout:
                    print(line, end="")
                ret = process.wait()
                if ret == 0:
                    logger.info(f"rsync finish: {remote_path} -> {local_path}")
                    return
                else:
                    logger.error(f"rsync failed (attempt {attempt}/{max_retries}): {remote_path} -> {local_path}")
            except KeyboardInterrupt:
                logger.info("rsync interrupted by user, exiting...")
                raise
            except Exception as e:
                logger.error(f"rsync error (attempt {attempt}/{max_retries}): {e}")
        logger.error(f"rsync failed after {max_retries} attempts: {remote_path} -> {local_path}")

if __name__ == "__main__":
    print(config_device)