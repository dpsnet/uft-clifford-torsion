"""
video_analyzer.py
视频动作分析模块

检测舞蹈视频中的动作密度、场景切换和视觉特征
用于辅助选择最佳的剪辑片段
"""

import numpy as np
import subprocess
import json
from typing import List, Tuple, Optional
from dataclasses import dataclass
from pathlib import Path


@dataclass
class MotionInfo:
    """动作信息"""
    start_time: float
    end_time: float
    intensity: float  # 动作强度 0-1
    motion_score: float  # 综合动作得分


@dataclass
class SceneChange:
    """场景切换信息"""
    time: float
    confidence: float  # 切换置信度
    type: str  # 'cut', 'fade', 'dissolve'


@dataclass
class VideoAnalysis:
    """完整视频分析结果"""
    duration: float
    width: int
    height: int
    fps: float
    motion_segments: List[MotionInfo]
    scene_changes: List[SceneChange]
    keyframes: List[float]  # 关键帧时间点


class VideoAnalyzer:
    """舞蹈视频分析器"""
    
    def __init__(self, sample_rate: int = 2):
        """
        Args:
            sample_rate: 每秒采样多少帧进行分析
        """
        self.sample_rate = sample_rate
        
    def analyze(self, video_path: str) -> VideoAnalysis:
        """
        完整分析视频
        """
        print(f"📹 分析视频: {video_path}")
        
        # 1. 获取视频元数据
        metadata = self._get_metadata(video_path)
        
        # 2. 检测场景切换
        scene_changes = self._detect_scene_changes(video_path)
        print(f"  ✓ 检测到 {len(scene_changes)} 个场景切换")
        
        # 3. 分析动作密度
        motion_segments = self._analyze_motion(video_path, metadata)
        print(f"  ✓ 分析完成，{len(motion_segments)} 个动作段落")
        
        # 4. 提取关键帧
        keyframes = self._extract_keyframes(video_path, metadata)
        print(f"  ✓ 提取 {len(keyframes)} 个关键帧")
        
        return VideoAnalysis(
            duration=metadata['duration'],
            width=metadata['width'],
            height=metadata['height'],
            fps=metadata['fps'],
            motion_segments=motion_segments,
            scene_changes=scene_changes,
            keyframes=keyframes
        )
    
    def _get_metadata(self, video_path: str) -> dict:
        """获取视频元数据"""
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json',
            '-show_streams', video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        data = json.loads(result.stdout)
        
        video_stream = next(s for s in data['streams'] if s['codec_type'] == 'video')
        
        duration = float(video_stream.get('duration', 0))
        if duration == 0:
            duration = float(data.get('format', {}).get('duration', 0))
        
        fps_str = video_stream.get('r_frame_rate', '30/1')
        fps = eval(fps_str)
        
        return {
            'duration': duration,
            'width': int(video_stream['width']),
            'height': int(video_stream['height']),
            'fps': fps,
            'total_frames': int(duration * fps)
        }
    
    def _detect_scene_changes(self, video_path: str, threshold: float = 0.3) -> List[SceneChange]:
        """
        使用FFmpeg的scene detection检测场景切换
        """
        cmd = [
            'ffmpeg', '-i', video_path,
            '-filter:v', f'select=gt(scene\\,{threshold})',
            '-show_entries', 'frame=pts_time',
            '-of', 'csv=p=0',
            '-f', 'null', '-'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        scene_changes = []
        
        for line in result.stderr.split('\n'):
            if 'pts_time:' in line:
                try:
                    time_str = line.split('pts_time:')[1].split()[0]
                    time = float(time_str)
                    scene_changes.append(SceneChange(
                        time=time,
                        confidence=0.7,
                        type='cut'
                    ))
                except (IndexError, ValueError):
                    continue
        
        return scene_changes
    
    def _analyze_motion(self, video_path: str, metadata: dict) -> List[MotionInfo]:
        """
        分析视频动作密度
        
        策略：
        1. 抽取帧
        2. 计算帧间光流或像素差异
        3. 识别高动作段落
        """
        duration = metadata['duration']
        fps = metadata['fps']
        
        # 使用FFmpeg的showinfo filter获取帧间差异信息
        # 这里使用简化的方法：基于帧间差分
        
        # 抽取部分帧用于分析
        sample_interval = max(1, int(fps / self.sample_rate))
        
        motion_scores = []
        timestamps = []
        
        # 使用FFmpeg提取帧并计算差分
        temp_dir = Path('/tmp/dance_motion_analysis')
        temp_dir.mkdir(exist_ok=True)
        
        # 提取灰度帧序列
        cmd = [
            'ffmpeg', '-i', video_path,
            '-vf', f'fps={self.sample_rate},format=gray',
            '-frames:v', str(int(duration * self.sample_rate)),
            str(temp_dir / 'frame_%04d.png')
        ]
        subprocess.run(cmd, capture_output=True)
        
        # 读取帧并计算动作
        try:
            from PIL import Image
            
            frames = sorted(temp_dir.glob('frame_*.png'))
            if len(frames) > 1:
                prev_frame = np.array(Image.open(frames[0]).convert('L'))
                
                for i, frame_path in enumerate(frames[1:], 1):
                    curr_frame = np.array(Image.open(frame_path).convert('L'))
                    
                    # 计算帧间差分（动作强度）
                    diff = np.abs(curr_frame.astype(float) - prev_frame.astype(float))
                    motion_score = np.mean(diff) / 255.0
                    
                    timestamp = i / self.sample_rate
                    motion_scores.append(motion_score)
                    timestamps.append(timestamp)
                    
                    prev_frame = curr_frame
                    
                    # 清理帧文件
                    frame_path.unlink()
                
                frames[0].unlink()
        
        except ImportError:
            # 如果没有PIL，使用简化方法
            # 基于场景切换密度推断动作
            timestamps = np.linspace(0, duration, int(duration * self.sample_rate))
            motion_scores = [0.5] * len(timestamps)  # 默认中等动作
        
        temp_dir.rmdir()
        
        # 分段聚类，识别动作段落
        return self._segment_motion(timestamps, motion_scores)
    
    def _segment_motion(self, timestamps: List[float], 
                       motion_scores: List[float],
                       window_size: float = 2.0) -> List[MotionInfo]:
        """
        将动作分数聚类成段落
        """
        if not timestamps:
            return []
        
        segments = []
        duration = timestamps[-1]
        
        # 滑动窗口
        window_start = 0
        while window_start < duration:
            window_end = min(window_start + window_size, duration)
            
            # 收集窗口内的动作分数
            window_scores = [
                score for t, score in zip(timestamps, motion_scores)
                if window_start <= t < window_end
            ]
            
            if window_scores:
                avg_intensity = np.mean(window_scores)
                max_intensity = np.max(window_scores)
                # 综合得分：平均强度 + 峰值强度
                score = (avg_intensity + max_intensity) / 2
                
                segments.append(MotionInfo(
                    start_time=window_start,
                    end_time=window_end,
                    intensity=avg_intensity,
                    motion_score=score
                ))
            
            window_start += window_size / 2  # 50%重叠
        
        return segments
    
    def _extract_keyframes(self, video_path: str, metadata: dict, 
                          num_keyframes: int = 10) -> List[float]:
        """
        提取代表性关键帧
        """
        duration = metadata['duration']
        
        # 均匀采样 + 场景切换点
        uniform_times = np.linspace(0, duration, num_keyframes)
        
        # 获取场景切换时间
        scene_times = [sc.time for sc in self._detect_scene_changes(video_path)]
        
        # 合并并去重
        all_times = sorted(set(list(uniform_times) + scene_times))
        
        return [float(t) for t in all_times[:num_keyframes + len(scene_times)]]
    
    def get_motion_score(self, analysis: VideoAnalysis, 
                        start_time: float, end_time: float) -> float:
        """
        计算指定时间段的动作得分
        """
        # 收集该时间段内的所有动作分数
        scores = []
        for seg in analysis.motion_segments:
            # 计算与查询区间的重叠
            overlap_start = max(seg.start_time, start_time)
            overlap_end = min(seg.end_time, end_time)
            
            if overlap_end > overlap_start:
                overlap_ratio = (overlap_end - overlap_start) / (end_time - start_time)
                scores.append(seg.motion_score * overlap_ratio)
        
        if not scores:
            return 0.5  # 默认中等得分
        
        return np.mean(scores)
    
    def check_scene_cut(self, analysis: VideoAnalysis, 
                       start_time: float, end_time: float) -> bool:
        """
        检查时间段内是否有场景切换
        返回True表示有切换（可能不适合剪辑）
        """
        for sc in analysis.scene_changes:
            if start_time < sc.time < end_time:
                return True
        return False
    
    def find_best_segments(self, analysis: VideoAnalysis,
                          target_duration: float,
                          min_segment_duration: float = 3.0) -> List[Tuple[float, float, float]]:
        """
        找出动作得分最高的候选片段
        
        Returns:
            List of (start, end, motion_score)
        """
        candidates = []
        duration = analysis.duration
        
        # 滑动窗口搜索
        window_size = target_duration
        step = 1.0
        
        current = 0
        while current + window_size <= duration:
            start = current
            end = current + window_size
            
            # 检查场景切换
            if self.check_scene_cut(analysis, start, end):
                current += step
                continue
            
            # 计算动作得分
            score = self.get_motion_score(analysis, start, end)
            
            candidates.append((start, end, score))
            current += step
        
        # 按得分排序
        candidates.sort(key=lambda x: x[2], reverse=True)
        
        return candidates


# 独立测试
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python video_analyzer.py <video_file>")
        sys.exit(1)
    
    video_file = sys.argv[1]
    
    analyzer = VideoAnalyzer()
    analysis = analyzer.analyze(video_file)
    
    print(f"\n📹 视频分析结果:")
    print(f"  分辨率: {analysis.width}x{analysis.height}")
    print(f"  时长: {analysis.duration:.2f}s")
    print(f"  帧率: {analysis.fps:.1f}fps")
    print(f"  场景切换: {len(analysis.scene_changes)}次")
    
    print(f"\n🎬 场景切换点:")
    for sc in analysis.scene_changes[:5]:
        print(f"  {sc.time:.2f}s (置信度: {sc.confidence:.2f})")
    
    print(f"\n💃 高动作段落 (Top 5):")
    top_motion = sorted(analysis.motion_segments, 
                       key=lambda x: x.motion_score, reverse=True)[:5]
    for seg in top_motion:
        print(f"  {seg.start_time:.1f}s - {seg.end_time:.1f}s "
              f"(强度: {seg.intensity:.3f}, 得分: {seg.motion_score:.3f})")
    
    print(f"\n✂️  推荐剪辑点 (30秒片段):")
    best_segments = analyzer.find_best_segments(analysis, target_duration=30)
    for i, (start, end, score) in enumerate(best_segments[:3], 1):
        print(f"  {i}. {start:.1f}s - {end:.1f}s (动作得分: {score:.3f})")
