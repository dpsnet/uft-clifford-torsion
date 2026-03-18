"""
涌现行为分析模块
分析群体仿真中的涌现现象

分析指标:
- 群体聚集/分散模式
- 资源竞争与合作
- 信息素路径形成
- 捕食者-猎物动态
- 社交结构形成
"""

import numpy as np
import torch
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
from dataclasses import dataclass
from scipy.spatial.distance import pdist, squareform
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.stats import entropy
import warnings
warnings.filterwarnings('ignore')

from population_sim import SuperWormAgent, PopulationSimulation
from ecosystem_env import SuperEcosystem, Pheromone


@dataclass
class EmergenceMetrics:
    """涌现指标数据结构"""
    # 群体结构指标
    clustering_coefficient: float = 0.0
    mean_cluster_size: float = 0.0
    n_clusters: int = 0
    
    # 空间分布指标
    spatial_entropy: float = 0.0
    spatial_uniformity: float = 0.0
    mean_nearest_neighbor: float = 0.0
    
    # 行为同步性
    behavior_entropy: float = 0.0
    dominant_behavior: str = ''
    behavior_sync_index: float = 0.0
    
    # 社会网络指标
    network_density: float = 0.0
    avg_degree: float = 0.0
    network_centrality: float = 0.0
    
    # 信息素指标
    pheromone_concentration: float = 0.0
    trail_strength: float = 0.0
    
    # 资源利用指标
    foraging_efficiency: float = 0.0
    resource_distribution: float = 0.0
    
    # 演化指标
    population_growth_rate: float = 0.0
    survival_rate: float = 0.0
    reproduction_rate: float = 0.0


class EmergenceAnalyzer:
    """
    涌现行为分析器
    分析群体仿真中的涌现现象
    """
    
    def __init__(self, simulation: PopulationSimulation):
        self.sim = simulation
        self.env = simulation.env
        self.worms = simulation.worms
        
        # 时序数据存储
        self.metrics_history: List[EmergenceMetrics] = []
        self.spatial_grids: List[np.ndarray] = []
        self.behavior_matrices: List[np.ndarray] = []
        
    def analyze_step(self, step: int) -> EmergenceMetrics:
        """分析单步涌现指标"""
        metrics = EmergenceMetrics()
        
        # 获取当前存活的虫子
        alive_worms = [w for w in self.worms if w.is_alive]
        if len(alive_worms) < 2:
            return metrics
        
        # 提取位置数据
        positions = np.array([[w.x, w.y] for w in alive_worms])
        
        # === 群体聚集分析 ===
        cluster_metrics = self._analyze_clustering(positions)
        metrics.clustering_coefficient = cluster_metrics['coefficient']
        metrics.mean_cluster_size = cluster_metrics['mean_size']
        metrics.n_clusters = cluster_metrics['n_clusters']
        
        # === 空间分布分析 ===
        spatial_metrics = self._analyze_spatial_distribution(positions)
        metrics.spatial_entropy = spatial_metrics['entropy']
        metrics.spatial_uniformity = spatial_metrics['uniformity']
        metrics.mean_nearest_neighbor = spatial_metrics['mean_nn_distance']
        
        # === 行为分析 ===
        behavior_metrics = self._analyze_behaviors(alive_worms)
        metrics.behavior_entropy = behavior_metrics['entropy']
        metrics.dominant_behavior = behavior_metrics['dominant']
        metrics.behavior_sync_index = behavior_metrics['sync_index']
        
        # === 社交网络分析 ===
        network_metrics = self._analyze_social_network(alive_worms)
        metrics.network_density = network_metrics['density']
        metrics.avg_degree = network_metrics['avg_degree']
        metrics.network_centrality = network_metrics['centrality']
        
        # === 信息素分析 ===
        phero_metrics = self._analyze_pheromones()
        metrics.pheromone_concentration = phero_metrics['concentration']
        metrics.trail_strength = phero_metrics['trail_strength']
        
        # === 资源利用分析 ===
        resource_metrics = self._analyze_resource_utilization(alive_worms)
        metrics.foraging_efficiency = resource_metrics['efficiency']
        metrics.resource_distribution = resource_metrics['distribution']
        
        # === 演化指标 ===
        if step > 0:
            evo_metrics = self._analyze_evolution(step)
            metrics.population_growth_rate = evo_metrics['growth_rate']
            metrics.survival_rate = evo_metrics['survival_rate']
            metrics.reproduction_rate = evo_metrics['reproduction_rate']
        
        self.metrics_history.append(metrics)
        return metrics
    
    def _analyze_clustering(self, positions: np.ndarray) -> Dict:
        """分析群体聚类"""
        n = len(positions)
        if n < 2:
            return {'coefficient': 0, 'mean_size': 0, 'n_clusters': 0}
        
        # 计算距离矩阵
        distances = squareform(pdist(positions))
        
        # 使用层次聚类
        threshold = 50.0  # 聚类距离阈值
        linkage_matrix = linkage(positions, method='average')
        clusters = fcluster(linkage_matrix, threshold, criterion='distance')
        
        n_clusters = len(np.unique(clusters))
        
        # 计算每个聚类的大小
        cluster_sizes = [np.sum(clusters == i) for i in np.unique(clusters)]
        mean_cluster_size = np.mean(cluster_sizes)
        
        # 计算聚类系数（基于距离分布）
        # 邻近的虫子对比例
        close_pairs = np.sum(distances < threshold) - n  # 减去对角线
        total_pairs = n * (n - 1)
        clustering_coeff = close_pairs / total_pairs if total_pairs > 0 else 0
        
        return {
            'coefficient': clustering_coeff,
            'mean_size': mean_cluster_size,
            'n_clusters': n_clusters
        }
    
    def _analyze_spatial_distribution(self, positions: np.ndarray) -> Dict:
        """分析空间分布"""
        n = len(positions)
        
        # 将空间划分为网格
        grid_size = 20
        grid = np.zeros((grid_size, grid_size))
        
        for x, y in positions:
            gx = min(int(x / self.env.width * grid_size), grid_size - 1)
            gy = min(int(y / self.env.height * grid_size), grid_size - 1)
            grid[gy, gx] += 1
        
        # 计算空间熵（分布均匀度）
        grid_probs = grid.flatten() / (n + 1e-8)
        grid_probs = grid_probs[grid_probs > 0]
        spatial_entropy = entropy(grid_probs) if len(grid_probs) > 0 else 0
        
        # 均匀度（熵归一化）
        max_entropy = np.log(grid_size ** 2)
        uniformity = spatial_entropy / max_entropy if max_entropy > 0 else 0
        
        # 平均最近邻距离
        if n >= 2:
            distances = squareform(pdist(positions))
            np.fill_diagonal(distances, np.inf)
            mean_nn = np.mean(np.min(distances, axis=1))
        else:
            mean_nn = 0
        
        return {
            'entropy': spatial_entropy,
            'uniformity': uniformity,
            'mean_nn_distance': mean_nn,
            'grid': grid
        }
    
    def _analyze_behaviors(self, worms: List[SuperWormAgent]) -> Dict:
        """分析行为分布"""
        # 统计当前行为
        behavior_counts = defaultdict(int)
        for w in worms:
            behavior_counts[w.current_behavior] += 1
        
        behaviors = list(behavior_counts.keys())
        counts = np.array(list(behavior_counts.values()))
        probs = counts / counts.sum()
        
        # 行为熵
        behavior_entropy = entropy(probs) if len(probs) > 0 else 0
        
        # 主导行为
        dominant = behaviors[np.argmax(counts)] if behaviors else 'none'
        
        # 行为同步性（Gini系数近似）
        sorted_counts = np.sort(counts)
        n = len(counts)
        index = np.arange(1, n + 1)
        gini = (2 * np.sum(index * sorted_counts)) / (n * np.sum(sorted_counts)) - (n + 1) / n
        sync_index = 1 - gini  # 转换为同步性（越高越同步）
        
        return {
            'entropy': behavior_entropy,
            'dominant': dominant,
            'sync_index': sync_index,
            'distribution': dict(behavior_counts)
        }
    
    def _analyze_social_network(self, worms: List[SuperWormAgent]) -> Dict:
        """分析社交网络结构"""
        n = len(worms)
        if n < 2:
            return {'density': 0, 'avg_degree': 0, 'centrality': 0}
        
        # 构建邻接矩阵（基于距离）
        positions = np.array([[w.x, w.y] for w in worms])
        distances = squareform(pdist(positions))
        
        # 连接阈值
        connection_threshold = 30.0
        adjacency = (distances < connection_threshold).astype(float)
        np.fill_diagonal(adjacency, 0)
        
        # 网络密度
        n_edges = np.sum(adjacency) / 2
        max_edges = n * (n - 1) / 2
        density = n_edges / max_edges if max_edges > 0 else 0
        
        # 平均度
        degrees = np.sum(adjacency, axis=1)
        avg_degree = np.mean(degrees)
        
        # 中心性（度中心性）
        centrality = np.max(degrees) / (n - 1) if n > 1 else 0
        
        return {
            'density': density,
            'avg_degree': avg_degree,
            'centrality': centrality
        }
    
    def _analyze_pheromones(self) -> Dict:
        """分析信息素分布"""
        active_pheromones = [
            p for p in self.env.pheromones 
            if p.is_active(self.env.step_count)
        ]
        
        if not active_pheromones:
            return {'concentration': 0, 'trail_strength': 0}
        
        # 总浓度
        total_concentration = sum(
            p.get_current_intensity(self.env.step_count) 
            for p in active_pheromones
        )
        
        # 路径强度（连续信息素的线性度）
        if len(active_pheromones) >= 3:
            positions = np.array([[p.x, p.y] for p in active_pheromones])
            # 计算所有信息素对的平均距离
            distances = pdist(positions)
            # 如果有明显的路径，距离分布应该呈现双峰（近的和远的）
            trail_strength = 1.0 - np.std(distances) / (np.mean(distances) + 1e-8)
        else:
            trail_strength = 0
        
        return {
            'concentration': total_concentration,
            'trail_strength': trail_strength
        }
    
    def _analyze_resource_utilization(self, worms: List[SuperWormAgent]) -> Dict:
        """分析资源利用效率"""
        if not worms:
            return {'efficiency': 0, 'distribution': 0}
        
        # 觅食效率（单位能量消耗获取的食物）
        efficiencies = []
        for w in worms:
            if w.distance_traveled > 0:
                eff = w.food_consumed / (w.distance_traveled + 1e-8)
                efficiencies.append(eff)
        
        avg_efficiency = np.mean(efficiencies) if efficiencies else 0
        
        # 食物分布均匀性
        foods = self.env.foods
        if foods:
            food_positions = np.array([[f.x, f.y] for f in foods])
            n_food = len(foods)
            
            # 计算虫子到最近食物的平均距离
            distances_to_food = []
            for w in worms:
                dists = np.sqrt((food_positions[:, 0] - w.x)**2 + (food_positions[:, 1] - w.y)**2)
                distances_to_food.append(np.min(dists))
            
            resource_dist = np.mean(distances_to_food)
        else:
            resource_dist = 0
        
        return {
            'efficiency': avg_efficiency,
            'distribution': resource_dist
        }
    
    def _analyze_evolution(self, step: int) -> Dict:
        """分析演化指标"""
        if step < 100:
            return {'growth_rate': 0, 'survival_rate': 0, 'reproduction_rate': 0}
        
        # 种群增长率
        pop_history = self.sim.population_history
        if len(pop_history) >= 100:
            recent_growth = (pop_history[-1] - pop_history[-100]) / 100
        else:
            recent_growth = 0
        
        # 存活率
        alive = len([w for w in self.worms if w.is_alive])
        total = len(self.worms)
        survival_rate = alive / total if total > 0 else 0
        
        # 繁殖率
        if step > 0:
            repro_rate = self.sim.birth_count / step
        else:
            repro_rate = 0
        
        return {
            'growth_rate': recent_growth,
            'survival_rate': survival_rate,
            'reproduction_rate': repro_rate
        }
    
    def analyze_trajectories(self) -> Dict:
        """分析虫子轨迹特征"""
        alive_worms = [w for w in self.worms if w.is_alive]
        
        if not alive_worms:
            return {}
        
        trajectory_metrics = []
        
        for worm in alive_worms:
            if len(worm.trajectory) < 10:
                continue
            
            traj = np.array(worm.trajectory)
            
            # 轨迹长度
            path_length = np.sum(np.sqrt(np.sum(np.diff(traj, axis=0)**2, axis=1)))
            
            # 位移
            displacement = np.sqrt(np.sum((traj[-1] - traj[0])**2))
            
            # 迂曲度（tortuosity）
            tortuosity = path_length / (displacement + 1e-8)
            
            # 活动范围（bounding box面积）
            bbox_area = (traj[:, 0].max() - traj[:, 0].min()) * (traj[:, 1].max() - traj[:, 1].min())
            
            trajectory_metrics.append({
                'path_length': path_length,
                'displacement': displacement,
                'tortuosity': tortuosity,
                'bbox_area': bbox_area
            })
        
        if not trajectory_metrics:
            return {}
        
        # 聚合统计
        return {
            'mean_path_length': np.mean([m['path_length'] for m in trajectory_metrics]),
            'mean_tortuosity': np.mean([m['tortuosity'] for m in trajectory_metrics]),
            'mean_bbox_area': np.mean([m['bbox_area'] for m in trajectory_metrics]),
            'trajectory_metrics': trajectory_metrics
        }
    
    def detect_emergent_patterns(self) -> Dict:
        """检测涌现模式"""
        patterns = {}
        
        if not self.metrics_history:
            return patterns
        
        recent_metrics = self.metrics_history[-100:] if len(self.metrics_history) > 100 else self.metrics_history
        
        # 1. 检测群体聚集
        avg_clustering = np.mean([m.clustering_coefficient for m in recent_metrics])
        if avg_clustering > 0.3:
            patterns['swarming'] = {
                'confidence': avg_clustering,
                'description': '群体表现出明显的聚集行为'
            }
        
        # 2. 检测信息素路径
        avg_trail = np.mean([m.trail_strength for m in recent_metrics])
        if avg_trail > 0.5:
            patterns['trail_following'] = {
                'confidence': avg_trail,
                'description': '形成信息素路径（类似蚂蚁）'
            }
        
        # 3. 检测行为同步
        avg_sync = np.mean([m.behavior_sync_index for m in recent_metrics])
        if avg_sync > 0.6:
            patterns['behavior_synchronization'] = {
                'confidence': avg_sync,
                'description': '群体行为呈现同步性'
            }
        
        # 4. 检测领域行为
        alive_worms = [w for w in self.worms if w.is_alive]
        if alive_worms:
            worms_with_territory = sum(1 for w in alive_worms if w.state.territory_center is not None)
            if worms_with_territory / len(alive_worms) > 0.3:
                patterns['territoriality'] = {
                    'confidence': worms_with_territory / len(alive_worms),
                    'description': '部分虫子表现出领域行为'
                }
        
        # 5. 检测合作行为
        avg_network_density = np.mean([m.network_density for m in recent_metrics])
        if avg_network_density > 0.2:
            patterns['social_cohesion'] = {
                'confidence': avg_network_density,
                'description': '存在社交网络结构'
            }
        
        return patterns
    
    def compare_to_biology(self) -> Dict:
        """与真实生物群体对比"""
        comparison = {
            'similarities': [],
            'differences': [],
            'metrics': {}
        }
        
        alive_worms = [w for w in self.worms if w.is_alive]
        if len(alive_worms) < 3:
            return comparison
        
        # 计算最近邻距离分布（与鱼群/鸟群对比）
        positions = np.array([[w.x, w.y] for w in alive_worms])
        distances = squareform(pdist(positions))
        np.fill_diagonal(distances, np.inf)
        nearest_neighbors = np.min(distances, axis=1)
        
        nn_mean = np.mean(nearest_neighbors)
        nn_std = np.std(nearest_neighbors)
        nn_cv = nn_std / (nn_mean + 1e-8)  # 变异系数
        
        comparison['metrics']['nearest_neighbor_cv'] = nn_cv
        comparison['metrics']['nearest_neighbor_mean'] = nn_mean
        
        # 与生物群体对比（近似值）
        # 鱼群: CV ~ 0.3-0.5
        # 鸟群: CV ~ 0.4-0.6
        # 随机分布: CV ~ 1.0
        if nn_cv < 0.6:
            comparison['similarities'].append({
                'trait': 'ordered_spacing',
                'description': f'间距有序（CV={nn_cv:.2f}），类似鱼群/鸟群'
            })
        else:
            comparison['differences'].append({
                'trait': 'disordered_spacing',
                'description': f'间距较无序（CV={nn_cv:.2f}），缺乏集体协调'
            })
        
        # 聚类分析
        if self.metrics_history:
            avg_n_clusters = np.mean([m.n_clusters for m in self.metrics_history[-50:]])
            comparison['metrics']['avg_n_clusters'] = avg_n_clusters
            
            if avg_n_clusters < len(alive_worms) / 5:
                comparison['similarities'].append({
                    'trait': 'clustering',
                    'description': f'形成大群体（{avg_n_clusters:.1f}个集群）'
                })
        
        return comparison
    
    def generate_report(self) -> str:
        """生成分析报告"""
        report = []
        report.append("=" * 70)
        report.append("涌现行为分析报告")
        report.append("=" * 70)
        
        # 基础统计
        alive_worms = [w for w in self.worms if w.is_alive]
        report.append(f"\n当前种群规模: {len(alive_worms)}")
        report.append(f"总出生数: {self.sim.birth_count}")
        report.append(f"总死亡数: {self.sim.death_count}")
        
        # 最新指标
        if self.metrics_history:
            latest = self.metrics_history[-1]
            report.append(f"\n最新涌现指标:")
            report.append(f"  聚类系数: {latest.clustering_coefficient:.3f}")
            report.append(f"  集群数量: {latest.n_clusters}")
            report.append(f"  空间熵: {latest.spatial_entropy:.3f}")
            report.append(f"  行为熵: {latest.behavior_entropy:.3f}")
            report.append(f"  主导行为: {latest.dominant_behavior}")
            report.append(f"  网络密度: {latest.network_density:.3f}")
            report.append(f"  信息素浓度: {latest.pheromone_concentration:.2f}")
        
        # 轨迹分析
        traj_analysis = self.analyze_trajectories()
        if traj_analysis:
            report.append(f"\n轨迹特征:")
            report.append(f"  平均路径长度: {traj_analysis['mean_path_length']:.1f}")
            report.append(f"  平均迂曲度: {traj_analysis['mean_tortuosity']:.3f}")
            report.append(f"  平均活动范围: {traj_analysis['mean_bbox_area']:.1f}")
        
        # 涌现模式
        patterns = self.detect_emergent_patterns()
        if patterns:
            report.append(f"\n检测到的涌现模式:")
            for pattern_name, pattern_info in patterns.items():
                report.append(f"  {pattern_name}: {pattern_info['description']}")
                report.append(f"    置信度: {pattern_info['confidence']:.3f}")
        
        # 生物对比
        comparison = self.compare_to_biology()
        if comparison['similarities']:
            report.append(f"\n与生物群体的相似性:")
            for sim in comparison['similarities']:
                report.append(f"  - {sim['description']}")
        
        report.append("\n" + "=" * 70)
        
        return "\n".join(report)


# 测试代码
if __name__ == "__main__":
    print("=" * 70)
    print("涌现行为分析测试")
    print("=" * 70)
    
    # 需要先有仿真结果才能测试
    print("\n此模块需要在群体仿真完成后进行分析")
    print("请运行 population_sim.py 生成仿真数据")
    print("\n使用示例:")
    print("  from population_sim import PopulationSimulation")
    print("  from emergence_analysis import EmergenceAnalyzer")
    print("  ")
    print("  sim = PopulationSimulation(n_initial_worms=10)")
    print("  results = sim.run(n_steps=500)")
    print("  ")
    print("  analyzer = EmergenceAnalyzer(sim)")
    print("  for step in range(500):")
    print("      metrics = analyzer.analyze_step(step)")
    print("  ")
    print("  report = analyzer.generate_report()")
    print("  print(report)")
