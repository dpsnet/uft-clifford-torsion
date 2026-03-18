"""
TNN小鼠听觉系统
模拟耳蜗、耳蜗核、上橄榄和下丘处理
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Dict


class Cochlea(nn.Module):
    """
    耳蜗模型
    功能: 频谱分析、频率选择
    小鼠听觉范围: 约1-100kHz (但对超声特别敏感)
    """
    
    def __init__(self, 
                 n_frequency_bands: int = 64,
                 sample_rate: int = 16000,
                 n_fft: int = 512):
        super().__init__()
        self.n_frequency_bands = n_frequency_bands
        self.sample_rate = sample_rate
        self.n_fft = n_fft
        
        # 频率选择权重 (模拟基底膜调谐)
        # 小鼠对30-100kHz超声特别敏感
        self.frequency_tuning = nn.Parameter(
            self._create_frequency_tuning(n_frequency_bands)
        )
        
        # 动态范围压缩 (模拟外毛细胞放大)
        self.compression_threshold = nn.Parameter(torch.tensor(0.1))
        self.compression_ratio = nn.Parameter(torch.tensor(0.5))
        
    def _create_frequency_tuning(self, n_bands: int) -> torch.Tensor:
        """创建频率调谐曲线 (对数分布)"""
        # 对数频率分布 (更关注高频/超声)
        freqs = torch.logspace(np.log10(1000), np.log10(80000), n_bands)
        
        # 归一化
        weights = freqs / freqs.max()
        return weights
    
    def forward(self, spectrogram: torch.Tensor) -> torch.Tensor:
        """
        Args:
            spectrogram: [B, T, F] 时频谱 (log mel spectrogram)
        Returns:
            cochlear_output: [B, T, n_bands] 耳蜗输出
        """
        # 应用频率调谐
        tuned = spectrogram * self.frequency_tuning.view(1, 1, -1)
        
        # 动态范围压缩
        mask = (tuned > self.compression_threshold).float()
        compressed = tuned * (1 - mask) + \
                     (self.compression_threshold + 
                      (tuned - self.compression_threshold) * self.compression_ratio) * mask
        
        # 时间整合 (模拟内毛细胞的时间常数)
        # 简单的指数移动平均
        alpha = 0.9
        integrated = torch.zeros_like(compressed)
        integrated[:, 0, :] = compressed[:, 0, :]
        
        for t in range(1, compressed.size(1)):
            integrated[:, t, :] = alpha * integrated[:, t-1, :] + (1 - alpha) * compressed[:, t, :]
        
        return F.relu(integrated)


class CochlearNucleus(nn.Module):
    """
    耳蜗核 - 音调和时间处理
    功能: 起始检测、包络提取、精细时间结构
    """
    
    def __init__(self, n_bands: int = 64):
        super().__init__()
        
        # 起始检测 (onset detection)
        self.onset_detector = nn.Conv1d(n_bands, n_bands, kernel_size=3, padding=1)
        
        # 包络提取
        self.envelope_extractor = nn.Sequential(
            nn.Conv1d(n_bands, n_bands, kernel_size=5, padding=2),
            nn.ReLU(),
            nn.MaxPool1d(kernel_size=4, stride=4)  # 下采样
        )
        
    def forward(self, cochlear_input: torch.Tensor) -> Dict[str, torch.Tensor]:
        """
        Args:
            cochlear_input: [B, T, n_bands]
        Returns:
            包含起始响应和包络的字典
        """
        # 转置为 [B, n_bands, T] 用于Conv1d
        x = cochlear_input.transpose(1, 2)
        
        # 起始检测
        onset = F.relu(self.onset_detector(x))
        
        # 包络提取
        envelope = self.envelope_extractor(x)
        
        return {
            'onset': onset.transpose(1, 2),  # [B, T, n_bands]
            'envelope': envelope.transpose(1, 2),  # [B, T//4, n_bands]
            'output': onset.transpose(1, 2)
        }


class SuperiorOlivaryComplex(nn.Module):
    """
    上橄榄复合体 - 双耳处理
    功能: 声音定位 (ITD和ILD)
    """
    
    def __init__(self, n_bands: int = 64, n_azimuths: int = 36):
        super().__init__()
        self.n_bands = n_bands
        self.n_azimuths = n_azimuths
        
        # ITD (Interaural Time Difference) 处理
        self.itd_tuning = nn.Linear(n_bands * 2, n_bands)
        
        # ILD (Interaural Level Difference) 处理
        self.ild_tuning = nn.Linear(n_bands * 2, n_bands)
        
        # 声源定位输出
        self.azimuth_estimation = nn.Sequential(
            nn.Linear(n_bands * 2, 128),
            nn.ReLU(),
            nn.Linear(128, n_azimuths)  # 36个方位角 (-180到+180度)
        )
        
    def forward(self, left_ear: torch.Tensor, right_ear: torch.Tensor) -> Dict[str, torch.Tensor]:
        """
        Args:
            left_ear: [B, T, n_bands]
            right_ear: [B, T, n_bands]
        Returns:
            包含定位信息的字典
        """
        # 合并双耳输入
        binaural = torch.cat([left_ear, right_ear], dim=-1)  # [B, T, n_bands*2]
        
        # ITD和ILD特征
        itd_features = F.relu(self.itd_tuning(binaural))
        ild_features = F.relu(self.ild_tuning(binaural))
        
        # 方位角估计
        azimuth_logits = self.azimuth_estimation(binaural)  # [B, T, n_azimuths]
        
        # 时间平均以获得稳定估计
        azimuth_distribution = F.softmax(azimuth_logits.mean(dim=1), dim=-1)  # [B, n_azimuths]
        
        return {
            'itd_features': itd_features,
            'ild_features': ild_features,
            'azimuth_logits': azimuth_logits,
            'azimuth_distribution': azimuth_distribution,
            'output': torch.cat([itd_features, ild_features], dim=-1)
        }


class InferiorColliculus(nn.Module):
    """
    下丘 - 听觉整合中心
    功能: 多模态整合、声音分类、惊吓反应通路
    """
    
    def __init__(self, input_dim: int = 128, output_dim: int = 256):
        super().__init__()
        
        self.feature_integration = nn.Sequential(
            nn.Linear(input_dim, 256),
            nn.LayerNorm(256),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(256, output_dim),
            nn.LayerNorm(output_dim),
            nn.ReLU()
        )
        
        # 声音类型分类 (同类叫声、捕食者声音、环境声)
        self.sound_classifier = nn.Linear(output_dim, 8)
        
        # 惊吓反应评估 (对突发大声)
        self.startle_assessment = nn.Linear(output_dim, 1)
        
    def forward(self, auditory_features: torch.Tensor) -> Dict[str, torch.Tensor]:
        """
        Args:
            auditory_features: [B, T, input_dim]
        Returns:
            整合后的听觉表征
        """
        # 时间平均整合
        integrated = auditory_features.mean(dim=1)  # [B, input_dim]
        
        # 特征整合
        output = self.feature_integration(integrated)
        
        # 分类
        sound_type = self.sound_classifier(output)
        
        # 惊吓评估
        startle_prob = torch.sigmoid(self.startle_assessment(output))
        
        return {
            'integrated': output,
            'sound_type_logits': sound_type,
            'sound_type_prob': F.softmax(sound_type, dim=-1),
            'startle_prob': startle_prob,
            'output': output
        }


class MouseAuditorySystem(nn.Module):
    """
    小鼠完整听觉系统
    
    通路:
    声音 -> 耳蜗 -> 耳蜗核 -> 上橄榄 -> 下丘
    """
    
    def __init__(self,
                 n_frequency_bands: int = 64,
                 output_dim: int = 256,
                 use_binaural: bool = True):
        super().__init__()
        
        self.use_binaural = use_binaural
        
        # 单耳处理
        self.cochlea = Cochlea(n_frequency_bands)
        self.cochlear_nucleus = CochlearNucleus(n_frequency_bands)
        
        if use_binaural:
            # 双耳处理 (用于声音定位)
            self.superior_olivary = SuperiorOlivaryComplex(n_frequency_bands)
            ic_input_dim = n_frequency_bands * 2
        else:
            ic_input_dim = n_frequency_bands
        
        self.inferior_colliculus = InferiorColliculus(ic_input_dim, output_dim)
        
        self.output_dim = output_dim
        
    def forward(self, 
                spectrogram: torch.Tensor,
                spectrogram_right: torch.Tensor = None) -> Dict[str, torch.Tensor]:
        """
        Args:
            spectrogram: [B, T, F] 左耳时频谱
            spectrogram_right: [B, T, F] 右耳时频谱 (可选)
        Returns:
            听觉特征字典
        """
        features = {}
        
        # 耳蜗处理
        cochlear_left = self.cochlea(spectrogram)
        features['cochlea_left'] = cochlear_left
        
        # 耳蜗核
        cn_left = self.cochlear_nucleus(cochlear_left)
        features['cochlear_nucleus_left'] = cn_left
        
        if self.use_binaural and spectrogram_right is not None:
            # 右耳处理
            cochlear_right = self.cochlea(spectrogram_right)
            cn_right = self.cochlear_nucleus(cochlear_right)
            
            # 双耳整合 (上橄榄)
            binaural = self.superior_olivary(cn_left['output'], cn_right['output'])
            features.update(binaural)
            
            # 下丘
            ic_output = self.inferior_colliculus(binaural['output'])
        else:
            # 单耳处理
            ic_output = self.inferior_colliculus(cn_left['output'])
        
        features.update(ic_output)
        features['output'] = ic_output['output']
        
        return features
    
    def get_output_dim(self) -> int:
        return self.output_dim


# 测试
if __name__ == "__main__":
    print("=== TNN小鼠听觉系统测试 ===\n")
    
    # 创建听觉系统
    auditory = MouseAuditorySystem()
    
    # 模拟音频输入 (64频带，100时间帧)
    batch_size = 2
    T, F = 100, 64
    audio_left = torch.rand(batch_size, T, F)
    audio_right = torch.rand(batch_size, T, F)
    
    print(f"音频输入: {audio_left.shape}")
    
    # 前向传播
    with torch.no_grad():
        features = auditory(audio_left, audio_right)
    
    print(f"\n各级特征:")
    for name, feat in features.items():
        if isinstance(feat, torch.Tensor):
            print(f"  {name}: {feat.shape}")
    
    print(f"\n声音类型预测:")
    print(f"  概率: {features['sound_type_prob']}")
    
    print(f"\n惊吓反应概率:")
    print(f"  {features['startle_prob'].squeeze()}")
    
    print(f"\n总参数量: {sum(p.numel() for p in auditory.parameters())/1e6:.2f}M")
    
    print("\n✓ 听觉系统测试通过!")
