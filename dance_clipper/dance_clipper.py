"""
Dance Video Smart Clipper
舞蹈视频智能剪辑系统

核心功能：将长舞蹈视频按音乐结构和动作连贯性缩编为指定时长的短视频
"""

import os
import json
import tempfile
import subprocess
from pathlib import Path
from dataclasses import dataclass
from typing import List, Tuple, Optional
import numpy as np

# 导入新模块
from dance_presets import PresetManager, get_preset
from gpu_accelerator import GPUAccelerator


@dataclass
class ClipConfig:
    """剪辑配置"""
    target_duration: float = 30.0  # 目标时长（秒）
    tolerance: float = 2.0  # 时长容差（±2秒）
    min_segment_duration: float = 4.0  # 最小片段时长（至少4秒保证完整性）
    max_segments: int = 3  # 最多拼接几段
    bpm_range: Tuple[int, int] = (60, 180)  # 合理的BPM范围
    # 音频权重 vs 视频权重（0-1）
    audio_weight: float = 0.6  # 音乐结构更重要
    video_weight: float = 0.4
    # 预设类型
    preset: str = None


@dataclass
class BeatInfo:
    """节拍信息"""
    time: float  # 时间点（秒）
    is_downbeat: bool  # 是否强拍
    bpm: float  # 当时的BPM


@dataclass
class VideoSegment:
    """视频片段候选"""
    start: float
    end: float
    music_score: float  # 音乐完整性得分
    motion_score: float  # 动作连贯性得分
    total_score: float


class DanceClipper:
    """舞蹈视频智能剪辑器"""
    
    def __init__(self, config: ClipConfig = None):
        self.config = config or ClipConfig()
        self.temp_dir = tempfile.mkdtemp(prefix="dance_clip_")
        self.gpu = GPUAccelerator()
        
        # 如果指定了预设，应用预设配置
        if self.config.preset:
            self._apply_preset(self.config.preset)
    
    def _apply_preset(self, preset_name: str):
        """应用舞蹈预设"""
        try:
            preset = get_preset(preset_name)
            self.config.bpm_range = preset.bpm_range
            self.config.audio_weight = preset.audio_weight
            self.config.video_weight = preset.video_weight
            self.config.min_segment_duration = preset.min_segment_duration
            print(f"🎭 应用预设: {preset.name_cn} ({preset_name})")
        except ValueError:
            print(f"⚠️ 未知预设: {preset_name}，使用默认配置")
    
    def clip(self, input_path: str, output_path: str, use_gpu: bool = True) -> dict:
        """
        主入口：智能剪辑舞蹈视频
        
        Args:
            input_path: 输入视频路径
            output_path: 输出视频路径
            use_gpu: 是否使用 GPU 加速
            
        Returns:
            剪辑报告字典
        """
        print(f"🎬 开始处理: {input_path}")
        
        # 检查 GPU
        if use_gpu and self.gpu.is_available():
            print("⚡ 使用 GPU 加速")
        
        # 1. 提取音频
        audio_path = self._extract_audio(input_path)
        print(f"✓ 音频提取完成: {audio_path}")
        
        # 2. 音频分析（节拍、BPM、乐句）
        beats = self._analyze_audio(audio_path)
        print(f"✓ 音频分析完成，检测到 {len(beats)} 个节拍，BPM: {beats[0].bpm if beats else 'N/A'}")
        
        # 自动检测舞蹈类型（如果未指定）
        if not self.config.preset and beats:
            detected = PresetManager.auto_detect_preset(beats[0].bpm)
            print(f"🎯 自动检测舞蹈类型: {get_preset(detected).name_cn}")
        
        # 3. 视频分析（动作密度、场景切换）
        video_info = self._analyze_video(input_path)
        print(f"✓ 视频分析完成，时长: {video_info['duration']:.1f}s, 分辨率: {video_info['width']}x{video_info['height']}")
        
        # 4. 生成候选片段
        candidates = self._generate_candidates(beats, video_info)
        print(f"✓ 生成 {len(candidates)} 个候选片段")
        
        # 5. 选择最优组合
        selected_segments = self._select_optimal_segments(candidates)
        print(f"✓ 选择 {len(selected_segments)} 个片段进行拼接")
        
        # 6. 执行剪辑
        if use_gpu and self.gpu.is_available():
            # 尝试 GPU 加速剪辑
            success = self._clip_with_gpu(input_path, output_path, selected_segments)
            if not success:
                print("⚠️ GPU 剪辑失败，回退到 CPU")
                self._clip_with_cpu(input_path, output_path, selected_segments)
        else:
            self._clip_with_cpu(input_path, output_path, selected_segments)
        
        # 7. 生成报告
        report = self._generate_report(input_path, output_path, selected_segments, video_info)
        print(f"✓ 剪辑完成: {output_path}")
        
        # 清理临时文件
        self._cleanup()
        
        return report
    
    def _extract_audio(self, video_path: str) -> str:
        """提取音频为WAV格式用于分析"""
        audio_path = os.path.join(self.temp_dir, "audio.wav")
        cmd = [
            "ffmpeg", "-y", "-i", video_path,
            "-vn", "-acodec", "pcm_s16le",
            "-ar", "44100", "-ac", "2",
            audio_path
        ]
        subprocess.run(cmd, capture_output=True, check=True)
        return audio_path
    
    def _analyze_audio(self, audio_path: str) -> List[BeatInfo]:
        """分析音频，返回节拍信息列表"""
        # 使用librosa进行专业音频分析
        try:
            import librosa
            y, sr = librosa.load(audio_path, sr=None)
            
            # 1. 检测BPM
            onset_env = librosa.onset.onset_strength(y=y, sr=sr)
            tempo = librosa.beat.tempo(onset_envelope=onset_env, sr=sr)[0]
            
            # 确保BPM在合理范围内
            if tempo < self.config.bpm_range[0]:
                tempo *= 2
            elif tempo > self.config.bpm_range[1]:
                tempo /= 2
            
            # 2. 检测节拍位置
            beat_frames = librosa.beat.beat_track(onset_envelope=onset_env, sr=sr)[1]
            beat_times = librosa.frames_to_time(beat_frames, sr=sr)
            
            # 3. 识别强拍（downbeat）- 通常在乐句开始
            # 简单策略：每4拍为一个乐句，第1拍为强拍
            beats = []
            for i, t in enumerate(beat_times):
                is_downbeat = (i % 4 == 0)
                beats.append(BeatInfo(time=float(t), is_downbeat=is_downbeat, bpm=tempo))
            
            return beats
            
        except ImportError:
            # 如果librosa不可用，使用简化版基于能量的检测
            return self._simple_beat_detection(audio_path)
    
    def _simple_beat_detection(self, audio_path: str) -> List[BeatInfo]:
        """简化的节拍检测（基于音频能量）"""
        # 使用ffmpeg获取音频数据
        cmd = [
            "ffmpeg", "-i", audio_path,
            "-f", "f32le", "-ac", "1", "-ar", "22050",
            "-"
        ]
        result = subprocess.run(cmd, capture_output=True)
        audio_data = np.frombuffer(result.stdout, dtype=np.float32)
        
        # 计算能量包络
        hop_size = 512
        frames = np.array([
            np.sum(audio_data[i:i+hop_size]**2)
            for i in range(0, len(audio_data)-hop_size, hop_size)
        ])
        
        # 简单的峰值检测（作为节拍候选）
        peaks = []
        threshold = np.mean(frames) * 1.5
        for i in range(1, len(frames)-1):
            if frames[i] > threshold and frames[i] > frames[i-1] and frames[i] > frames[i+1]:
                time = i * hop_size / 22050
                peaks.append(BeatInfo(time=time, is_downbeat=(len(peaks) % 4 == 0), bpm=120))
        
        return peaks
    
    def _analyze_video(self, video_path: str) -> dict:
        """分析视频信息"""
        # 使用ffprobe获取视频元数据
        cmd = [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_streams", video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        info = json.loads(result.stdout)
        
        video_stream = next(s for s in info["streams"] if s["codec_type"] == "video")
        
        duration = float(video_stream.get("duration", 0))
        if duration == 0:
            # 从格式信息获取
            duration = float(info.get("format", {}).get("duration", 0))
        
        return {
            "duration": duration,
            "width": int(video_stream["width"]),
            "height": int(video_stream["height"]),
            "fps": eval(video_stream.get("r_frame_rate", "30/1")),
            "bitrate": int(video_stream.get("bit_rate", 0))
        }
    
    def _generate_candidates(self, beats: List[BeatInfo], video_info: dict) -> List[VideoSegment]:
        """生成候选片段列表"""
        candidates = []
        duration = video_info["duration"]
        
        # 在强拍位置生成候选起点
        downbeats = [b for b in beats if b.is_downbeat]
        
        # 如果强拍太少，用所有节拍
        if len(downbeats) < 4:
            downbeats = beats[::4]  # 每4拍取一个
        
        # 生成不同长度的候选片段（从强拍到强拍，保证完整性）
        for i, start_beat in enumerate(downbeats[:-1]):
            for j in range(i+1, min(i+16, len(downbeats))):  # 最多4个乐句
                end_beat = downbeats[j]
                seg_duration = end_beat.time - start_beat.time
                
                # 过滤太短的片段
                if seg_duration < self.config.min_segment_duration:
                    continue
                
                # 音乐得分：完整乐句得高分
                phrase_count = j - i
                music_score = min(1.0, phrase_count / 4)  # 4个乐句得满分
                
                # 动作得分：基于在视频中的位置（避免开头结尾的静止）
                mid_time = (start_beat.time + end_beat.time) / 2
                position_score = 1.0 - abs(mid_time - duration/2) / (duration/2)
                motion_score = 0.5 + 0.5 * position_score  # 中间部分得分高
                
                # 综合得分
                total_score = (
                    self.config.audio_weight * music_score +
                    self.config.video_weight * motion_score
                )
                
                candidates.append(VideoSegment(
                    start=start_beat.time,
                    end=end_beat.time,
                    music_score=music_score,
                    motion_score=motion_score,
                    total_score=total_score
                ))
        
        # 按得分排序
        candidates.sort(key=lambda x: x.total_score, reverse=True)
        return candidates
    
    def _select_optimal_segments(self, candidates: List[VideoSegment]) -> List[VideoSegment]:
        """选择最优片段组合，使总时长接近目标"""
        target = self.config.target_duration
        tolerance = self.config.tolerance
        
        # 尝试找到一个片段刚好符合时长
        for seg in candidates:
            if abs((seg.end - seg.start) - target) <= tolerance:
                return [seg]
        
        # 尝试两个片段拼接
        for i, seg1 in enumerate(candidates[:20]):  # 只看前20个
            for seg2 in candidates[i+1:30]:
                total = (seg1.end - seg1.start) + (seg2.end - seg2.start)
                if abs(total - target) <= tolerance:
                    # 检查是否重叠
                    if seg1.end <= seg2.start or seg2.end <= seg1.start:
                        return sorted([seg1, seg2], key=lambda x: x.start)
        
        # 退而求其次：选择一个最接近目标的单个片段
        best_single = min(candidates, key=lambda x: abs((x.end - x.start) - target))
        return [best_single]
    
    def _clip_with_gpu(self, input_path: str, output_path: str, segments: List[VideoSegment]) -> bool:
        """使用 GPU 加速剪辑"""
        if len(segments) == 1:
            seg = segments[0]
            duration = seg.end - seg.start
            return self.gpu.encode_video_gpu(input_path, output_path, seg.start, duration)
        else:
            # 多片段拼接暂不支持 GPU 加速，回退到 CPU
            return False
    
    def _clip_with_cpu(self, input_path: str, output_path: str, segments: List[VideoSegment]):
        """使用 CPU 剪辑"""
        if len(segments) == 1:
            self._cut_single_segment(input_path, output_path, segments[0])
        else:
            self._concat_segments(input_path, output_path, segments)
    
    def _cut_single_segment(self, input_path: str, output_path: str, segment: VideoSegment):
        """单一片段剪辑"""
        duration = segment.end - segment.start
        cmd = [
            "ffmpeg", "-y", "-i", input_path,
            "-ss", str(segment.start),
            "-t", str(duration),
            "-c", "copy",
            output_path
        ]
        subprocess.run(cmd, capture_output=True, check=True)
    
    def _concat_segments(self, input_path: str, output_path: str, segments: List[VideoSegment]):
        """多片段拼接"""
        # 创建concat列表文件
        list_path = os.path.join(self.temp_dir, "concat_list.txt")
        segment_files = []
        
        for i, seg in enumerate(segments):
            seg_path = os.path.join(self.temp_dir, f"segment_{i}.mp4")
            self._cut_single_segment(input_path, seg_path, seg)
            segment_files.append(seg_path)
        
        # 写入concat列表
        with open(list_path, "w") as f:
            for seg_path in segment_files:
                f.write(f"file '{seg_path}'\n")
        
        # 拼接
        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", list_path,
            "-c", "copy",
            output_path
        ]
        subprocess.run(cmd, capture_output=True, check=True)
    
    def _generate_report(self, input_path: str, output_path: str, 
                         segments: List[VideoSegment], video_info: dict) -> dict:
        """生成剪辑报告"""
        total_duration = sum(s.end - s.start for s in segments)
        
        return {
            "input_file": input_path,
            "output_file": output_path,
            "original_duration": video_info["duration"],
            "output_duration": total_duration,
            "target_duration": self.config.target_duration,
            "preset": self.config.preset,
            "gpu_accelerated": self.gpu.is_available(),
            "segments": [
                {
                    "start": f"{s.start:.2f}s",
                    "end": f"{s.end:.2f}s",
                    "duration": f"{s.end - s.start:.2f}s",
                    "music_score": f"{s.music_score:.2f}",
                    "motion_score": f"{s.motion_score:.2f}"
                }
                for s in segments
            ],
            "compression_ratio": f"{video_info['duration'] / total_duration:.1f}x"
        }
    
    def _cleanup(self):
        """清理临时文件"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)


# CLI入口
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="舞蹈视频智能剪辑工具")
    parser.add_argument("input", help="输入视频路径")
    parser.add_argument("-o", "--output", help="输出视频路径", default="output_clip.mp4")
    parser.add_argument("-t", "--target", type=float, default=30.0, help="目标时长（秒）")
    parser.add_argument("--tolerance", type=float, default=2.0, help="时长容差（秒）")
    parser.add_argument("-p", "--preset", help="舞蹈预设类型", 
                       choices=['ballet', 'hip_hop', 'folk', 'modern', 'latin', 'jazz'])
    parser.add_argument("--no-gpu", action="store_true", help="禁用GPU加速")
    parser.add_argument("--list-presets", action="store_true", help="列出所有预设")
    
    args = parser.parse_args()
    
    # 列出预设
    if args.list_presets:
        print("🎭 支持的舞蹈类型：\n")
        for name, desc in PresetManager.list_presets().items():
            preset = get_preset(name)
            print(f"  {preset.name_cn} ({name})")
            print(f"    BPM: {preset.bpm_range[0]}-{preset.bpm_range[1]}")
            print(f"    {preset.description}\n")
        exit(0)
    
    # 创建配置
    config = ClipConfig(
        target_duration=args.target,
        tolerance=args.tolerance,
        preset=args.preset
    )
    
    clipper = DanceClipper(config)
    report = clipper.clip(args.input, args.output, use_gpu=not args.no_gpu)
    
    print("\n📊 剪辑报告:")
    print(json.dumps(report, indent=2, ensure_ascii=False))
