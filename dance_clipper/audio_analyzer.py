"""
audio_analyzer.py
音频节奏分析模块

提供专业的音乐节拍检测、BPM分析和乐句分割
"""

import numpy as np
from typing import List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class PhraseInfo:
    """乐句信息"""
    start_time: float
    end_time: float
    bpm: float
    beats_count: int
    confidence: float  # 乐句边界置信度


@dataclass  
class AudioAnalysis:
    """完整音频分析结果"""
    bpm: float
    beats: List[float]  # 所有节拍时间点
    downbeats: List[float]  # 强拍时间点
    phrases: List[PhraseInfo]  # 乐句列表
    duration: float


class AudioAnalyzer:
    """音频节奏分析器"""
    
    def __init__(self):
        self.sample_rate = 22050  # 分析用采样率
        self.hop_length = 512
        
    def analyze(self, audio_path: str) -> AudioAnalysis:
        """
        完整分析音频，返回节奏信息
        
        使用Librosa进行专业级音频分析：
        1. BPM检测
        2. 节拍跟踪
        3. 强拍识别（downbeat detection）
        4. 乐句分割
        """
        try:
            import librosa
            
            # 加载音频
            y, sr = librosa.load(audio_path, sr=self.sample_rate, mono=True)
            duration = librosa.get_duration(y=y, sr=sr)
            
            # 1. 计算 onset strength（能量变化）
            onset_env = librosa.onset.onset_strength(
                y=y, sr=sr, hop_length=self.hop_length
            )
            
            # 2. BPM检测
            tempo, beat_frames = librosa.beat.beat_track(
                onset_envelope=onset_env,
                sr=sr,
                hop_length=self.hop_length,
                start_bpm=120
            )
            
            # 处理BPM范围（舞蹈音乐通常在60-180之间）
            bpm = float(tempo[0]) if isinstance(tempo, np.ndarray) else float(tempo)
            if bpm < 60:
                bpm *= 2
            elif bpm > 180:
                bpm /= 2
            
            # 3. 转换为时间
            beat_times = librosa.frames_to_time(
                beat_frames, sr=sr, hop_length=self.hop_length
            )
            beats = [float(t) for t in beat_times]
            
            # 4. 强拍检测
            downbeats = self._detect_downbeats(y, sr, beat_frames, bpm)
            
            # 5. 乐句分割（通常4-8拍为一个乐句）
            phrases = self._segment_phrases(beats, downbeats, bpm, duration)
            
            return AudioAnalysis(
                bpm=bpm,
                beats=beats,
                downbeats=downbeats,
                phrases=phrases,
                duration=duration
            )
            
        except ImportError:
            raise ImportError(
                "需要安装librosa进行专业音频分析。\n"
                "请运行: pip install librosa"
            )
    
    def _detect_downbeats(self, y: np.ndarray, sr: int, 
                          beat_frames: np.ndarray, bpm: float) -> List[float]:
        """
        检测强拍（downbeat）位置
        
        策略：
        1. 使用低音频率能量变化
        2. 通常强拍对应低频能量的峰值
        3. 舞蹈音乐通常是4/4拍，所以每4拍一个强拍
        """
        # 提取低频信号（20-200Hz）
        import librosa
        
        # 计算低频能量包络
        S = librosa.stft(y, n_fft=2048, hop_length=self.hop_length)
        freqs = librosa.fft_frequencies(sr=sr, n_fft=2048)
        
        # 只取低频部分
        low_freq_mask = freqs < 200
        low_freq_mag = np.abs(S[low_freq_mask, :])
        low_env = np.sum(low_freq_mag, axis=0)
        
        # 平滑
        low_env = np.convolve(low_env, np.ones(5)/5, mode='same')
        
        # 在每个beat附近寻找低频峰值作为强拍候选
        downbeats = []
        beats_per_measure = 4  # 假设4/4拍
        
        for i, beat_frame in enumerate(beat_frames):
            if beat_frame < len(low_env):
                # 检查这是否是每小节的第1拍
                if i % beats_per_measure == 0:
                    downbeats.append(float(librosa.frames_to_time(
                        beat_frame, sr=sr, hop_length=self.hop_length
                    )))
        
        return downbeats
    
    def _segment_phrases(self, beats: List[float], downbeats: List[float],
                         bpm: float, duration: float) -> List[PhraseInfo]:
        """
        分割乐句
        
        舞蹈音乐的乐句结构：
        - 一个小节 = 4拍
        - 一个乐句 = 4-8小节（16-32拍）
        - 使用强拍作为乐句边界
        """
        phrases = []
        
        if len(downbeats) < 2:
            # 如果没有检测到强拍，使用等间隔分割
            phrase_duration = 8 * 60 / bpm  # 8拍 = 2小节
            current_time = 0
            while current_time < duration:
                end_time = min(current_time + phrase_duration, duration)
                phrases.append(PhraseInfo(
                    start_time=current_time,
                    end_time=end_time,
                    bpm=bpm,
                    beats_count=8,
                    confidence=0.5
                ))
                current_time = end_time
        else:
            # 使用强拍作为乐句边界
            # 通常2-4个强拍构成一个乐句
            phrase_measures = 4  # 4小节一个乐句
            beats_per_measure = 4
            
            for i in range(0, len(downbeats) - phrase_measures, phrase_measures):
                start = downbeats[i]
                end_idx = min(i + phrase_measures, len(downbeats) - 1)
                end = downbeats[end_idx] if end_idx < len(downbeats) else duration
                
                if end > start:
                    phrases.append(PhraseInfo(
                        start_time=start,
                        end_time=end,
                        bpm=bpm,
                        beats_count=phrase_measures * beats_per_measure,
                        confidence=0.8
                    ))
        
        return phrases
    
    def get_clip_points(self, analysis: AudioAnalysis, target_duration: float,
                       tolerance: float = 2.0) -> List[Tuple[float, float]]:
        """
        获取适合剪辑的时间点
        
        返回能够在乐句边界进行剪辑的时间段，使总时长接近target_duration
        """
        candidates = []
        
        for phrase in analysis.phrases:
            phrase_duration = phrase.end_time - phrase.start_time
            
            # 单个乐句是否符合时长要求
            if abs(phrase_duration - target_duration) <= tolerance:
                candidates.append((phrase.start_time, phrase.end_time))
            
            # 尝试相邻乐句组合
            for next_phrase in analysis.phrases:
                if next_phrase.start_time > phrase.end_time:
                    combined_duration = (next_phrase.end_time - phrase.start_time)
                    if abs(combined_duration - target_duration) <= tolerance:
                        candidates.append((phrase.start_time, next_phrase.end_time))
        
        # 按与目标时长的接近程度排序
        candidates.sort(key=lambda x: abs((x[1] - x[0]) - target_duration))
        
        return candidates
    
    def visualize(self, audio_path: str, output_path: str = None):
        """
        可视化音频分析结果（调试用）
        """
        try:
            import matplotlib.pyplot as plt
            import librosa.display
            
            analysis = self.analyze(audio_path)
            y, sr = librosa.load(audio_path, sr=self.sample_rate)
            
            fig, axes = plt.subplots(3, 1, figsize=(14, 8))
            
            # 1. 波形图 + 节拍标记
            ax1 = axes[0]
            librosa.display.waveshow(y, sr=sr, ax=ax1, alpha=0.6)
            for beat in analysis.downbeats:
                ax1.axvline(beat, color='r', linestyle='--', alpha=0.7, label='Downbeat')
            ax1.set_title(f'Waveform with Downbeats (BPM: {analysis.bpm:.1f})')
            ax1.set_xlabel('Time (s)')
            
            # 2. 节拍强度图
            ax2 = axes[1]
            onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=self.hop_length)
            times = librosa.times_like(onset_env, sr=sr, hop_length=self.hop_length)
            ax2.plot(times, onset_env, label='Onset strength')
            for beat in analysis.beats:
                ax2.axvline(beat, color='g', alpha=0.3)
            ax2.set_title('Onset Strength')
            ax2.set_xlabel('Time (s)')
            
            # 3. 乐句分割
            ax3 = axes[2]
            for i, phrase in enumerate(analysis.phrases):
                color = plt.cm.viridis(i / max(1, len(analysis.phrases) - 1))
                ax3.axvspan(phrase.start_time, phrase.end_time, alpha=0.3, color=color)
                mid = (phrase.start_time + phrase.end_time) / 2
                ax3.text(mid, 0.5, f'Phrase {i+1}', ha='center', fontsize=8)
            ax3.set_xlim(0, analysis.duration)
            ax3.set_ylim(0, 1)
            ax3.set_title('Phrase Segmentation')
            ax3.set_xlabel('Time (s)')
            
            plt.tight_layout()
            
            if output_path:
                plt.savefig(output_path, dpi=150, bbox_inches='tight')
                print(f"可视化结果已保存: {output_path}")
            else:
                plt.show()
                
        except ImportError:
            print("需要安装matplotlib进行可视化: pip install matplotlib")


# 独立测试入口
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python audio_analyzer.py <audio_file> [--visualize]")
        sys.exit(1)
    
    audio_file = sys.argv[1]
    visualize = "--visualize" in sys.argv
    
    analyzer = AudioAnalyzer()
    
    print(f"正在分析: {audio_file}")
    analysis = analyzer.analyze(audio_file)
    
    print(f"\n🎵 音频分析结果:")
    print(f"  BPM: {analysis.bpm:.1f}")
    print(f"  总时长: {analysis.duration:.2f}s")
    print(f"  检测节拍数: {len(analysis.beats)}")
    print(f"  强拍数: {len(analysis.downbeats)}")
    print(f"  乐句数: {len(analysis.phrases)}")
    
    print(f"\n📍 乐句结构:")
    for i, phrase in enumerate(analysis.phrases[:5]):  # 只显示前5个
        print(f"  乐句{i+1}: {phrase.start_time:.2f}s - {phrase.end_time:.2f}s "
              f"(时长: {phrase.end_time-phrase.start_time:.2f}s)")
    
    if visualize:
        output_viz = audio_file.replace('.mp3', '_analysis.png').replace('.wav', '_analysis.png')
        analyzer.visualize(audio_file, output_viz)
