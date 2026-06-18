# Calib Tool

RDK 设备标定数据传输与处理工具。

## 目录结构

```
calib_tool/
├── config/               # 配置文件
│   ├── paths.yaml        # 路径配置
│   ├── device.yaml       # 设备连接配置
│   └── calib_params.yaml # 测量标定参数配置
├── utils/                # 工具模块
│   ├── ssh_client.py     # SSH/SCP/RSYNC 连接与传输
│   ├── paths.py          # 路径读取
│   ├── file_utils.py     # 文件工具
│   └── table_utils.py    # 表格工具
├── scripts/              # 脚本
│   ├── calibrate.py      # 自动执行标定
│   ├── scp_data.py       # 从 RDK 传输数据到本地
│   ├── process_calib.py  # 处理标定结果，生成 CSV
│   └── test.py           # 测试 SSH 连接
├── calib_data/           # 标定数据（完整目录）
├── calib_data_json/      # 标定数据（仅 json 文件）
├── calib_log/            # 日志
├── rosbag/               # rosbag 数据
└── .gitignore
```

## 环境准备

### 创建虚拟环境（推荐）

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 安装依赖

```bash
pip install -r requirements.txt
```

## 使用

### 运行主流程

```bash
python3 main.py
```

主流程依次执行：
1. `calibrate.calib()` — 自动执行标定
2. `ScpTransfer` — 从 RDK 传输标定数据到本地
3. `CalibProcessor` — 处理标定结果，计算并输出 CSV

### 各脚本说明

#### calibrate.py — 自动执行标定

在本地依次执行 shell 脚本（`get_rosbag.sh`、`calib.sh`），实时输出日志。

```bash
python3 scripts/calibrate.py
```

#### scp_data.py — 从 RDK 传输数据

通过 SSH 连接 RDK 设备，提供以下传输方法：

| 方法 | 说明 |
|------|------|
| `transfer_calib_json()` | 扫描 RDK 标定目录，仅传输 json 标定结果文件到本地 |
| `transfer_calib()` | 传输 RDK 上整个 calib 目录到本地 |
| `transfer_rosbag(rosbag=None)` | 传输 rosbag 数据，可指定具体 rosbag 或传输全部 |
| `remove_dir()` | 删除 RDK 上的 calib 目录 |
| `ssh_close()` | 关闭 SSH 连接 |

```bash
python3 scripts/scp_data.py
```

#### process_calib.py — 处理标定结果

解析标定日志和 json 结果文件，生成 CSV 表格并计算均值与方差。

| 方法 | 说明 |
|------|------|
| `process_log()` | 解析 calib_*log 日志，提取标定时间信息 |
| `write_csv()` | 读取 json 标定结果，写入 CSV 文件 |
| `calculate_stats()` | 计算标定结果的均值与方差，输出最终 CSV |

```bash
python3 scripts/process_calib.py
```

#### test.py — 测试 SSH 连接

测试能否正常连接 RDK 设备。

```bash
python3 scripts/test.py
```

### 复制结果到桌面

```bash
bash scripts/shell/cp_to_win.sh
```

## 配置

编辑 `config/device.yaml` 设置设备连接信息：

```yaml
device:
  host: 192.168.66.149
  user: root
  password: root
  port: 22
```
