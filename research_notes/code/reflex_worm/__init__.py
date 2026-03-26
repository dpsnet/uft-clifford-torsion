"""
微型TNN"反射虫"实验包

验证"结构即行为"假说：不同的TNN拓扑结构产生不同的先天反射行为
"""

from .environment import Environment2D, LightSource, Obstacle
from .tnn_worm import TNNWorm, TNNWormCore, SpectralDimension, MiniTorsionField
from .behaviors import (
    create_phototaxis_worm,
    create_photophobia_worm,
    create_thigmotaxis_worm,
    create_exploration_worm,
    create_homeostasis_worm,
    create_worm_by_behavior,
    get_behavior_info,
    compare_torsion_fields,
    BEHAVIOR_PRESETS
)
from .simulation import ReflexWormExperiment, ExperimentConfig, run_quick_demo, run_full_experiment
from .visualize import (
    plot_single_trajectory,
    plot_multiple_trajectories,
    plot_behavior_statistics,
    plot_spectral_evolution,
    create_behavior_metrics_table,
    generate_all_visualizations
)

__version__ = '1.0.0'
__author__ = 'TNN Research Team'

__all__ = [
    # 环境
    'Environment2D', 'LightSource', 'Obstacle',
    # TNN核心
    'TNNWorm', 'TNNWormCore', 'SpectralDimension', 'MiniTorsionField',
    # 行为预设
    'create_phototaxis_worm', 'create_photophobia_worm',
    'create_thigmotaxis_worm', 'create_exploration_worm',
    'create_homeostasis_worm', 'create_worm_by_behavior',
    'get_behavior_info', 'compare_torsion_fields', 'BEHAVIOR_PRESETS',
    # 仿真
    'ReflexWormExperiment', 'ExperimentConfig',
    'run_quick_demo', 'run_full_experiment',
    # 可视化
    'plot_single_trajectory', 'plot_multiple_trajectories',
    'plot_behavior_statistics', 'plot_spectral_evolution',
    'create_behavior_metrics_table', 'generate_all_visualizations'
]
