"""
超级TNN生态系统
大规模群体智能仿真实验

模块:
- super_tnn_worm: 超级虫子核心 (~140万参数)
- ecosystem_env: 复杂生态环境
- population_sim: 群体仿真
- emergence_analysis: 涌现行为分析
- visualize_ecosystem: 可视化工具
- run_experiment: 主运行脚本

使用:
    from super_ecosystem import PopulationSimulation, EmergenceAnalyzer, EcosystemVisualizer
    
    # 运行仿真
    sim = PopulationSimulation(n_initial_worms=20)
    results = sim.run(n_steps=1000)
    
    # 分析涌现
    analyzer = EmergenceAnalyzer(sim)
    
    # 可视化
    visualizer = EcosystemVisualizer(sim)
    visualizer.generate_all_visualizations(analyzer)
"""

__version__ = "1.0.0"
__author__ = "TNN Research"

from .super_tnn_worm import SuperTNNCore, WormState, WormMemory
from .ecosystem_env import SuperEcosystem, FoodSource, WaterSource, Pheromone
from .population_sim import PopulationSimulation, SuperWormAgent, WormConfig
from .emergence_analysis import EmergenceAnalyzer, EmergenceMetrics
from .visualize_ecosystem import EcosystemVisualizer

__all__ = [
    'SuperTNNCore',
    'WormState',
    'WormMemory',
    'SuperEcosystem',
    'FoodSource',
    'WaterSource',
    'Pheromone',
    'PopulationSimulation',
    'SuperWormAgent',
    'WormConfig',
    'EmergenceAnalyzer',
    'EmergenceMetrics',
    'EcosystemVisualizer',
]
