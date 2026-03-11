"""
dance_presets.py
舞蹈类型预设配置

不同舞种有不同的音乐特征和剪辑策略
"""

from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass
class DancePreset:
    """舞蹈类型预设"""
    name: str
    name_cn: str
    description: str
    
    # BPM 特征范围
    bpm_range: Tuple[int, int]
    bpm_typical: int  # 典型 BPM
    
    # 音乐结构
    beats_per_measure: int  # 每小节拍数
    measures_per_phrase: int  # 每乐句小节数
    
    # 剪辑策略权重
    audio_weight: float  # 音乐结构权重
    video_weight: float  # 动作连贯性权重
    
    # 片段时长偏好
    min_segment_duration: float  # 最短片段（秒）
    ideal_segment_duration: float  # 理想片段（秒）
    
    # 特殊规则
    prefer_continuous: bool  # 是否偏好连续片段（不拼接）
    cut_on_motion_peak: bool  # 是否倾向于在动作高潮处剪辑
    avoid_mid_movement: bool  # 是否避免在动作中间切断
    
    # 目标平台建议
    recommended_platforms: Dict[str, Dict]


# ==================== 预设定义 ====================

BALLET_PRESET = DancePreset(
    name="ballet",
    name_cn="芭蕾",
    description="古典芭蕾，重视优雅的动作连贯性和音乐抒情性",
    
    bpm_range=(60, 120),
    bpm_typical=80,
    
    beats_per_measure=4,
    measures_per_phrase=8,  # 芭蕾乐句较长，8小节
    
    audio_weight=0.7,  # 更重视音乐
    video_weight=0.3,
    
    min_segment_duration=8.0,  # 芭蕾需要较长片段展示完整动作
    ideal_segment_duration=16.0,
    
    prefer_continuous=True,  # 芭蕾不适合拼接
    cut_on_motion_peak=False,  # 不在高潮处切断
    avoid_mid_movement=True,  # 绝对不能在跳跃/旋转中间切断
    
    recommended_platforms={
        "tiktok": {"duration": 15, "note": "适合展示单一技巧动作"},
        "xiaohongshu": {"duration": 30, "note": "适合变奏片段"},
        "bilibili": {"duration": 60, "note": "适合完整舞段展示"},
        "teaching": {"duration": 120, "note": "适合教学分解"}
    }
)


HIP_HOP_PRESET = DancePreset(
    name="hip_hop",
    name_cn="街舞",
    description="Hip-hop、Breaking、Popping 等街头舞蹈，节奏感强",
    
    bpm_range=(80, 150),
    bpm_typical=100,
    
    beats_per_measure=4,
    measures_per_phrase=4,  # 街舞乐句较短，4小节
    
    audio_weight=0.5,  # 音乐和动作同等重要
    video_weight=0.5,
    
    min_segment_duration=4.0,
    ideal_segment_duration=8.0,
    
    prefer_continuous=False,  # 可以拼接不同高光时刻
    cut_on_motion_peak=True,  # 可以在炸点（power move）后切断
    avoid_mid_movement=False,  # 街舞动作快，可以适当灵活
    
    recommended_platforms={
        "tiktok": {"duration": 15, "note": "适合展示单个炸点动作"},
        "xiaohongshu": {"duration": 30, "note": "适合 routine 展示"},
        "bilibili": {"duration": 60, "note": "适合 battle 片段"},
        "competition": {"duration": 45, "note": "适合比赛视频"}
    }
)


FOLK_DANCE_PRESET = DancePreset(
    name="folk",
    name_cn="民族舞",
    description="各民族传统舞蹈，节奏多变，重视文化内涵",
    
    bpm_range=(60, 140),
    bpm_typical=90,
    
    beats_per_measure=4,
    measures_per_phrase=4,  # 可变的，取决于具体民族
    
    audio_weight=0.65,
    video_weight=0.35,
    
    min_segment_duration=6.0,
    ideal_segment_duration=12.0,
    
    prefer_continuous=True,
    cut_on_motion_peak=False,
    avoid_mid_movement=True,
    
    recommended_platforms={
        "tiktok": {"duration": 15, "note": "适合展示特色动作"},
        "xiaohongshu": {"duration": 30, "note": "适合服饰+动作展示"},
        "bilibili": {"duration": 60, "note": "适合完整剧目"},
        "cultural": {"duration": 45, "note": "适合文化推广"}
    }
)


MODERN_DANCE_PRESET = DancePreset(
    name="modern",
    name_cn="现代舞",
    description="现代舞/当代舞，情感表达优先，节奏自由",
    
    bpm_range=(40, 120),  # 范围很宽，现代舞可能很慢
    bpm_typical=70,
    
    beats_per_measure=4,
    measures_per_phrase=4,
    
    audio_weight=0.6,
    video_weight=0.4,
    
    min_segment_duration=10.0,  # 现代舞需要长片段表达情感
    ideal_segment_duration=20.0,
    
    prefer_continuous=True,
    cut_on_motion_peak=False,
    avoid_mid_movement=True,
    
    recommended_platforms={
        "tiktok": {"duration": 15, "note": "不太适合，可能过于抽象"},
        "xiaohongshu": {"duration": 30, "note": "适合情感高潮片段"},
        "bilibili": {"duration": 90, "note": "适合完整作品展示"},
        "art": {"duration": 120, "note": "适合艺术欣赏"}
    }
)


LATIN_DANCE_PRESET = DancePreset(
    name="latin",
    name_cn="拉丁舞",
    description="伦巴、恰恰、桑巴等，节奏鲜明，热情奔放",
    
    bpm_range=(100, 180),
    bpm_typical=120,
    
    beats_per_measure=4,
    measures_per_phrase=4,
    
    audio_weight=0.55,
    video_weight=0.45,
    
    min_segment_duration=5.0,
    ideal_segment_duration=10.0,
    
    prefer_continuous=False,
    cut_on_motion_peak=True,
    avoid_mid_movement=False,
    
    recommended_platforms={
        "tiktok": {"duration": 15, "note": "适合展示旋转/造型"},
        "xiaohongshu": {"duration": 30, "note": "适合双人舞展示"},
        "bilibili": {"duration": 60, "note": "适合比赛/表演片段"},
        "competition": {"duration": 90, "note": "适合完整套路"}
    }
)


JAZZ_DANCE_PRESET = DancePreset(
    name="jazz",
    name_cn="爵士舞",
    description="爵士舞，节奏感强，注重身体线条和表现力",
    
    bpm_range=(90, 160),
    bpm_typical=120,
    
    beats_per_measure=4,
    measures_per_phrase=4,
    
    audio_weight=0.5,
    video_weight=0.5,
    
    min_segment_duration=4.0,
    ideal_segment_duration=8.0,
    
    prefer_continuous=False,
    cut_on_motion_peak=True,
    avoid_mid_movement=False,
    
    recommended_platforms={
        "tiktok": {"duration": 15, "note": "适合卡点动作"},
        "xiaohongshu": {"duration": 30, "note": "适合编舞展示"},
        "bilibili": {"duration": 60, "note": "适合完整作品"},
        "cover": {"duration": 30, "note": "适合翻跳视频"}
    }
)


# ==================== 预设管理器 ====================

class PresetManager:
    """预设管理器"""
    
    _presets: Dict[str, DancePreset] = {
        "ballet": BALLET_PRESET,
        "hip_hop": HIP_HOP_PRESET,
        "folk": FOLK_DANCE_PRESET,
        "modern": MODERN_DANCE_PRESET,
        "latin": LATIN_DANCE_PRESET,
        "jazz": JAZZ_DANCE_PRESET,
    }
    
    @classmethod
    def get_preset(cls, name: str) -> DancePreset:
        """获取预设"""
        if name not in cls._presets:
            raise ValueError(f"未知舞蹈类型: {name}。可用: {list(cls._presets.keys())}")
        return cls._presets[name]
    
    @classmethod
    def list_presets(cls) -> Dict[str, str]:
        """列出所有预设"""
        return {
            name: f"{preset.name_cn} - {preset.description}"
            for name, preset in cls._presets.items()
        }
    
    @classmethod
    def get_preset_names(cls) -> list:
        """获取预设名称列表"""
        return list(cls._presets.keys())
    
    @classmethod
    def apply_preset_to_config(cls, config: dict, preset_name: str) -> dict:
        """将预设应用到配置"""
        preset = cls.get_preset(preset_name)
        
        # 更新配置
        config['bpm_range'] = preset.bpm_range
        config['beats_per_measure'] = preset.beats_per_measure
        config['measures_per_phrase'] = preset.measures_per_phrase
        config['audio']['weight'] = preset.audio_weight
        config['video']['weight'] = preset.video_weight
        config['min_segment_duration'] = preset.min_segment_duration
        
        # 添加预设信息
        config['dance_type'] = preset.name
        config['dance_type_cn'] = preset.name_cn
        
        return config
    
    @classmethod
    def auto_detect_preset(cls, bpm: float) -> str:
        """
        根据BPM自动检测可能的舞蹈类型
        返回最匹配的预设名称
        """
        scores = {}
        
        for name, preset in cls._presets.items():
            min_bpm, max_bpm = preset.bpm_range
            typical = preset.bpm_typical
            
            # 计算匹配分数
            if min_bpm <= bpm <= max_bpm:
                # BPM在范围内，根据与典型值的接近程度打分
                distance = abs(bpm - typical)
                scores[name] = 1.0 - (distance / (max_bpm - min_bpm))
            else:
                # BPM不在范围内，给低分
                if bpm < min_bpm:
                    scores[name] = 0.1 * (bpm / min_bpm)
                else:
                    scores[name] = 0.1 * (max_bpm / bpm)
        
        # 返回得分最高的
        if scores:
            return max(scores, key=scores.get)
        return "ballet"  # 默认返回芭蕾


# 便捷函数
def get_preset(name: str) -> DancePreset:
    """获取舞蹈预设"""
    return PresetManager.get_preset(name)


def list_dance_types() -> Dict[str, str]:
    """列出所有舞蹈类型"""
    return PresetManager.list_presets()


def auto_detect_dance_type(bpm: float) -> str:
    """自动检测舞蹈类型"""
    return PresetManager.auto_detect_preset(bpm)


if __name__ == "__main__":
    # 测试
    print("🩰 支持的舞蹈类型：\n")
    
    for name, desc in list_dance_types().items():
        preset = get_preset(name)
        print(f"{preset.name_cn} ({name})")
        print(f"  BPM: {preset.bpm_range[0]}-{preset.bpm_range[1]} (典型{preset.bpm_typical})")
        print(f"  描述: {preset.description}")
        print(f"  推荐时长: {preset.ideal_segment_duration}s")
        print()
    
    # 测试自动检测
    print("🎵 BPM自动检测测试：")
    test_bpms = [70, 100, 130, 150]
    for bpm in test_bpms:
        detected = auto_detect_dance_type(bpm)
        preset = get_preset(detected)
        print(f"  BPM {bpm} → {preset.name_cn} ({detected})")
