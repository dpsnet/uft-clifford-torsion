#!/usr/bin/env python3
"""
example.py - 使用示例
展示如何使用舞蹈视频智能剪辑系统的各种功能
"""

import sys
from dance_clipper import DanceClipper, ClipConfig


def example_1_basic():
    """示例1: 基本使用"""
    print("=== 示例1: 基本剪辑 ===")
    
    config = ClipConfig(target_duration=30.0)
    clipper = DanceClipper(config)
    
    # report = clipper.clip("your_dance_video.mp4", "output.mp4")
    # print(report)
    
    print("代码: clipper.clip('input.mp4', 'output.mp4')")
    print()


def example_2_custom_config():
    """示例2: 自定义配置"""
    print("=== 示例2: 自定义配置 ===")
    
    config = ClipConfig(
        target_duration=15.0,      # 15秒短视频
        tolerance=1.0,             # 误差±1秒
        min_segment_duration=3.0,  # 每段至少3秒
        max_segments=1,            # 不拼接，单一片段
        audio_weight=0.7,          # 更重视音乐结构
        video_weight=0.3           # 动作连贯性次要
    )
    
    clipper = DanceClipper(config)
    print(f"配置: 目标{config.target_duration}s, 音乐权重{config.audio_weight}")
    print()


def example_3_analyze_only():
    """示例3: 仅分析，不剪辑"""
    print("=== 示例3: 仅分析音频 ===")
    
    from audio_analyzer import AudioAnalyzer
    
    analyzer = AudioAnalyzer()
    # analysis = analyzer.analyze("audio.wav")
    
    print("代码:")
    print("  from audio_analyzer import AudioAnalyzer")
    print("  analyzer = AudioAnalyzer()")
    print("  analysis = analyzer.analyze('audio.wav')")
    print("  print(f'BPM: {analysis.bpm}')")
    print("  print(f'乐句数: {len(analysis.phrases)}')")
    print()


def example_4_find_best_segments():
    """示例4: 查找最佳片段"""
    print("=== 示例4: 查找最佳片段 ===")
    
    from video_analyzer import VideoAnalyzer
    
    analyzer = VideoAnalyzer()
    # analysis = analyzer.analyze("video.mp4")
    # segments = analyzer.find_best_segments(analysis, target_duration=30)
    
    print("代码:")
    print("  from video_analyzer import VideoAnalyzer")
    print("  analyzer = VideoAnalyzer()")
    print("  analysis = analyzer.analyze('video.mp4')")
    print("  segments = analyzer.find_best_segments(analysis, 30)")
    print("  for start, end, score in segments[:3]:")
    print("      print(f'{start:.1f}s - {end:.1f}s, 得分: {score:.3f}')")
    print()


def example_5_batch_process():
    """示例5: 批量处理"""
    print("=== 示例5: 批量处理 ===")
    print("使用提供的 shell 脚本:")
    print("  ./batch_clip.sh ./raw_videos 30 ./output_clips")
    print()
    print("或在Python中:")
    print("""
    import os
    from dance_clipper import DanceClipper, ClipConfig
    
    config = ClipConfig(target_duration=30.0)
    clipper = DanceClipper(config)
    
    for video in os.listdir('./raw_videos'):
        if video.endswith('.mp4'):
            input_path = f'./raw_videos/{video}'
            output_path = f'./output_clips/{video[:-4]}_clip.mp4'
            clipper.clip(input_path, output_path)
    """)
    print()


def main():
    print("🎬 舞蹈视频智能剪辑系统 - 使用示例\n")
    print("=" * 50)
    print()
    
    example_1_basic()
    example_2_custom_config()
    example_3_analyze_only()
    example_4_find_best_segments()
    example_5_batch_process()
    
    print("=" * 50)
    print("\n📖 详细文档请查看 README.md")
    print("🔧 完整命令行参数请运行: python dance_clipper.py --help")


if __name__ == "__main__":
    main()
