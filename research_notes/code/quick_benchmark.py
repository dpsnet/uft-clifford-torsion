"""
TNN快速基准测试 - 生成研究报告数据
简化版本用于快速验证
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.utils.data import DataLoader
import torchvision
import torchvision.transforms as transforms
import numpy as np
import json
import time
import sys
import os

sys.path.append('/root/.openclaw/workspace/research_notes/code')
from tnn_implementation import (
    TorsionNeuralNetwork, AdaptiveDepthTNN, TNNForImageClassification,
    StandardMLP, StandardCNN, train_epoch, evaluate
)

def quick_mnist_test(epochs=5):
    """快速MNIST测试"""
    print("="*60)
    print("MNIST快速测试 (5 epochs)")
    print("="*60)
    
    device = 'cpu'  # 使用CPU确保稳定
    
    # 数据
    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.1307,), (0.3081,))
    ])
    
    train_dataset = torchvision.datasets.MNIST('./data', train=True, download=True, transform=transform)
    test_dataset = torchvision.datasets.MNIST('./data', train=False, download=True, transform=transform)
    
    # 使用子集加速
    train_subset = torch.utils.data.Subset(train_dataset, range(10000))
    test_subset = torch.utils.data.Subset(test_dataset, range(2000))
    
    train_loader = DataLoader(train_subset, batch_size=128, shuffle=True)
    test_loader = DataLoader(test_subset, batch_size=128, shuffle=False)
    
    criterion = nn.CrossEntropyLoss()
    results = {}
    
    # MLP基线
    print("\n[1/3] MLP基线...")
    mlp = StandardMLP(784, [128, 128], 10).to(device)
    optimizer = optim.Adam(mlp.parameters(), lr=0.001)
    
    mlp_history = {'train_acc': [], 'test_acc': []}
    start = time.time()
    
    for epoch in range(epochs):
        # 训练
        mlp.train()
        train_correct = 0
        train_total = 0
        train_loss_sum = 0
        for data, target in train_loader:
            data, target = data.to(device), target.to(device)
            data = data.view(data.size(0), -1)  # 展平
            optimizer.zero_grad()
            output = mlp(data)
            loss = criterion(output, target)
            loss.backward()
            optimizer.step()
            
            train_loss_sum += loss.item()
            pred = output.argmax(dim=1)
            train_correct += pred.eq(target).sum().item()
            train_total += target.size(0)
        
        train_acc = 100. * train_correct / train_total
        
        # 测试
        mlp.eval()
        test_correct = 0
        test_total = 0
        with torch.no_grad():
            for data, target in test_loader:
                data, target = data.to(device), target.to(device)
                data = data.view(data.size(0), -1)  # 展平
                output = mlp(data)
                pred = output.argmax(dim=1)
                test_correct += pred.eq(target).sum().item()
                test_total += target.size(0)
        
        test_acc = 100. * test_correct / test_total
        
        mlp_history['train_acc'].append(train_acc)
        mlp_history['test_acc'].append(test_acc)
        print(f"  Epoch {epoch+1}: Train={train_acc:.1f}%, Test={test_acc:.1f}%")
    
    results['MLP'] = {
        'final_test_acc': mlp_history['test_acc'][-1],
        'training_time': time.time() - start,
        'params': sum(p.numel() for p in mlp.parameters()),
        'history': mlp_history
    }
    
    # TNN
    print("\n[2/3] TNN...")
    tnn = TorsionNeuralNetwork(784, 10, [128, 128], internal_dim=32, device=device).to(device)
    optimizer = optim.Adam(tnn.parameters(), lr=0.001)
    
    tnn_history = {'train_acc': [], 'test_acc': [], 'spectral_dim': []}
    start = time.time()
    
    for epoch in range(epochs):
        # 训练
        tnn.train()
        train_correct = 0
        train_total = 0
        train_loss_sum = 0
        for data, target in train_loader:
            data, target = data.to(device), target.to(device)
            data = data.view(data.size(0), -1)
            optimizer.zero_grad()
            output = tnn(data)
            loss = criterion(output, target)
            
            # 添加扭转场正则化
            if hasattr(tnn, 'get_regularization_loss'):
                reg_loss = tnn.get_regularization_loss()
                loss = loss + 0.001 * reg_loss
            
            loss.backward()
            optimizer.step()
            
            train_loss_sum += loss.item()
            pred = output.argmax(dim=1)
            train_correct += pred.eq(target).sum().item()
            train_total += target.size(0)
        
        train_acc = 100. * train_correct / train_total
        
        # 测试
        tnn.eval()
        test_correct = 0
        test_total = 0
        with torch.no_grad():
            for data, target in test_loader:
                data, target = data.to(device), target.to(device)
                data = data.view(data.size(0), -1)
                output = tnn(data)
                pred = output.argmax(dim=1)
                test_correct += pred.eq(target).sum().item()
                test_total += target.size(0)
        
        test_acc = 100. * test_correct / test_total
        
        tnn_history['train_acc'].append(train_acc)
        tnn_history['test_acc'].append(test_acc)
        tnn_history['spectral_dim'].append(tnn.get_spectral_dimension())
        print(f"  Epoch {epoch+1}: Train={train_acc:.1f}%, Test={test_acc:.1f}%, d_s={tnn.get_spectral_dimension():.2f}")
    
    results['TNN'] = {
        'final_test_acc': tnn_history['test_acc'][-1],
        'training_time': time.time() - start,
        'params': sum(p.numel() for p in tnn.parameters()),
        'history': tnn_history
    }
    
    # Adaptive-TNN
    print("\n[3/3] Adaptive-TNN...")
    atnn = AdaptiveDepthTNN(784, 10, base_depth=4, base_width=128, device=device).to(device)
    optimizer = optim.Adam(atnn.parameters(), lr=0.001)
    
    atnn_history = {'train_acc': [], 'test_acc': [], 'spectral_dim': []}
    start = time.time()
    
    for epoch in range(epochs):
        # 训练
        atnn.train()
        train_correct = 0
        train_total = 0
        train_loss_sum = 0
        for data, target in train_loader:
            data, target = data.to(device), target.to(device)
            data = data.view(data.size(0), -1)
            optimizer.zero_grad()
            output = atnn(data)
            loss = criterion(output, target)
            loss.backward()
            optimizer.step()
            
            train_loss_sum += loss.item()
            pred = output.argmax(dim=1)
            train_correct += pred.eq(target).sum().item()
            train_total += target.size(0)
        
        train_acc = 100. * train_correct / train_total
        
        # 测试
        atnn.eval()
        test_correct = 0
        test_total = 0
        with torch.no_grad():
            for data, target in test_loader:
                data, target = data.to(device), target.to(device)
                data = data.view(data.size(0), -1)
                output = atnn(data)
                pred = output.argmax(dim=1)
                test_correct += pred.eq(target).sum().item()
                test_total += target.size(0)
        
        test_acc = 100. * test_correct / test_total
        
        atnn_history['train_acc'].append(train_acc)
        atnn_history['test_acc'].append(test_acc)
        atnn_history['spectral_dim'].append(atnn.get_spectral_dimension())
        print(f"  Epoch {epoch+1}: Train={train_acc:.1f}%, Test={test_acc:.1f}%, d_s={atnn.get_spectral_dimension():.2f}")
    
    results['Adaptive-TNN'] = {
        'final_test_acc': atnn_history['test_acc'][-1],
        'training_time': time.time() - start,
        'params': sum(p.numel() for p in atnn.parameters()),
        'history': atnn_history
    }
    
    return results

def quick_cifar_test(epochs=10):
    """快速CIFAR-10测试"""
    print("\n" + "="*60)
    print("CIFAR-10快速测试 (10 epochs)")
    print("="*60)
    
    device = 'cpu'
    
    transform_train = transforms.Compose([
        transforms.RandomCrop(32, padding=4),
        transforms.RandomHorizontalFlip(),
        transforms.ToTensor(),
        transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010)),
    ])
    
    transform_test = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010)),
    ])
    
    train_dataset = torchvision.datasets.CIFAR10('./data', train=True, download=True, transform=transform_train)
    test_dataset = torchvision.datasets.CIFAR10('./data', train=False, download=True, transform=transform_test)
    
    # 子集
    train_subset = torch.utils.data.Subset(train_dataset, range(5000))
    test_subset = torch.utils.data.Subset(test_dataset, range(1000))
    
    train_loader = DataLoader(train_subset, batch_size=128, shuffle=True)
    test_loader = DataLoader(test_subset, batch_size=128, shuffle=False)
    
    criterion = nn.CrossEntropyLoss()
    results = {}
    
    # CNN基线
    print("\n[1/2] CNN基线...")
    cnn = StandardCNN(num_classes=10, in_channels=3).to(device)
    optimizer = optim.Adam(cnn.parameters(), lr=0.001)
    
    cnn_history = {'train_acc': [], 'test_acc': []}
    start = time.time()
    
    for epoch in range(epochs):
        train_stats = train_epoch(cnn, train_loader, optimizer, criterion, device, False)
        test_stats = evaluate(cnn, test_loader, criterion, device)
        cnn_history['train_acc'].append(train_stats['accuracy'])
        cnn_history['test_acc'].append(test_stats['accuracy'])
        if (epoch + 1) % 2 == 0:
            print(f"  Epoch {epoch+1}: Train={train_stats['accuracy']:.1f}%, Test={test_stats['accuracy']:.1f}%")
    
    results['CNN'] = {
        'final_test_acc': cnn_history['test_acc'][-1],
        'training_time': time.time() - start,
        'params': sum(p.numel() for p in cnn.parameters()),
        'history': cnn_history
    }
    
    # TNN-CNN
    print("\n[2/2] TNN-CNN...")
    tnn_cnn = TNNForImageClassification(num_classes=10, in_channels=3, device=device).to(device)
    optimizer = optim.Adam(tnn_cnn.parameters(), lr=0.001)
    
    tnn_cnn_history = {'train_acc': [], 'test_acc': []}
    start = time.time()
    
    for epoch in range(epochs):
        train_stats = train_epoch(tnn_cnn, train_loader, optimizer, criterion, device, True)
        test_stats = evaluate(tnn_cnn, test_loader, criterion, device)
        tnn_cnn_history['train_acc'].append(train_stats['accuracy'])
        tnn_cnn_history['test_acc'].append(test_stats['accuracy'])
        if (epoch + 1) % 2 == 0:
            print(f"  Epoch {epoch+1}: Train={train_stats['accuracy']:.1f}%, Test={test_stats['accuracy']:.1f}%")
    
    results['TNN-CNN'] = {
        'final_test_acc': tnn_cnn_history['test_acc'][-1],
        'training_time': time.time() - start,
        'params': sum(p.numel() for p in tnn_cnn.parameters()),
        'history': tnn_cnn_history
    }
    
    return results

if __name__ == "__main__":
    # 创建结果目录
    os.makedirs('./results', exist_ok=True)
    
    # 运行实验
    mnist_results = quick_mnist_test(epochs=5)
    cifar_results = quick_cifar_test(epochs=10)
    
    # 保存结果
    summary = {
        'mnist': {
            name: {
                'final_test_acc': data['final_test_acc'],
                'training_time': data['training_time'],
                'params': data['params']
            }
            for name, data in mnist_results.items()
        },
        'cifar10': {
            name: {
                'final_test_acc': data['final_test_acc'],
                'training_time': data['training_time'],
                'params': data['params']
            }
            for name, data in cifar_results.items()
        }
    }
    
    with open('./results/quick_benchmark_results.json', 'w') as f:
        json.dump(summary, f, indent=2)
    
    print("\n" + "="*60)
    print("实验完成! 结果保存至 results/quick_benchmark_results.json")
    print("="*60)
    
    # 打印对比表
    print("\n【MNIST结果】")
    for name, data in mnist_results.items():
        print(f"  {name}: Acc={data['final_test_acc']:.2f}%, Time={data['training_time']:.1f}s, Params={data['params']/1e6:.3f}M")
    
    print("\n【CIFAR-10结果】")
    for name, data in cifar_results.items():
        print(f"  {name}: Acc={data['final_test_acc']:.2f}%, Time={data['training_time']:.1f}s, Params={data['params']/1e6:.3f}M")
