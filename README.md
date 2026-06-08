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
│   ├── process_calib.py  # 主脚本
│   └── test.py           # 测试脚本
├── calib_data/           # 标定数据（完整目录）
├── calib_data_json/      # 标定数据（仅 json 文件）
├── calib_log/            # 日志
├── rosbag/               # rosbag 数据
└── .gitignore
```

## 使用

### 主脚本 (process_calib.py)

运行主脚本：
```bash
python scripts/process_calib.py
```

`Ctrl+C` 可终止传输。

### 复制结果到桌面

```bash
bash scripts/shell/cp_to_win.sh
```

