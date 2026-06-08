#!/bin/bash
# 重命名标定结果目录和文件

CALIB_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
# echo $CALIB_DIR

# 查找已存在的最大编号（目录/文件都查）
max_n=0
for item in ${CALIB_DIR}/calib_data_* ${CALIB_DIR}/calib_data_json_* ${CALIB_DIR}/calib_params_*.csv ${CALIB_DIR}/calculate_calib_params_*.csv; do
    [ -e "$item" ] || continue
    base=$(basename "$item")
    # 提取编号：calib_data_1 -> 1, calib_data_json_2 -> 2, ...
    n=$(echo "$base" | grep -oP '(?<=_)\d+' | head -1)
    if [[ "$n" =~ ^[0-9]+$ ]] && [ "$n" -gt "$max_n" ]; then
        max_n=$n
    fi
done
next_n=$((max_n + 1))

mv ${CALIB_DIR}/calib_data ${CALIB_DIR}/calib_data_${next_n}
mv ${CALIB_DIR}/calib_data_json ${CALIB_DIR}/calib_data_json_${next_n}
mv ${CALIB_DIR}/calib_params.csv ${CALIB_DIR}/calib_params_${next_n}.csv
mv ${CALIB_DIR}/calculate_calib_params.csv ${CALIB_DIR}/calculate_calib_params_${next_n}.csv