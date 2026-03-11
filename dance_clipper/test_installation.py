#!/usr/bin/env python3
"""
test_installation.py - 测试安装和环境
运行此脚本检查所有依赖是否就绪
"""

import sys


def check_python_version():
    """检查Python版本"""
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print(f"✓ Python版本: {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"✗ Python版本过低: {version.major}.{version.minor}.{version.micro}")
        print("  需要 Python 3.8+")
        return False


def check_ffmpeg():
    """检查FFmpeg"""
    import subprocess
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0]
            print(f"✓ FFmpeg: {version_line}")
            return True
    except FileNotFoundError:
        pass
    
    print("✗ FFmpeg未安装或未添加到PATH")
    print("  安装指南: https://ffmpeg.org/download.html")
    return False


def check_python_packages():
    """检查Python包"""
    packages = {
        'numpy': 'numpy',
        'librosa': 'librosa',
        'yaml': 'pyyaml',
        'PIL': 'pillow'
    }
    
    all_ok = True
    for name, install_name in packages.items():
        try:
            __import__(name)
            print(f"✓ {install_name}")
        except ImportError:
            print(f"✗ {install_name} 未安装")
            print(f"  安装命令: pip install {install_name}")
            all_ok = False
    
    return all_ok


def check_project_files():
    """检查项目文件"""
    from pathlib import Path
    
    required_files = [
        'dance_clipper.py',
        'audio_analyzer.py',
        'video_analyzer.py',
        'config.yaml',
        'README.md'
    ]
    
    all_ok = True
    for file in required_files:
        if Path(file).exists():
            print(f"✓ {file}")
        else:
            print(f"✗ {file} 缺失")
            all_ok = False
    
    return all_ok


def test_basic_functionality():
    """测试基本功能"""
    try:
        from dance_clipper import DanceClipper, ClipConfig
        config = ClipConfig()
        clipper = DanceClipper(config)
        print("✓ 核心模块可以正常导入")
        return True
    except Exception as e:
        print(f"✗ 核心模块导入失败: {e}")
        return False


def main():
    print("🧪 舞蹈视频智能剪辑系统 - 安装测试\n")
    print("=" * 50)
    
    results = []
    
    print("\n1. Python版本检查:")
    results.append(check_python_version())
    
    print("\n2. FFmpeg检查:")
    results.append(check_ffmpeg())
    
    print("\n3. Python包检查:")
    results.append(check_python_packages())
    
    print("\n4. 项目文件检查:")
    results.append(check_project_files())
    
    print("\n5. 功能测试:")
    results.append(test_basic_functionality())
    
    print("\n" + "=" * 50)
    
    if all(results):
        print("\n🎉 所有检查通过！系统已就绪。")
        print("\n快速开始:")
        print("  python dance_clipper.py your_video.mp4 -o output.mp4 -t 30")
    else:
        print("\n⚠️ 部分检查未通过，请根据提示安装缺失的依赖。")
        sys.exit(1)


if __name__ == "__main__":
    main()
