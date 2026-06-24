# 运行 evo_traj 命令，可视化 TUM 格式的轨迹文件，并保存截图和终点坐标
import subprocess
import re
import math
import sys
import logging
import argparse
from pathlib import Path
from utils import paths, file_utils
from concurrent.futures import ThreadPoolExecutor, as_completed

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger(__name__)

class EVO:
    def __init__(self):
        self.path_length = None
        self.dev = None

    def run_evo_traj(self, tum_file_path, output_image_path):
        """执行 evo_traj 命令，成功返回 True，失败返回 False"""
        cmd = ["evo_traj", "tum", str(tum_file_path), "--save_plot", str(output_image_path), "--no_warnings"]
        
        try:
            result = subprocess.run(cmd, text=True, capture_output=True, check=True)
            output = result.stdout.strip()
            # 获取轨迹总长度
            match = re.search(r'(\d+\.?\d*)m\s+path length', output)
            if match:
                self.path_length = float(match.group(1))

            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Command failed, return code: {e.returncode}")
            return False
        except FileNotFoundError:
            logger.error("evo_traj command not found, please install evo toolkit")
            return False

    def read_last_pose(self, tum_file_path):
        """读取 TUM 文件最后一行，提取 [tx, ty, tz] 列表"""
        try:
            with open(tum_file_path, 'r') as f:
                last_line = None
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        last_line = line
            if not last_line:
                return None
            parts = last_line.split()
            if len(parts) < 4:
                return None
            return [float(parts[1]), float(parts[2]), float(parts[3])]
        except Exception as e:
            logger.error(f"Failed to read TUM file {tum_file_path}: {e}")
            return None

    def process_vio_results(self, vio_results, tum_file_rel, output_base_path, txt_name):
        """处理单个 vio_results 路径下的所有 rosbag"""
        
        rosbag_dirs = file_utils.find_rosbag_dirs(vio_results)
        
        success = 0
        fail = 0
        
        # TXT 文件名用传入的 txt_name 命名（如 v1, v2, v3），覆盖写入
        txt_path = output_base_path / f"{txt_name}.txt"
        
        with open(txt_path, 'w') as f:
            for rosbag_dir in rosbag_dirs:
                tum_file_path: Path = rosbag_dir / tum_file_rel
                
                if not tum_file_path.exists():
                    logger.warning(f"TUM file not found, skip: {tum_file_path}")
                    fail += 1
                    continue
                
                rosbag_output_dir: Path = output_base_path / rosbag_dir.name
                rosbag_output_dir.mkdir(parents=True, exist_ok=True)
                
                output_image_path = rosbag_output_dir / "trajectory_plot.png"
                
                logger.info(f"Processing rosbag: {rosbag_dir.name}")
                logger.info(f"  TUM: {tum_file_path}")
                logger.info(f"  Output: {output_image_path}")
                
                # 读取最后一行位姿数据 [tx, ty, tz]，计算距原点的偏差
                pose = self.read_last_pose(tum_file_path)
                if pose:
                    self.dev = math.sqrt(pose[0]**2 + pose[1]**2 + pose[2]**2)
                    logger.info(f"  Last pose: {pose}, dev: {self.dev:.3f}")
                else:
                    self.dev = None
                    logger.warning(f"  No valid pose data found")
                
                ok = self.run_evo_traj(tum_file_path, output_image_path)
                
                if pose and ok and self.dev is not None and self.path_length > 0:
                    ratio = self.dev / self.path_length
                    logger.info(f"  dev/path_length: {ratio:.4f}")
                    f.write(f"{rosbag_dir.name} , {pose} , {(ratio*100):.4f}%\n")
                elif pose:
                    f.write(f"{rosbag_dir.name} , {pose} N/A\n")
                else:
                    f.write(f"{rosbag_dir.name} N/A\n")
                if ok:
                    success += 1
                else:
                    fail += 1
        
        logger.info(f"Pose data saved to: {txt_path}")
        return success, fail

    def get_traj(self):
        """运行 evo_traj 命令，可视化 TUM 格式的轨迹文件，并保存截图和终点坐标"""
        parser = argparse.ArgumentParser(description="运行 evo_traj 可视化 TUM 轨迹并保存截图")
        parser.add_argument("dirs", nargs="*", help="要处理的 vio_results 目录（覆盖配置文件中的设置）")
        args = parser.parse_args()
        
        config: dict = paths.evo_config
        tum_file_rel = config.get("tum_file")
        output_base = config.get("output_image")
        
        # 如果传了命令行参数则使用传入的，否则使用配置文件中的
        if args.dirs:
            vio_results_list = args.dirs
        else:
            vio_results_list = config.get("vio_results")
            if not vio_results_list:
                logger.error("Missing vio_results in config")
                sys.exit(1)
            if isinstance(vio_results_list, str):
                vio_results_list = [vio_results_list]
        
        
        num_threads = len(vio_results_list)
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            future_to_path = {}
            for path in vio_results_list:
                # TXT 文件名用路径的最后一级目录名（如 v1, v2, v3）

                subprocess.run(["bash", paths.zip_sh, path], check=True)

                rosbag_parent = Path(path).stem if Path(path).suffix else Path(path).name
                
                output_base_path = path / Path(output_base)
                output_base_path.mkdir(parents=True, exist_ok=True)
                
                future = executor.submit(self.process_vio_results, path, tum_file_rel, output_base_path, rosbag_parent)
                future_to_path[future] = path
            
            total_success = 0
            total_fail = 0
            
            for future in as_completed(future_to_path):
                path = future_to_path[future]
                try:
                    success, fail = future.result()
                    total_success += success
                    total_fail += fail
                except Exception as e:
                    logger.error(f"Error processing {path}: {e}")
                    total_fail += 1
        
        total_dirs = total_success + total_fail
        logger.info(f"All done! Success: {total_success}, Failed: {total_fail}, Total: {total_dirs}")

if __name__ == "__main__":
    s = EVO()
    s.get_traj()