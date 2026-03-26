"""
果蝇视觉处理系统
模拟果蝇复眼的视觉通路

果蝇视觉特点:
- 复眼: 约800个小眼（ommatidia）
- 视觉分辨率: 非常低，但时间分辨率极高（ flicker fusion ~250Hz）
- 运动检测: 是果蝇视觉的核心功能
- 视觉通路: 复眼 -> 层状细胞（L1-L5）-> 髓质（Medulla）-> 小叶（Lobula）

本实现使用简化模型:
- 32×32像素输入（模拟复眼低分辨率）
- 运动检测（ON/OFF通道，方向选择性）
- Looming检测（扩展刺激检测，用于逃跑反应）
- 颜色处理（简化版）
"""

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Tuple, Optional
from scipy.ndimage import gaussian_filter


class MotionDetector:
    """
    运动检测器（Hassenstein-Reichardt模型简化版）
    
    果蝇使用相关型运动检测器来感知运动方向
    """
    
    def __init__(self, n_directions: int = 8, time_constant: float = 0.1):
        """
        Args:
            n_directions: 检测方向数量
            time_constant: 时间常数（秒）
        """
        self.n_directions = n_directions
        self.time_constant = time_constant
        
        # 方向角度
        self.directions = np.linspace(0, 2 * np.pi, n_directions, endpoint=False)
        
        # 延迟线状态
        self.delayed_frames = []
        self.max_delay = 3
    
    def process(self, current_frame: np.ndarray) -> np.ndarray:
        """
        处理帧并输出运动检测信号
        
        Args:
            current_frame: [H, W] 灰度图像
        
        Returns:
            motion_map: [H, W, n_directions] 各方向运动强度
        """
        # 存储帧历史
        self.delayed_frames.append(current_frame.copy())
        if len(self.delayed_frames) > self.max_delay:
            self.delayed_frames.pop(0)
        
        h, w = current_frame.shape
        motion_map = np.zeros((h, w, self.n_directions))
        
        if len(self.delayed_frames) < 2:
            return motion_map
        
        # 获取延迟帧
        delayed = self.delayed_frames[-2]
        
        # 对每个方向计算运动
        for i, angle in enumerate(self.directions):
            # 计算偏移
            dx = int(np.round(np.cos(angle)))
            dy = int(np.round(np.sin(angle)))
            
            # 空间偏移当前帧
            shifted = np.roll(current_frame, (dy, dx), axis=(0, 1))
            
            # 相关计算: 当前帧偏移位置 × 延迟帧原位置
            correlation = shifted * delayed
            
            motion_map[:, :, i] = correlation
        
        return motion_map
    
    def reset(self):
        """重置状态"""
        self.delayed_frames = []


class LoomingDetector:
    """
    Looming刺激检测器
    
    果蝇对快速扩展的视觉刺激（looming）有强烈的逃跑反应
    用于检测捕食者接近
    """
    
    def __init__(
        self,
        n_sectors: int = 12,       # 径向扇区数
        radial_bins: int = 8,      # 径向分层
        expansion_threshold: float = 0.5,
        time_window: int = 5
    ):
        self.n_sectors = n_sectors
        self.radial_bins = radial_bins
        self.expansion_threshold = expansion_threshold
        self.time_window = time_window
        
        # 历史记录
        self.size_history = []
        self.max_history = 20
    
    def detect(self, frame: np.ndarray, center: Optional[Tuple[int, int]] = None) -> Tuple[float, np.ndarray]:
        """
        检测looming刺激
        
        Args:
            frame: [H, W] 灰度图像
            center: 视野中心，默认图像中心
        
        Returns:
            looming_score: 0-1，looming程度
            looming_map: [n_sectors] 各扇区looming信号
        """
        h, w = frame.shape
        
        if center is None:
            center = (h // 2, w // 2)
        
        cy, cx = center
        
        # 计算到中心的距离
        y, x = np.ogrid[:h, :w]
        r = np.sqrt((x - cx)**2 + (y - cy)**2)
        theta = np.arctan2(y - cy, x - cx)
        
        # 最大半径
        max_r = min(h, w) // 2
        
        # 计算每个扇区的平均强度
        sector_intensities = []
        
        for i in range(self.n_sectors):
            theta_start = 2 * np.pi * i / self.n_sectors - np.pi
            theta_end = 2 * np.pi * (i + 1) / self.n_sectors - np.pi
            
            # 创建扇区掩码
            sector_mask = (theta >= theta_start) & (theta < theta_end) & (r < max_r)
            
            if np.any(sector_mask):
                sector_intensity = np.mean(frame[sector_mask])
            else:
                sector_intensity = 0.0
            
            sector_intensities.append(sector_intensity)
        
        sector_intensities = np.array(sector_intensities)
        
        # 存储历史
        self.size_history.append(sector_intensities.copy())
        if len(self.size_history) > self.max_history:
            self.size_history.pop(0)
        
        # 计算扩展率
        if len(self.size_history) >= self.time_window:
            old = np.mean(self.size_history[-self.time_window], axis=0)
            recent = np.mean(self.size_history[-1], axis=0)
            
            # 扩展率 = (当前 - 过去) / 过去
            expansion_rate = np.where(old > 0.01, (recent - old) / (old + 1e-6), 0)
            
            # looming分数：正扩展的累积
            looming_map = np.maximum(0, expansion_rate)
            looming_score = np.mean(looming_map)
        else:
            looming_score = 0.0
            looming_map = np.zeros(self.n_sectors)
        
        return looming_score, looming_map
    
    def reset(self):
        """重置状态"""
        self.size_history = []


class ONOFFChannels:
    """
    ON/OFF通道分离
    
    果蝇视觉通路中，光感受器信号被分离为:
    - ON通道: 对亮度增加响应
    - OFF通道: 对亮度减少响应
    """
    
    def __init__(self, time_constant: float = 0.05):
        self.time_constant = time_constant
        self.prev_frame = None
    
    def process(self, frame: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        分离ON和OFF通道
        
        Returns:
            on_channel: 亮度增加区域
            off_channel: 亮度减少区域
        """
        if self.prev_frame is None:
            self.prev_frame = frame.copy()
            return np.zeros_like(frame), np.zeros_like(frame)
        
        # 计算差分
        diff = frame - self.prev_frame
        
        # ON通道: 正变化
        on_channel = np.maximum(0, diff)
        
        # OFF通道: 负变化
        off_channel = np.maximum(0, -diff)
        
        # 更新历史
        self.prev_frame = frame.copy()
        
        return on_channel, off_channel
    
    def reset(self):
        """重置状态"""
        self.prev_frame = None


class FlyVision(nn.Module):
    """
    果蝇视觉处理系统
    
    完整的视觉通路模拟:
    1. 预处理: 归一化、降采样到32×32
    2. ON/OFF分离
    3. 运动检测
    4. Looming检测
    5. 特征提取和输出
    
    输出: 1024维向量（32×32特征图）
    """
    
    def __init__(
        self,
        input_size: Tuple[int, int] = (128, 128),  # 原始输入大小
        output_size: Tuple[int, int] = (32, 32),   # 果蝇复眼等效分辨率
        n_motion_directions: int = 8,
        use_color: bool = False,
        device='cpu'
    ):
        super().__init__()
        
        self.input_size = input_size
        self.output_size = output_size
        self.n_motion_directions = n_motion_directions
        self.use_color = use_color
        self.device = device
        
        # 视觉预处理
        self.input_channels = 3 if use_color else 1
        
        # 简化的神经网络特征提取 - 直接投影避免尺寸计算问题
        input_dim = self.input_channels * input_size[0] * input_size[1]
        self.feature_extractor = nn.Sequential(
            nn.Linear(input_dim, 512),
            nn.ReLU(),
            nn.Linear(512, 256),
            nn.ReLU()
        ).to(device)
        
        # 输出投影到1024维
        self.output_projection = nn.Sequential(
            nn.Linear(256, 1024),
            nn.LayerNorm(1024),
            nn.GELU()
        ).to(device)
        
        # 传统视觉处理组件
        self.motion_detector = MotionDetector(n_directions=n_motion_directions)
        self.looming_detector = LoomingDetector()
        self.onoff_channels = ONOFFChannels()
        
        # 状态
        self.current_motion_map = None
        self.current_looming_score = 0.0
        self.current_looming_map = None
    
    def preprocess_frame(self, frame: np.ndarray) -> torch.Tensor:
        """
        预处理输入帧
        
        Args:
            frame: [H, W] 或 [H, W, 3] numpy数组
        
        Returns:
            tensor: [1, C, H, W] torch张量
        """
        # 归一化到[0, 1]
        if frame.dtype == np.uint8:
            frame = frame.astype(np.float32) / 255.0
        
        # 确保有通道维度
        if len(frame.shape) == 2:
            frame = np.expand_dims(frame, axis=0)  # [1, H, W]
        else:
            frame = np.transpose(frame, (2, 0, 1))  # [C, H, W]
        
        # 转换为tensor
        tensor = torch.from_numpy(frame).unsqueeze(0).to(self.device)  # [1, C, H, W]
        
        return tensor
    
    def forward(self, frame: np.ndarray) -> torch.Tensor:
        """
        处理视觉输入
        
        Args:
            frame: numpy图像数组
        
        Returns:
            visual_features: [1024] 视觉特征向量
        """
        # 转换为灰度用于传统处理
        if len(frame.shape) == 3:
            gray_frame = np.mean(frame, axis=2)
        else:
            gray_frame = frame
        
        # 调整大小
        from scipy.ndimage import zoom
        zoom_factors = (self.input_size[0] / gray_frame.shape[0], 
                       self.input_size[1] / gray_frame.shape[1])
        resized_gray = zoom(gray_frame, zoom_factors, order=1)
        
        # === 传统视觉处理 ===
        # ON/OFF分离
        on_channel, off_channel = self.onoff_channels.process(resized_gray)
        
        # 运动检测
        self.current_motion_map = self.motion_detector.process(resized_gray)
        
        # Looming检测
        self.current_looming_score, self.current_looming_map = \
            self.looming_detector.detect(resized_gray)
        
        # === 神经网络特征提取 ===
        tensor_input = self.preprocess_frame(frame)
        
        # 展平输入
        tensor_flat = tensor_input.reshape(1, -1)
        
        with torch.no_grad():
            features = self.feature_extractor(tensor_flat)
            
            # 投影到1024维
            visual_features = self.output_projection(features)
        
        return visual_features.squeeze(0)
    
    def get_motion_features(self) -> Optional[np.ndarray]:
        """获取运动检测特征"""
        if self.current_motion_map is None:
            return None
        
        # 压缩运动图为低维特征
        # [H, W, n_directions] -> 按方向平均
        motion_features = np.mean(self.current_motion_map, axis=(0, 1))
        return motion_features
    
    def get_looming_features(self) -> Tuple[float, Optional[np.ndarray]]:
        """获取looming检测特征"""
        return self.current_looming_score, self.current_looming_map
    
    def get_edge_features(self, frame: np.ndarray) -> np.ndarray:
        """
        提取边缘特征（果蝇对边缘敏感）
        
        使用简单的Sobel算子
        """
        if len(frame.shape) == 3:
            gray = np.mean(frame, axis=2)
        else:
            gray = frame
        
        # Sobel算子
        sobel_x = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]])
        sobel_y = np.array([[-1, -2, -1], [0, 0, 0], [1, 2, 1]])
        
        from scipy.ndimage import convolve
        grad_x = convolve(gray, sobel_x)
        grad_y = convolve(gray, sobel_y)
        
        # 梯度幅值
        edge_magnitude = np.sqrt(grad_x**2 + grad_y**2)
        
        # 调整大小到输出尺寸
        from scipy.ndimage import zoom
        zoom_factors = (self.output_size[0] / edge_magnitude.shape[0],
                       self.output_size[1] / edge_magnitude.shape[1])
        edge_resized = zoom(edge_magnitude, zoom_factors, order=1)
        
        return edge_resized.flatten()
    
    def get_polarity_features(self, frame: np.ndarray) -> np.ndarray:
        """
        提取亮/暗区域特征（果蝇对明暗对比敏感）
        """
        if len(frame.shape) == 3:
            gray = np.mean(frame, axis=2)
        else:
            gray = frame
        
        # 高斯平滑
        from scipy.ndimage import gaussian_filter
        smoothed = gaussian_filter(gray, sigma=2.0)
        
        # 计算局部均值
        local_mean = gaussian_filter(smoothed, sigma=5.0)
        
        # 亮于局部均值的区域
        bright_regions = (smoothed > local_mean).astype(np.float32)
        
        # 调整大小
        from scipy.ndimage import zoom
        zoom_factors = (self.output_size[0] / bright_regions.shape[0],
                       self.output_size[1] / bright_regions.shape[1])
        polarity_resized = zoom(bright_regions, zoom_factors, order=1)
        
        return polarity_resized.flatten()
    
    def reset(self):
        """重置所有视觉处理状态"""
        self.motion_detector.reset()
        self.looming_detector.reset()
        self.onoff_channels.reset()
        self.current_motion_map = None
        self.current_looming_score = 0.0
        self.current_looming_map = None
    
    def detect_escape_stimulus(self, threshold: float = 0.3) -> bool:
        """
        检测是否需要逃跑的looming刺激
        
        Returns:
            should_escape: 是否触发逃跑
        """
        return self.current_looming_score > threshold
    
    def get_attention_map(self) -> Optional[np.ndarray]:
        """
        获取视觉注意力图
        
        结合运动、looming和边缘信息
        """
        if self.current_motion_map is None:
            return None
        
        # 平均所有方向的运动
        motion_magnitude = np.mean(self.current_motion_map, axis=2)
        
        # 归一化
        if np.max(motion_magnitude) > 0:
            motion_magnitude = motion_magnitude / np.max(motion_magnitude)
        
        return motion_magnitude


# 测试代码
if __name__ == "__main__":
    print("=" * 60)
    print("果蝇视觉系统测试")
    print("=" * 60)
    
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"使用设备: {device}")
    
    # 创建视觉系统
    vision = FlyVision(device=device)
    
    print("\n视觉系统参数:")
    print(f"  输入大小: {vision.input_size}")
    print(f"  输出大小: {vision.output_size}")
    print(f"  运动方向数: {vision.n_motion_directions}")
    
    # 测试运动检测
    print("\n" + "=" * 60)
    print("运动检测测试")
    
    motion_detector = MotionDetector(n_directions=8)
    
    # 创建移动的圆点
    for t in range(10):
        frame = np.zeros((64, 64))
        x = int(32 + 10 * np.cos(t * 0.5))
        y = int(32 + 10 * np.sin(t * 0.5))
        if 0 <= x < 64 and 0 <= y < 64:
            frame[y, x] = 1.0
        
        motion_map = motion_detector.process(frame)
        
        if t > 0:
            motion_per_direction = np.mean(motion_map, axis=(0, 1))
            dominant_direction = np.argmax(motion_per_direction)
            print(f"  帧 {t}: 主导运动方向={dominant_direction}, 强度={motion_per_direction[dominant_direction]:.3f}")
    
    # 测试looming检测
    print("\n" + "=" * 60)
    print("Looming检测测试")
    
    looming_detector = LoomingDetector()
    
    # 创建扩展的圆
    for t in range(10):
        frame = np.zeros((64, 64))
        center = (32, 32)
        radius = int(2 + t * 2)
        
        y, x = np.ogrid[:64, :64]
        mask = (x - center[1])**2 + (y - center[0])**2 <= radius**2
        frame[mask] = 1.0
        
        score, sectors = looming_detector.detect(frame)
        print(f"  帧 {t}: looming分数={score:.3f}")
    
    # 测试完整视觉系统
    print("\n" + "=" * 60)
    print("完整视觉系统测试")
    
    # 创建测试帧（灰度）
    test_frame = np.random.rand(128, 128).astype(np.float32)
    
    features = vision(test_frame)
    print(f"  视觉特征形状: {features.shape}")
    print(f"  视觉特征范围: [{features.min():.3f}, {features.max():.3f}]")
    
    motion_features = vision.get_motion_features()
    if motion_features is not None:
        print(f"  运动特征: {motion_features}")
    
    looming_score, looming_map = vision.get_looming_features()
    print(f"  Looming分数: {looming_score:.3f}")
    
    print("\n" + "=" * 60)
    print("测试完成!")
