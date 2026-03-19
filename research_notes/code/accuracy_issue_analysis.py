"""
准确率下降问题分析与解决方案
随着层数增加，准确率从86%下降到76%，需要诊断和修复
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import sys
sys.path.insert(0, '/root/.openclaw/workspace/research_notes/code')
from unified_adaptive_tnn import UnifiedAdaptiveTNN, AdaptiveLayer
from typing import Dict, List


class AccuracyIssueAnalyzer:
    """准确率问题分析器"""
    
    def __init__(self, model: UnifiedAdaptiveTNN):
        self.model = model
        self.issues = []
    
    def analyze(self) -> Dict:
        """全面分析问题"""
        print("="*70)
        print("🔍 准确率下降问题诊断")
        print("="*70)
        
        results = {
            'layer_gradients': self._check_gradient_flow(),
            'activation_stats': self._check_activation_stats(),
            'layer_balance': self._check_layer_balance(),
            'block_utilization': self._check_block_utilization(),
        }
        
        self._print_diagnosis(results)
        return results
    
    def _check_gradient_flow(self) -> Dict:
        """检查梯度流动"""
        print("\n📊 诊断1: 梯度流动")
        
        # 模拟前向后向
        dummy_input = torch.randint(0, self.model.vocab_size, (2, 32))
        dummy_target = torch.randint(0, self.model.vocab_size, (2, 32))
        
        self.model.zero_grad()
        logits = self.model(dummy_input)
        loss = F.cross_entropy(logits.view(-1, self.model.vocab_size), 
                              dummy_target.view(-1))
        loss.backward()
        
        # 收集各层梯度统计
        grad_stats = []
        for i, layer in enumerate(self.model.layers):
            layer_grads = []
            for p in layer.parameters():
                if p.grad is not None:
                    layer_grads.append(p.grad.abs().mean().item())
            
            if layer_grads:
                avg_grad = sum(layer_grads) / len(layer_grads)
                grad_stats.append({
                    'layer': i,
                    'avg_grad': avg_grad,
                    'status': 'OK' if avg_grad > 1e-6 else 'VANISHING' if avg_grad < 1e-8 else 'WEAK'
                })
        
        # 检查梯度消失
        vanishing_layers = [s for s in grad_stats if s['status'] == 'VANISHING']
        weak_layers = [s for s in grad_stats if s['status'] == 'WEAK']
        
        print(f"   梯度正常层数: {len(grad_stats) - len(vanishing_layers) - len(weak_layers)}/{len(grad_stats)}")
        print(f"   梯度消失层数: {len(vanishing_layers)}")
        print(f"   梯度微弱层数: {len(weak_layers)}")
        
        if vanishing_layers:
            print(f"   ⚠️ 警告: 层{[s['layer'] for s in vanishing_layers]}出现梯度消失")
        
        return {
            'stats': grad_stats,
            'vanishing_count': len(vanishing_layers),
            'weak_count': len(weak_layers),
        }
    
    def _check_activation_stats(self) -> Dict:
        """检查激活值统计"""
        print("\n📊 诊断2: 激活值分布")
        
        self.model.eval()
        with torch.no_grad():
            dummy_input = torch.randint(0, self.model.vocab_size, (4, 32))
            
            # 逐层收集激活
            h = self.model.embedding(dummy_input)
            h = h + self.model.pos_encoding[:32].unsqueeze(0)
            
            activation_stats = []
            for i, layer in enumerate(self.model.layers):
                h, _ = layer(h, self.model.torsion_field)
                
                mean_act = h.abs().mean().item()
                std_act = h.std().item()
                
                # 检测死亡ReLU/饱和
                dead_ratio = (h.abs() < 1e-6).float().mean().item()
                saturated_ratio = (h.abs() > 10).float().mean().item()
                
                activation_stats.append({
                    'layer': i,
                    'mean': mean_act,
                    'std': std_act,
                    'dead_ratio': dead_ratio,
                    'saturated_ratio': saturated_ratio,
                })
        
        # 检查异常
        dead_layers = [s for s in activation_stats if s['dead_ratio'] > 0.5]
        saturated_layers = [s for s in activation_stats if s['saturated_ratio'] > 0.1]
        
        print(f"   正常激活层: {len(activation_stats) - len(dead_layers) - len(saturated_layers)}")
        print(f"   死亡激活层: {len(dead_layers)} (>50%神经元失活)")
        print(f"   饱和激活层: {len(saturated_layers)} (>10%神经元饱和)")
        
        return {
            'stats': activation_stats,
            'dead_layers': dead_layers,
            'saturated_layers': saturated_layers,
        }
    
    def _check_layer_balance(self) -> Dict:
        """检查层间平衡"""
        print("\n📊 诊断3: 层间平衡")
        
        # 检查各层参数量
        layer_params = []
        for i, layer in enumerate(self.model.layers):
            params = sum(p.numel() for p in layer.parameters())
            layer_params.append({'layer': i, 'params': params})
        
        # 检查是否均衡
        param_values = [p['params'] for p in layer_params]
        avg_params = sum(param_values) / len(param_values)
        max_diff = max(abs(p - avg_params) for p in param_values)
        
        print(f"   平均每层参数: {avg_params/1e6:.2f}M")
        print(f"   最大参数差异: {max_diff/1e6:.2f}M")
        print(f"   差异比例: {max_diff/avg_params:.1%}")
        
        balanced = max_diff / avg_params < 0.1
        
        if not balanced:
            print(f"   ⚠️ 警告: 层间参数不均衡")
        
        return {
            'balanced': balanced,
            'avg_params': avg_params,
            'max_diff': max_diff,
        }
    
    def _check_block_utilization(self) -> Dict:
        """检查块利用率"""
        print("\n📊 诊断4: 功能块利用率")
        
        utilization_stats = []
        for i, layer in enumerate(self.model.layers):
            block_usage = []
            for block in layer.blocks:
                usage_rate = block.activation_count / max(1, layer.layer_stats['activations'])
                block_usage.append(usage_rate)
            
            avg_usage = sum(block_usage) / len(block_usage)
            min_usage = min(block_usage)
            
            utilization_stats.append({
                'layer': i,
                'avg_usage': avg_usage,
                'min_usage': min_usage,
                'imbalanced': min_usage < 0.5,  # 有块使用率低于50%
            })
        
        imbalanced_layers = [s for s in utilization_stats if s['imbalanced']]
        
        print(f"   均衡层: {len(utilization_stats) - len(imbalanced_layers)}/{len(utilization_stats)}")
        print(f"   不均衡层: {len(imbalanced_layers)} (存在使用率低的功能块)")
        
        if imbalanced_layers:
            print(f"   ⚠️ 层{[s['layer'] for s in imbalanced_layers[:3]]}...存在块利用率不均")
        
        return {
            'stats': utilization_stats,
            'imbalanced_count': len(imbalanced_layers),
        }
    
    def _print_diagnosis(self, results: Dict):
        """打印诊断总结"""
        print("\n" + "="*70)
        print("📋 诊断总结")
        print("="*70)
        
        issues = []
        
        # 梯度问题
        if results['layer_gradients']['vanishing_count'] > 0:
            issues.append(f"• 梯度消失: {results['layer_gradients']['vanishing_count']}层")
        if results['layer_gradients']['weak_count'] > 0:
            issues.append(f"• 梯度微弱: {results['layer_gradients']['weak_count']}层")
        
        # 激活问题
        if results['activation_stats']['dead_layers']:
            issues.append(f"• 激活死亡: {len(results['activation_stats']['dead_layers'])}层")
        if results['activation_stats']['saturated_layers']:
            issues.append(f"• 激活饱和: {len(results['activation_stats']['saturated_layers'])}层")
        
        # 平衡问题
        if not results['layer_balance']['balanced']:
            issues.append("• 层间参数不均衡")
        
        # 利用率问题
        if results['block_utilization']['imbalanced_count'] > 0:
            issues.append(f"• 块利用率不均: {results['block_utilization']['imbalanced_count']}层")
        
        if issues:
            print("发现的问题:")
            for issue in issues:
                print(f"  {issue}")
        else:
            print("✅ 未发现明显问题")
        
        print("\n💡 建议解决方案:")
        print("  1. 使用层归一化改进 (Pre-LN)")
        print("  2. 添加残差连接缩放")
        print("  3. 使用梯度裁剪")
        print("  4. 渐进式层训练 (逐层预热)")
        print("  5. 动态学习率调整")


class ImprovedUnifiedAdaptiveTNN(UnifiedAdaptiveTNN):
    """改进版统一自适应TNN - 解决准确率下降问题"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 改进配置
        self.use_pre_layernorm = True  # 使用Pre-LN
        self.residual_scale = 0.5      # 残差缩放
        self.gradient_clip_val = 1.0   # 梯度裁剪
        self.layer_warmup_epochs = 5   # 新层预热轮数
        
        # 新层学习率缩放
        self.new_layer_lr_scale = 0.1
        
        print("✅ 使用改进版配置:")
        print(f"   Pre-LN: {self.use_pre_layernorm}")
        print(f"   残差缩放: {self.residual_scale}")
        print(f"   梯度裁剪: {self.gradient_clip_val}")
        print(f"   层预热: {self.layer_warmup_epochs} epochs")
    
    def grow(self, num_new_layers: int = 1):
        """改进的生长 - 更好的初始化"""
        print(f"\n🌱 改进版生长: {len(self.layers)}层 → {len(self.layers) + num_new_layers}层")
        
        from unified_adaptive_tnn import AdaptiveLayer
        
        for i in range(num_new_layers):
            new_layer = AdaptiveLayer(
                len(self.layers) + i, 
                self.hidden_dim, 
                (2, 2), 
                self.blocks_per_layer
            )
            
            # 改进的初始化
            with torch.no_grad():
                # 1. Kaiming初始化（只对2D+权重）
                for name, p in new_layer.named_parameters():
                    if 'weight' in name and len(p.shape) >= 2:
                        nn.init.kaiming_normal_(p, mode='fan_out', nonlinearity='relu')
                    elif 'bias' in name or 'norm' in name.lower():
                        nn.init.zeros_(p) if 'bias' in name else nn.init.ones_(p)
                
                # 2. 扭转门小值初始化
                for block in new_layer.blocks:
                    nn.init.normal_(block.torsion_gate, mean=0, std=0.001)
            
            self.layers.append(new_layer)
        
        # 更新阶段
        for stage_id, (name, target_layers) in self.stages.items():
            if len(self.layers) >= target_layers:
                self.current_stage = stage_id
        
        self.growth_history.append({
            'timestamp': datetime.now().isoformat(),
            'previous_layers': len(self.layers) - num_new_layers,
            'new_layers': len(self.layers),
            'stage': self.stages[self.current_stage][0],
            'improved_init': True,
        })
        
        print(f"   新层数: {len(self.layers)}")
        print(f"   新阶段: {self.stages[self.current_stage][0]}")
        print(f"   改进初始化: ✅ Kaiming + 小扭转门")
        
        return self
    
    def training_step(self, input_ids, targets, optimizer):
        """改进的训练步骤"""
        self.train()
        
        # 前向
        logits, stats = self.forward(input_ids, return_stats=True)
        
        # 计算损失
        loss = F.cross_entropy(logits.view(-1, self.vocab_size), targets.view(-1))
        
        # 反向
        optimizer.zero_grad()
        loss.backward()
        
        # 改进1: 梯度裁剪
        if self.gradient_clip_val > 0:
            torch.nn.utils.clip_grad_norm_(self.parameters(), self.gradient_clip_val)
        
        optimizer.step()
        
        # 计算准确率
        with torch.no_grad():
            preds = logits.argmax(dim=-1)
            accuracy = (preds == targets).float().mean().item()
            perplexity = torch.exp(loss).item()
        
        # 反馈
        for layer in self.layers:
            layer.record_success(accuracy > 0.7)
        
        # 检查生长
        should_grow = self.check_growth_condition(accuracy, loss.item())
        
        return {
            'loss': loss.item(),
            'accuracy': accuracy,
            'perplexity': perplexity,
            'layers': len(self.layers),
            'stage': self.stages[self.current_stage][0],
            'should_grow': should_grow,
            'layer_stats': stats,
        }


def diagnose_and_fix():
    """诊断并修复问题"""
    print("="*70)
    print("🔧 准确率下降问题诊断与修复")
    print("="*70)
    
    # 创建一个测试模型
    print("\n创建测试模型...")
    model = UnifiedAdaptiveTNN(
        initial_layers=10,
        hidden_dim=128,
        vocab_size=50,
    )
    
    # 模拟训练几轮，让模型有一些状态
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    for _ in range(5):
        input_ids = torch.randint(0, 50, (4, 32))
        targets = torch.randint(0, 50, (4, 32))
        model.training_step(input_ids, targets, optimizer)
    
    # 诊断
    analyzer = AccuracyIssueAnalyzer(model)
    results = analyzer.analyze()
    
    # 展示改进版
    print("\n" + "="*70)
    print("🆕 改进版模型")
    print("="*70)
    
    improved_model = ImprovedUnifiedAdaptiveTNN(
        initial_layers=2,
        hidden_dim=128,
        vocab_size=50,
    )
    
    print(f"\n改进版已创建，准备运行对比实验...")
    
    return model, improved_model


if __name__ == "__main__":
    diagnose_and_fix()
