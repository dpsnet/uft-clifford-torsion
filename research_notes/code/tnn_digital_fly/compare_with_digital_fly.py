"""
与Eon Systems数字果蝇对比分析

Eon Systems数字果蝇规格:
- 125,000神经元
- 50M突触
- LIF（Leaky Integrate-and-Fire）模型
- 全连接组（Connectome）基础

TNN-数字果蝇规格:
- 约250,000参数
- 扭转神经网络架构
- 谱维调制
- 短期可塑性（STP）

对比维度:
1. 行为准确性
2. 响应延迟
3. 能量效率
4. 鲁棒性
5. 可解释性
"""

import numpy as np
import torch
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from scipy.spatial.distance import cosine
from scipy.stats import pearsonr


@dataclass
class BehaviorMetrics:
    """行为度量指标"""
    # 轨迹相似度
    trajectory_similarity: float = 0.0
    trajectory_rmse: float = 0.0
    
    # 速度匹配
    speed_correlation: float = 0.0
    speed_rmse: float = 0.0
    
    # 转向匹配
    turning_correlation: float = 0.0
    turning_accuracy: float = 0.0
    
    # 行为序列匹配
    behavior_sequence_accuracy: float = 0.0
    behavior_timing_error: float = 0.0


@dataclass
class ResponseMetrics:
    """响应度量指标"""
    # 延迟
    locomotion_latency: float = 0.0      # 行走启动延迟 (ms)
    escape_latency: float = 0.0          # 逃跑响应延迟 (ms)
    grooming_latency: float = 0.0        # 理毛启动延迟 (ms)
    foraging_latency: float = 0.0        # 觅食响应延迟 (ms)
    
    # 持续时间
    behavior_duration_accuracy: float = 0.0


@dataclass
class EfficiencyMetrics:
    """效率度量指标"""
    # 计算效率
    flops_per_step: int = 0              # 每步浮点运算数
    memory_usage_mb: float = 0.0
    
    # 能量模型（相对值）
    relative_energy_cost: float = 1.0
    synaptic_operations: int = 0
    
    # 实时性能
    steps_per_second: float = 0.0
    real_time_factor: float = 1.0        # 仿真速度/真实时间


@dataclass
class RobustnessMetrics:
    """鲁棒性度量指标"""
    # 扰动容忍
    stability_under_noise: float = 0.0   # 噪声下的稳定性
    perturbation_recovery_time: float = 0.0
    
    # 故障容忍
    lesion_resistance: float = 0.0       # 损伤抗性
    graceful_degradation: float = 0.0    # 优雅降级
    
    # 环境适应
    adaptation_speed: float = 0.0


@dataclass
class InterpretabilityMetrics:
    """可解释性度量指标"""
    # 参数-行为映射
    parameter_behavior_correlation: float = 0.0
    
    # 激活可视化
    activation_sparsity: float = 0.0
    feature_selectivity: float = 0.0
    
    # 因果分析
    intervention_effect_size: float = 0.0
    counterfactual_consistency: float = 0.0


class EonFlyReference:
    """
    Eon Systems数字果蝇参考数据
    
    基于文献和公开数据的基准值
    """
    
    # 行为参数（基于真实果蝇和Eon仿真）
    REFERENCE_BEHAVIORS = {
        'walking_speed_mm_s': 20.0,           # 平均行走速度
        'stride_frequency_hz': 10.0,          # 步频
        'turning_speed_rad_s': 2.0,           # 转向速度
        'grooming_duration_s': 5.0,           # 理毛持续时间
        'escape_latency_ms': 50.0,            # 逃跑延迟
        'foraging_efficiency': 0.7,           # 觅食效率
    }
    
    # 神经参数
    REFERENCE_NEURAL = {
        'neurons': 125000,
        'synapses': 50000000,
        'firing_rate_hz': 10.0,
        'synaptic_delay_ms': 1.0,
    }
    
    # 轨迹模板（模拟）
    @staticmethod
    def generate_reference_trajectory(
        behavior: str,
        duration_steps: int,
        dt: float = 0.01
    ) -> Dict[str, np.ndarray]:
        """生成参考轨迹"""
        t = np.arange(duration_steps) * dt
        
        if behavior == 'walking':
            # 直线行走
            speed = 20.0  # mm/s
            x = speed * t
            y = np.zeros_like(t)
            speed_profile = np.full_like(t, speed)
            
        elif behavior == 'circling':
            # 圆周运动
            radius = 10.0  # mm
            angular_speed = 2.0  # rad/s
            x = radius * np.cos(angular_speed * t)
            y = radius * np.sin(angular_speed * t)
            speed_profile = np.full_like(t, radius * angular_speed)
            
        elif behavior == 'escape':
            # 逃跑：快速直线
            speed = 60.0  # mm/s
            x = speed * t
            y = np.zeros_like(t)
            # 速度衰减
            speed_profile = speed * np.exp(-t / 0.5)
            
        elif behavior == 'grooming':
            # 理毛：位置基本不变，有小幅度移动
            x = 0.5 * np.sin(2 * np.pi * 2 * t)
            y = 0.5 * np.cos(2 * np.pi * 2 * t)
            speed_profile = np.full_like(t, 3.0)
            
        else:
            x = np.zeros_like(t)
            y = np.zeros_like(t)
            speed_profile = np.zeros_like(t)
        
        return {
            'x': x,
            'y': y,
            'speed': speed_profile,
            'time': t
        }


class DigitalFlyComparator:
    """
    TNN-数字果蝇与Eon数字果蝇对比器
    """
    
    def __init__(self):
        self.reference = EonFlyReference()
        
        # 存储对比结果
        self.behavior_metrics = BehaviorMetrics()
        self.response_metrics = ResponseMetrics()
        self.efficiency_metrics = EfficiencyMetrics()
        self.robustness_metrics = RobustnessMetrics()
        self.interpretability_metrics = InterpretabilityMetrics()
    
    def compare_trajectories(
        self,
        reference_trajectory: Dict[str, np.ndarray],
        test_trajectory: Dict[str, np.ndarray]
    ) -> BehaviorMetrics:
        """
        对比轨迹相似度
        """
        metrics = BehaviorMetrics()
        
        # 确保长度一致
        min_len = min(len(reference_trajectory['x']), len(test_trajectory['x']))
        
        ref_x = reference_trajectory['x'][:min_len]
        ref_y = reference_trajectory['y'][:min_len]
        ref_speed = reference_trajectory['speed'][:min_len]
        
        test_x = test_trajectory['x'][:min_len]
        test_y = test_trajectory['y'][:min_len]
        test_speed = test_trajectory['speed'][:min_len]
        
        # 轨迹相似度（位置RMSE）
        position_error = np.sqrt((ref_x - test_x)**2 + (ref_y - test_y)**2)
        metrics.trajectory_rmse = np.mean(position_error)
        
        # 余弦相似度
        ref_path = np.vstack([ref_x, ref_y]).flatten()
        test_path = np.vstack([test_x, test_y]).flatten()
        
        if np.linalg.norm(ref_path) > 0 and np.linalg.norm(test_path) > 0:
            similarity = 1 - cosine(ref_path, test_path)
            metrics.trajectory_similarity = max(0, similarity)
        
        # 速度相关性
        if len(ref_speed) > 1 and np.std(ref_speed) > 0:
            corr, _ = pearsonr(ref_speed, test_speed)
            metrics.speed_correlation = corr if not np.isnan(corr) else 0.0
        
        metrics.speed_rmse = np.sqrt(np.mean((ref_speed - test_speed)**2))
        
        # 转向准确性
        ref_heading = np.arctan2(np.diff(ref_y), np.diff(ref_x))
        test_heading = np.arctan2(np.diff(test_y), np.diff(test_x))
        
        if len(ref_heading) > 0:
            heading_error = np.abs(np.arctan2(
                np.sin(ref_heading - test_heading),
                np.cos(ref_heading - test_heading)
            ))
            metrics.turning_accuracy = 1 - np.mean(heading_error) / np.pi
        
        self.behavior_metrics = metrics
        return metrics
    
    def measure_response_latency(
        self,
        stimulus_time: float,
        response_time: float,
        behavior_type: str
    ) -> float:
        """
        测量响应延迟
        
        Args:
            stimulus_time: 刺激开始时间 (s)
            response_time: 响应开始时间 (s)
            behavior_type: 行为类型
        
        Returns:
            latency_ms: 延迟（毫秒）
        """
        latency_ms = (response_time - stimulus_time) * 1000
        
        if behavior_type == 'escape':
            self.response_metrics.escape_latency = latency_ms
        elif behavior_type == 'walking':
            self.response_metrics.locomotion_latency = latency_ms
        elif behavior_type == 'grooming':
            self.response_metrics.grooming_latency = latency_ms
        elif behavior_type == 'foraging':
            self.response_metrics.foraging_latency = latency_ms
        
        return latency_ms
    
    def calculate_efficiency(
        self,
        brain_model: torch.nn.Module,
        steps_per_second: float,
        device: str = 'cpu'
    ) -> EfficiencyMetrics:
        """
        计算效率指标
        """
        metrics = EfficiencyMetrics()
        
        # 计算FLOPs
        total_params = sum(p.numel() for p in brain_model.parameters())
        
        # 简化估计：每参数每步2 FLOPs（乘加）
        metrics.flops_per_step = total_params * 2
        
        # 内存使用估计
        param_memory = total_params * 4 / (1024 * 1024)  # MB (float32)
        metrics.memory_usage_mb = param_memory * 2  # 参数 + 梯度
        
        # 计算性能
        metrics.steps_per_second = steps_per_second
        
        # 实时因子（假设100Hz生物时间）
        metrics.real_time_factor = steps_per_second / 100.0
        
        # 相对能量成本（与Eon对比）
        # Eon: 125K神经元 × 10Hz × 50M synapses
        eon_synaptic_ops = 125000 * 10 * 50
        # TNN: 参数 × 处理复杂度
        tnn_ops = metrics.flops_per_step / 1e6  # 百万操作
        metrics.relative_energy_cost = tnn_ops / eon_synaptic_ops
        
        self.efficiency_metrics = metrics
        return metrics
    
    def evaluate_robustness(
        self,
        brain_model: torch.nn.Module,
        test_function,
        noise_levels: List[float] = [0.0, 0.1, 0.2, 0.5]
    ) -> RobustnessMetrics:
        """
        评估鲁棒性
        
        Args:
            brain_model: 大脑模型
            test_function: 测试函数，返回性能分数
            noise_levels: 噪声水平列表
        """
        metrics = RobustnessMetrics()
        
        # 基准性能
        baseline_performance = test_function(brain_model, noise_level=0.0)
        
        # 不同噪声下的性能
        performances = []
        for noise in noise_levels:
            perf = test_function(brain_model, noise_level=noise)
            performances.append(perf / baseline_performance if baseline_performance > 0 else 0)
        
        # 稳定性：噪声下性能保持率
        metrics.stability_under_noise = np.mean(performances[1:]) if len(performances) > 1 else 1.0
        
        # 优雅降级：性能随噪声线性下降程度
        if len(performances) >= 2:
            degradation = np.polyfit(noise_levels, performances, 1)[0]
            metrics.graceful_degradation = max(0, 1 + degradation)  # 越接近1越好
        
        self.robustness_metrics = metrics
        return metrics
    
    def analyze_interpretability(
        self,
        brain_model: torch.nn.Module,
        sample_inputs: List[torch.Tensor]
    ) -> InterpretabilityMetrics:
        """
        分析可解释性
        """
        metrics = InterpretabilityMetrics()
        
        # 激活稀疏性
        activation_stats = []
        
        with torch.no_grad():
            for inp in sample_inputs:
                # 获取中间激活（假设模型有hook）
                # 这里简化处理
                pass
        
        # 特征选择性（简化估计）
        # 高选择性 = 不同输入产生明显不同的激活模式
        metrics.feature_selectivity = 0.5  # 占位值
        
        self.interpretability_metrics = metrics
        return metrics
    
    def generate_comparison_report(self) -> str:
        """
        生成对比报告
        """
        report = []
        report.append("=" * 70)
        report.append("TNN-数字果蝇 vs Eon Systems数字果蝇 对比报告")
        report.append("=" * 70)
        
        # 架构对比
        report.append("\n## 1. 架构对比")
        report.append(f"\nEon Systems数字果蝇:")
        report.append(f"  - 神经元数量: {self.reference.REFERENCE_NEURAL['neurons']:,}")
        report.append(f"  - 突触数量: {self.reference.REFERENCE_NEURAL['synapses']:,}")
        report.append(f"  - 模型类型: LIF脉冲神经网络")
        report.append(f"  - 连接方式: 生物Connectome基础")
        
        report.append(f"\nTNN-数字果蝇:")
        report.append(f"  - 参数数量: ~250,000")
        report.append(f"  - 模型类型: 扭转神经网络")
        report.append(f"  - 核心特征: 谱维调制 + 短期可塑性")
        report.append(f"  - 参数比: 250K / 125K = 2.0x")
        
        # 行为对比
        report.append("\n## 2. 行为准确性对比")
        report.append(f"  - 轨迹相似度: {self.behavior_metrics.trajectory_similarity:.3f}")
        report.append(f"  - 轨迹RMSE: {self.behavior_metrics.trajectory_rmse:.3f} mm")
        report.append(f"  - 速度相关性: {self.behavior_metrics.speed_correlation:.3f}")
        report.append(f"  - 转向准确性: {self.behavior_metrics.turning_accuracy:.3f}")
        
        # 响应延迟对比
        report.append("\n## 3. 响应延迟对比")
        report.append(f"  - 行走启动延迟: {self.response_metrics.locomotion_latency:.1f} ms")
        report.append(f"  - 逃跑响应延迟: {self.response_metrics.escape_latency:.1f} ms")
        report.append(f"  - 理毛启动延迟: {self.response_metrics.grooming_latency:.1f} ms")
        report.append(f"  - 觅食响应延迟: {self.response_metrics.foraging_latency:.1f} ms")
        
        # 效率对比
        report.append("\n## 4. 能量效率对比")
        report.append(f"  - TNN FLOPs/步: {self.efficiency_metrics.flops_per_step:,}")
        report.append(f"  - 内存使用: {self.efficiency_metrics.memory_usage_mb:.2f} MB")
        report.append(f"  - 实时因子: {self.efficiency_metrics.real_time_factor:.2f}x")
        report.append(f"  - 相对能量成本: {self.efficiency_metrics.relative_energy_cost:.4f}")
        
        # 鲁棒性对比
        report.append("\n## 5. 鲁棒性对比")
        report.append(f"  - 噪声稳定性: {self.robustness_metrics.stability_under_noise:.3f}")
        report.append(f"  - 优雅降级: {self.robustness_metrics.graceful_degradation:.3f}")
        
        # 可解释性对比
        report.append("\n## 6. 可解释性对比")
        report.append(f"  - 激活稀疏性: {self.interpretability_metrics.activation_sparsity:.3f}")
        report.append(f"  - 特征选择性: {self.interpretability_metrics.feature_selectivity:.3f}")
        
        # 综合评价
        report.append("\n## 7. 综合评价")
        
        # 计算综合评分
        behavior_score = (
            self.behavior_metrics.trajectory_similarity * 0.3 +
            self.behavior_metrics.speed_correlation * 0.3 +
            self.behavior_metrics.turning_accuracy * 0.4
        )
        
        response_score = 1.0  # 如果延迟在合理范围内
        if self.response_metrics.escape_latency < 100:  # ms
            response_score = 1.0
        elif self.response_metrics.escape_latency < 200:
            response_score = 0.8
        else:
            response_score = 0.5
        
        efficiency_score = min(1.0, self.efficiency_metrics.real_time_factor)
        
        overall_score = (behavior_score + response_score + efficiency_score) / 3
        
        report.append(f"  - 行为准确性评分: {behavior_score:.3f}/1.0")
        report.append(f"  - 响应速度评分: {response_score:.3f}/1.0")
        report.append(f"  - 计算效率评分: {efficiency_score:.3f}/1.0")
        report.append(f"  - 综合评分: {overall_score:.3f}/1.0")
        
        report.append("\n## 8. 关键发现")
        
        # 自动分析关键发现
        findings = []
        
        if self.behavior_metrics.trajectory_similarity > 0.7:
            findings.append("✓ 轨迹与参考行为高度相似")
        elif self.behavior_metrics.trajectory_similarity > 0.5:
            findings.append("△ 轨迹与参考行为中等相似")
        else:
            findings.append("✗ 轨迹与参考行为差异较大")
        
        if self.response_metrics.escape_latency < 100:
            findings.append("✓ 逃跑响应延迟在生物合理范围内 (<100ms)")
        else:
            findings.append("△ 逃跑响应延迟偏长")
        
        if self.efficiency_metrics.real_time_factor >= 1.0:
            findings.append("✓ 支持实时仿真")
        else:
            findings.append("△ 仿真速度慢于实时")
        
        for finding in findings:
            report.append(f"  {finding}")
        
        report.append("\n" + "=" * 70)
        
        return "\n".join(report)
    
    def save_report(self, filepath: str):
        """保存对比报告到文件"""
        report = self.generate_comparison_report()
        with open(filepath, 'w') as f:
            f.write(report)
        print(f"对比报告已保存到: {filepath}")


# 测试代码
if __name__ == "__main__":
    print("=" * 60)
    print("对比分析模块测试")
    print("=" * 60)
    
    comparator = DigitalFlyComparator()
    
    print("\nEon Systems参考数据:")
    for key, value in comparator.reference.REFERENCE_BEHAVIORS.items():
        print(f"  {key}: {value}")
    
    # 测试轨迹对比
    print("\n轨迹对比测试:")
    ref_traj = EonFlyReference.generate_reference_trajectory('walking', 100)
    
    # 模拟测试轨迹（添加噪声）
    test_traj = {
        'x': ref_traj['x'] + np.random.randn(100) * 2,
        'y': ref_traj['y'] + np.random.randn(100) * 2,
        'speed': ref_traj['speed'] + np.random.randn(100) * 3,
        'time': ref_traj['time']
    }
    
    metrics = comparator.compare_trajectories(ref_traj, test_traj)
    print(f"  轨迹相似度: {metrics.trajectory_similarity:.3f}")
    print(f"  轨迹RMSE: {metrics.trajectory_rmse:.3f}")
    print(f"  速度相关性: {metrics.speed_correlation:.3f}")
    
    # 测试报告生成
    print("\n报告预览:")
    report = comparator.generate_comparison_report()
    print(report[:1000] + "...")
    
    print("\n" + "=" * 60)
    print("测试完成!")
