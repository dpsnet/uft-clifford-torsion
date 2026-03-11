#!/bin/bash
# 统一场理论开放数据接口初始化脚本

WORKSPACE="/root/.openclaw/workspace/research_notes/data_pipeline"
echo "初始化开放数据接口..."

# 创建数据目录结构
mkdir -p ${WORKSPACE}/{gw,cmb,particle,atomic}
mkdir -p ${WORKSPACE}/gw/{ligo,virgo,kagra,nanograv}
mkdir -p ${WORKSPACE}/cmb/{planck,camb,simulations}
mkdir -p ${WORKSPACE}/particle/{pdg,lhc,measurements}
mkdir -p ${WORKSPACE}/atomic/{nist,nuclear,spectroscopy}
mkdir -p ${WORKSPACE}/code/{analysis,visualization,models}
mkdir -p ${WORKSPACE}/results/{figures,tables,reports}

# 创建数据索引文件
cat > ${WORKSPACE}/DATA_INDEX.md << 'EOF'
# 开放数据接口索引

## 引力波数据

### LIGO/Virgo/KAGRA
- **源**: GWOSC (https://www.gwosc.org/)
- **格式**: HDF5, GWPY
- **更新频率**: 事件触发
- **数据范围**: O1-O4 (2015-2025)

### 脉冲星计时阵列
- **源**: NANOGrav, IPTA, EPTA, PPTA
- **格式**: TXT, FITS
- **更新频率**: 年度
- **数据范围**: 纳赫兹引力波背景

## 宇宙学数据

### Planck CMB
- **源**: Planck Legacy Archive (https://pla.esac.esa.int/)
- **格式**: FITS
- **数据产品**: 功率谱、透镜势、前景图

### 大尺度结构
- **源**: SDSS, DESI, LSST
- **格式**: FITS, HDF5
- **数据产品**: 星系目录、功率谱、BAO

## 粒子物理数据

### 粒子数据手册 (PDG)
- **源**: PDG (https://pdg.lbl.gov/)
- **格式**: HTML, PDF, JSON
- **更新频率**: 年度

### LHC实验
- **源**: HEPData (https://www.hepdata.net/)
- **格式**: YAML, JSON
- **实验**: ATLAS, CMS, ALICE, LHCb

## 原子/核数据

### NIST原子光谱
- **源**: NIST ASD (https://physics.nist.gov/cgi-bin/ASD/energy1.pl)
- **格式**: HTML, ASCII
- **数据**: 能级、跃迁、电离能

### 原子质量评估 (AME)
- **源**: AME2020
- **格式**: ASCII
- **数据**: 原子质量、衰变数据

## 数据更新脚本

位于: ${WORKSPACE}/scripts/
- update_gw_data.sh - 更新引力波数据
- update_cmb_data.sh - 更新CMB数据
- update_particle_data.sh - 更新粒子数据
- update_atomic_data.sh - 更新原子数据

EOF

echo "数据目录结构创建完成"
echo "工作空间: ${WORKSPACE}"

# 创建Python数据分析环境配置
cat > ${WORKSPACE}/requirements.txt << 'EOF'
# 科学计算
numpy>=1.21.0
scipy>=1.7.0
matplotlib>=3.4.0
pandas>=1.3.0

# 天文学/宇宙学
astropy>=5.0.0
camb>=1.3.0
healpy>=1.15.0

# 引力波分析
ligo-segments>=1.2.0
igwn-auth-utils>=0.2.0

# 统计/机器学习
emcee>=3.1.0
scikit-learn>=1.0.0

# 数据处理
h5py>=3.6.0
requests>=2.27.0
beautifulsoup4>=4.10.0

# 可视化
plotly>=5.5.0
seaborn>=0.11.0
EOF

echo "Python依赖配置创建完成"

# 创建引力波数据下载脚本
cat > ${WORKSPACE}/scripts/download_gw_event.py << 'EOF'
#!/usr/bin/env python3
"""
下载LIGO/Virgo引力波事件数据
用法: python download_gw_event.py --event GW150914 --output-dir ./data/
"""

import argparse
import os
from gwpy.timeseries import TimeSeries

def download_gw_event(event_name, output_dir="./"):
    """下载指定引力波事件的应变数据"""
    
    # 事件时间字典（示例）
    event_times = {
        "GW150914": 1126259462,
        "GW170817": 1187008882,
        # 可扩展更多事件
    }
    
    if event_name not in event_times:
        print(f"未知事件: {event_name}")
        return
    
    gps_time = event_times[event_name]
    
    # 下载数据（LIGO Hanford和Livingston）
    for ifo in ["H1", "L1"]:
        try:
            print(f"下载 {ifo} 数据...")
            data = TimeSeries.fetch_open_data(ifo, gps_time-10, gps_time+10)
            output_file = os.path.join(output_dir, f"{event_name}_{ifo}_strain.hdf5")
            data.write(output_file)
            print(f"保存到: {output_file}")
        except Exception as e:
            print(f"下载 {ifo} 数据失败: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="下载引力波事件数据")
    parser.add_argument("--event", required=True, help="事件名称 (如 GW150914)")
    parser.add_argument("--output-dir", default="./", help="输出目录")
    
    args = parser.parse_args()
    download_gw_event(args.event, args.output_dir)
EOF

chmod +x ${WORKSPACE}/scripts/download_gw_event.py

echo "数据下载脚本创建完成"
echo "开放数据接口初始化完成"
