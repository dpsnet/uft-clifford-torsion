"""
gpu_accelerator.py
GPU 加速模块

利用 CUDA 加速视频处理和音频分析
"""

import os
import subprocess
import numpy as np
from typing import Optional, Tuple
from pathlib import Path


class GPUAccelerator:
    """GPU 加速器"""
    
    def __init__(self):
        self.cuda_available = self._check_cuda()
        self.gpu_info = self._get_gpu_info() if self.cuda_available else None
        
    def _check_cuda(self) -> bool:
        """检查 CUDA 是否可用"""
        try:
            # 检查 nvidia-smi
            result = subprocess.run(
                ['nvidia-smi'],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        
        # 检查 PyTorch CUDA
        try:
            import torch
            if torch.cuda.is_available():
                return True
        except ImportError:
            pass
        
        return False
    
    def _get_gpu_info(self) -> dict:
        """获取 GPU 信息"""
        info = {"available": False, "devices": []}
        
        try:
            import torch
            if torch.cuda.is_available():
                info["available"] = True
                info["device_count"] = torch.cuda.device_count()
                info["current_device"] = torch.cuda.current_device()
                
                for i in range(torch.cuda.device_count()):
                    props = torch.cuda.get_device_properties(i)
                    info["devices"].append({
                        "id": i,
                        "name": torch.cuda.get_device_name(i),
                        "total_memory": props.total_memory / (1024**3),  # GB
                        "compute_capability": f"{props.major}.{props.minor}"
                    })
        except ImportError:
            pass
        
        return info
    
    def is_available(self) -> bool:
        """GPU 是否可用"""
        return self.cuda_available
    
    def get_ffmpeg_cuda_flags(self) -> list:
        """
        获取 FFmpeg 的 CUDA 加速参数
        用于视频解码/编码加速
        """
        if not self.cuda_available:
            return []
        
        # FFmpeg CUDA 加速参数
        return [
            '-hwaccel', 'cuda',
            '-hwaccel_output_format', 'cuda'
        ]
    
    def get_video_codec(self, use_gpu: bool = True) -> str:
        """获取推荐的视频编码器"""
        if use_gpu and self.cuda_available:
            return 'h264_nvenc'  # NVIDIA GPU 编码
        return 'libx264'  # CPU 编码
    
    def encode_video_gpu(self, input_path: str, output_path: str, 
                         start: float = None, duration: float = None) -> bool:
        """
        使用 GPU 加速编码视频
        """
        if not self.cuda_available:
            return False
        
        cmd = ['ffmpeg', '-y']
        
        # 添加 CUDA 硬件加速
        cmd.extend(self.get_ffmpeg_cuda_flags())
        
        # 输入
        cmd.extend(['-i', input_path])
        
        # 时间裁剪
        if start is not None:
            cmd.extend(['-ss', str(start)])
        if duration is not None:
            cmd.extend(['-t', str(duration)])
        
        # GPU 编码
        cmd.extend([
            '-c:v', 'h264_nvenc',
            '-preset', 'fast',  # GPU编码用fast，quality会慢很多
            '-cq', '23',  # 质量
            '-c:a', 'copy',
            output_path
        ])
        
        try:
            subprocess.run(cmd, capture_output=True, check=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"GPU编码失败，回退到CPU: {e}")
            return False
    
    def analyze_audio_gpu(self, audio_data: np.ndarray, sr: int) -> Optional[Tuple[float, np.ndarray]]:
        """
        使用 GPU 加速音频分析（如果可用）
        
        Returns:
            (bpm, beat_frames) 或 None
        """
        if not self.cuda_available:
            return None
        
        try:
            import torch
            import librosa
            
            # 将音频数据移到 GPU
            device = torch.device('cuda')
            
            # 使用 librosa 但尝试利用 GPU 加速某些操作
            # 注意：librosa 本身主要用 CPU，这里主要是演示框架
            
            # 计算 onset envelope（CPU）
            onset_env = librosa.onset.onset_strength(
                y=audio_data, sr=sr
            )
            
            # BPM 检测（CPU）
            tempo = librosa.beat.tempo(
                onset_envelope=onset_env, sr=sr
            )[0]
            
            # 节拍跟踪
            _, beat_frames = librosa.beat.beat_track(
                onset_envelope=onset_env, sr=sr
            )
            
            return float(tempo), beat_frames
            
        except Exception as e:
            print(f"GPU音频分析失败: {e}")
            return None
    
    def batch_process_gpu(self, video_paths: list, 
                         process_func, max_workers: int = 4) -> list:
        """
        批量 GPU 处理
        
        Args:
            video_paths: 视频路径列表
            process_func: 处理函数
            max_workers: 最大并行数（GPU显存限制）
            
        Returns:
            处理结果列表
        """
        if not self.cuda_available:
            # 回退到 CPU 串行处理
            return [process_func(path) for path in video_paths]
        
        from concurrent.futures import ThreadPoolExecutor
        
        # GPU 处理通常受显存限制，不宜开太多线程
        workers = min(max_workers, len(video_paths))
        
        with ThreadPoolExecutor(max_workers=workers) as executor:
            results = list(executor.map(process_func, video_paths))
        
        return results
    
    def estimate_processing_time(self, video_duration: float, 
                                  resolution: str = '1080p',
                                  use_gpu: bool = True) -> float:
        """
        预估处理时间（秒）
        
        Returns:
            预估处理时间
        """
        # 基于经验值的估算
        gpu_speedup = 3.0 if (use_gpu and self.cuda_available) else 1.0
        
        # 不同分辨率的基础处理速度（秒/秒视频）
        base_speed = {
            '720p': 0.3,
            '1080p': 0.5,
            '4k': 2.0
        }.get(resolution, 0.5)
        
        estimated = video_duration * base_speed / gpu_speedup
        return max(1.0, estimated)  # 最少1秒
    
    def print_info(self):
        """打印 GPU 信息"""
        if not self.cuda_available:
            print("❌ GPU 加速不可用")
            print("   请检查 NVIDIA 驱动和 CUDA 安装")
            return
        
        print("✅ GPU 加速可用")
        
        if self.gpu_info and self.gpu_info.get("devices"):
            print(f"   检测到 {self.gpu_info['device_count']} 个 GPU 设备:")
            for device in self.gpu_info["devices"]:
                print(f"   - {device['name']}")
                print(f"     显存: {device['total_memory']:.1f} GB")
                print(f"     计算能力: {device['compute_capability']}")


# 便捷函数
def check_gpu() -> bool:
    """检查 GPU 是否可用"""
    acc = GPUAccelerator()
    return acc.is_available()


def get_gpu_info():
    """获取 GPU 信息"""
    acc = GPUAccelerator()
    return acc.gpu_info


if __name__ == "__main__":
    # 测试
    print("🚀 GPU 加速器测试\n")
    
    acc = GPUAccelerator()
    acc.print_info()
    
    print(f"\nFFmpeg CUDA 参数: {acc.get_ffmpeg_cuda_flags()}")
    print(f"推荐编码器: {acc.get_video_codec()}")
    
    # 预估时间测试
    for res in ['720p', '1080p', '4k']:
        time_cpu = acc.estimate_processing_time(300, res, use_gpu=False)
        time_gpu = acc.estimate_processing_time(300, res, use_gpu=True)
        print(f"\n{res} 视频 (5分钟):")
        print(f"  CPU 预估: {time_cpu:.1f}s")
        print(f"  GPU 预估: {time_gpu:.1f}s")
        print(f"  加速比: {time_cpu/time_gpu:.1f}x")
