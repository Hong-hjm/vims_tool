# VIMS Tool

VIMS Tool 是一个面向 **RDK（地平线机器人开发套件）** 的辅助工具。目前主要功能包括：

- 对采集的rosbag进行标定，上传rosbag与结果至本机
- 对vio算法运行后的结果文件进行轨迹可视化等处理

---

## 目录

- [项目结构](#项目结构)
- [环境要求](#环境要求)
- [快速开始](#快速开始)
- [配置说明](#配置说明)
  - [设备配置 (`device.yaml`)](#设备配置-deviceyaml)
  - [路径配置 (`paths.yaml`)](#路径配置-pathsyaml)
  - [标定参数 (`calib_params.yaml`)](#标定参数-calib_paramsyaml)
- [使用指南](#使用指南)
  - [1. 自动标定流程](#1-自动标定流程)
  - [2. 标定结果处理](#2-标定结果处理)
  - [3. 数据传输](#3-数据传输)
  - [4. VIO 轨迹可视化](#4-vio-轨迹可视化)
- [输出说明](#输出说明)
- [依赖项](#依赖项)

---

## 项目结构

```
vims_tool/
├── calib.py                          # 标定主入口
├── evo_traj.py                       # VIO 轨迹可视化入口
├── requirements.txt                  # Python 依赖
├── config/
│   ├── calib_params.yaml             # 标定参数（外参初值、标定次数）
│   ├── device.yaml                   # RDK 设备连接信息
│   └── paths.yaml                    # 路径配置（RDK & 本地）
├── scripts/
│   ├── calibrate.py                  # 自动执行标定脚本
│   ├── process_calib.py              # 标定结果解析与 CSV 生成
│   ├── scp_data.py                   # RDK -> 本地数据传输
│   ├── test.py                       # 测试脚本
│   └── shell/
│       ├── run_calibrate/
│       │   ├── calib.sh              # 远程执行标定的 Shell 脚本
│       │   └── get_rosbag.sh         # 获取标定 rosbag 列表
│       ├── remove/
│       │   └── rm_data.sh            # 删除 RDK 上的数据
│       ├── zip/
│       │   └── zip.sh                # 压缩目录脚本
│       └── evo/
│           ├── set_evo_Agg.sh        # 关闭 evo 可视化（后端设为 Agg）
│           └── set_evo_TkAgg.sh      # 开启 evo 可视化（后端设为 TkAgg）
└── utils/
    ├── file_utils.py                 # 文件操作工具
    ├── log_utils.py                  # 日志捕获与输出重定向
    ├── paths.py                      # 路径加载模块
    ├── ssh_client.py                 # SSH / rsync 远程操作
    └── table_utils.py                # 表格处理与统计
```

---

## 环境要求

- **Python** ≥ 3.10
- **RDK 设备**（如 RDK X5），已配置 ROS 2 标定环境
- **本地主机**（x86 Linux），可通过 SSH 访问 RDK 设备
- **evo** — SLAM 轨迹评估工具（用于 VIO 轨迹可视化）

---

## 快速开始

### 1. 安装 Python 依赖

```bash
cd /path/to/your/vim_tool
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. 安装系统工具

标定脚本依赖 `yq`（YAML 命令行处理器）、`sshpass`（SSH 免交互密码登录），脚本会自动安装，也可手动安装：

```bash
sudo apt-get install -y sshpass
sudo wget https://github.com/mikefarah/yq/releases/latest/download/yq_linux_amd64 -O /usr/bin/yq
sudo chmod +x /usr/bin/yq
```

系统默认已安装 `rsync` 若系统不存在 `rsync` 需手动安装：

```bash
rsync --version             # 检查是否输出rsync版本号，若无版本号相关信息，执行下方命令进行安装
sudo apt update
sudo apt install rsync
```


### 3. 配置设备与路径

编辑 `config/` 目录下的配置文件（详见 [配置说明](#配置说明)）。

## 配置说明

### 设备配置 (`device.yaml`)

配置 RDK 设备的 SSH 连接信息：

```yaml
device:
  platform: x5              # 设备平台
  ros_distro: humble        # ROS 2 发行版
  host: 192.168.66.149      # RDK IP 地址
  user: root                # SSH 用户名
  password: root            # SSH 密码
  port: 22                  # SSH 端口
```

### 路径配置 (`paths.yaml`)

配置 RDK 端和本地端的文件路径，以及 evo 轨迹可视化参数：

> **⚠️ 注意：** 存放 rosbag 的目录 `rosbag_dir` 中每个路径的**最后一级目录名**需要遵循命名规则，标定脚本会根据目录名判断对应的视角类型：
> - 以 `pingshi` 开头 → 平视（`frontal_view`）
> - 以 `fushi` 开头 → 俯视（`overhead_view`）
> - 以 `yangshi` 开头 → 仰视（`upward_view`）
>
> 例如：`pingshi_1`、`pingshi_2`、`fushi_1`、`yangshi_1` 都是合法的目录名。

```yaml
RDK:
  paths:
    calib_data_dir: "/root/calibration/0.0.2/calib_data/"   # RDK 标定数据目录
    rosbag_dir:                                             # RDK rosbag 目录列表
      - "/root/calibration/0.0.2/pingshi_1/"
      - "/root/calibration/0.0.2/fushi_1/"
      - "/root/calibration/0.0.2/yangshi_1/"

x86:
  paths:
    calib_data_dir: "calib_data"           # 本地标定数据目录
    calib_data_json_dir: "calib_data_json" # 本地标定 JSON 目录
    log_dir: "log"                         # 本地日志目录
    rosbag_dir: "rosbag"                   # 本地 rosbag 目录
  files:
    calib_params_file: "calibration_result.json"  # 标定结果文件名

evo:
  vio_results:                              # VIO 结果目录列表
    - "/mnt/c/Users/.../v1/"
    - "/mnt/c/Users/.../v2/"
    - "/mnt/c/Users/.../v3/"
  tum_file: "trajectory/ov_est.tum"         # TUM 轨迹文件相对路径
  output_image: "vio_output_img/"           # 轨迹截图输出目录
```

### 标定参数 (`calib_params.yaml`)

配置各视角的外参初值和标定次数：

```yaml
calibration:
  # 格式: [roll_deg, pitch_deg, yaw_deg, x, y, z]
  frontal_view: [0.0, 0.0, 0.0, 0.135, 0.04, 0.152]     # 平视
  overhead_view: [0.0, 5.94, 0.0, 0.139, 0.04, 0.149]   # 俯视
  upward_view: [0.0, -5.94, 0.0, 0.13, 0.04, 0.164]     # 仰视

calib_num: 1   # 每个 rosbag 的标定次数
```

---

## 使用指南

### 1. 自动标定流程

`calib.py` 是标定流程的主入口，执行以下步骤：

1. **读取标定次数** — 支持通过命令行参数 `calib_num:=N` 临时覆盖配置文件中的标定次数
2. **远程标定** — 调用 `calib.sh`，通过 SSH 在 RDK 设备上依次执行每个 rosbag 的标定
3. **传输数据** — 将RDK中生成的标定结果文件，传输到本机
4. **结果处理** — 处理标定数据和日志，计算结果平均值与标准差，生成 CSV 报表

```bash
# 默认标定（使用配置文件中的 calib_num）
python calib.py

# 指定标定次数（临时覆盖）
python calib.py calib_num:=3
```

### 2. 标定结果处理

`process_calib.py` 中的 `CalibProcessor` 类负责：

- **解析日志** — 从标定日志中提取每个 rosbag 的标定耗时
- **生成 CSV** — 将标定结果（平移向量、旋转角度）写入 `calib_params.csv`
- **统计分析** — 计算每个视角下各 rosbag 的均值和方差，输出到 `calculate_calib_params.csv`

```python
from scripts.process_calib import CalibProcessor

processor = CalibProcessor()
processor.log_dir = "log/20260608_173436"   # 指定日志目录
processor.process_log()                     # 解析日志
processor.write_csv()                       # 生成 CSV
processor.calculate_stats()                 # 计算统计量
```

### 3. 数据传输

`scp_data.py` 中的 `ScpTransfer` 类提供 RDK 与本地之间的文件传输功能：

- **传输标定 JSON** — 仅传输 `calibration_result.json` 文件
- **传输完整标定目录** — 传输整个 `calib_data` 目录
- **传输 rosbag** — 传输 rosbag 数据包
- **删除 RDK 数据** — 通过 SSH 远程删除 RDK 上的标定数据

### 4. VIO 轨迹可视化

`evo_traj.py` 提供 VIO 轨迹的批量可视化功能：

- 自动关闭 evo 的 GUI 显示（后端设为 Agg），适合无图形界面的环境
- 批量处理多个 `vio_results` 目录下的 TUM 格式轨迹文件
- 为每个 rosbag 生成轨迹截图
- 提取轨迹终点坐标并保存到 TXT 文件
- 支持多线程并行处理
- 自动压缩 `vio_result_*` 子文件夹

```bash
# 使用配置文件中的路径
python evo_traj.py

# 指定要处理的目录
python evo_traj.py /path/to/v1/ /path/to/v2/
```

---

## 输出说明

| 文件 | 说明 |
|------|------|
| `calib_params.csv` | 标定结果明细表，包含每个 rosbag 每次标定的平移、旋转和耗时 |
| `calculate_calib_params.csv` | 标定结果统计表，包含各 rosbag 的均值和方差 |
| `log/` | 标定流程日志，按时间戳分目录保存 |
| `calib_data/` | 从 RDK 传输到本地的标定数据 |
| `calib_data_json/` | 提取的标定 JSON 文件 |
| `vio_output_img/` | VIO 轨迹截图 |
| `*.txt` | VIO 轨迹终点坐标记录 |

---

## 依赖项

### Python 包

- `pyyaml` — YAML 配置文件解析
- `paramiko` — SSH 远程连接
- `pandas` — 数据处理与 CSV 输出
- `evo` — SLAM 轨迹评估与可视化

### 系统工具

- `sshpass` — SSH 免交互密码登录
- `yq` — 命令行 YAML 处理器
- `rsync` — 远程文件同步