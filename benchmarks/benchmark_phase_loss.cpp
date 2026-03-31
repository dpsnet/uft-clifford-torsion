/**
 * @file benchmark_phase_loss.cpp
 * @brief Performance benchmarks for Phase-Aware Loss module
 */

#include <core/phase_aware_loss.h>
#include <torch/torch.h>
#include <iostream>
#include <chrono>
#include <vector>
#include <math>

using namespace uft;
using namespace std::chrono;

// Benchmark timing helper
class Timer {
    high_resolution_clock::time_point start_;
    std::string name_;
public:
    explicit Timer(const std::string& name) : name_(name) {
        start_ = high_resolution_clock::now();
    }
    
    ~Timer() {
        auto end = high_resolution_clock::now();
        auto duration = duration_cast<microseconds>(end - start_).count();
        std::cout << "  " << name_ << ": " << duration << " μs" << std::endl;
    }
};

// Benchmark 1: Torsion regularization performance
void benchmark_torsion_regularization() {
    std::cout << "\nBenchmark 1: Torsion Regularization" << std::endl;
    
    PhaseLossConfig config;
    config.torsion_coef = 0.001f;
    config.torsion_min_energy = 1.0f;
    config.torsion_target = 3.0f;
    
    const int num_layers = 12;
    PhaseAwareLoss loss_module(config, num_layers);
    
    // Prepare data
    std::vector<torch::Tensor> torsion_energies;
    for (int i = 0; i < num_layers; ++i) {
        torsion_energies.push_back(torch::tensor(2.0f + i * 0.1f));
    }
    
    float avg_energy = 0.0f;
    
    // Warmup
    for (int i = 0; i < 10; ++i) {
        loss_module.compute_torsion_regularization(torsion_energies, avg_energy);
    }
    
    // Benchmark
    {
        Timer timer("Compute torsion regularization (12 layers)");
        for (int i = 0; i < 1000; ++i) {
            loss_module.compute_torsion_regularization(torsion_energies, avg_energy);
        }
    }
}

// Benchmark 2: Adaptive torsion loss
void benchmark_adaptive_torsion() {
    std::cout << "\nBenchmark 2: Adaptive Torsion Loss" << std::endl;
    
    PhaseLossConfig config;
    config.torsion_coef = -1.0f;  // Adaptive mode
    
    const int num_layers = 24;
    PhaseAwareLoss loss_module(config, num_layers);
    
    std::vector<torch::Tensor> torsion_energies;
    for (int i = 0; i < num_layers; ++i) {
        torsion_energies.push_back(torch::tensor(1.0f + i * 0.05f));
    }
    
    float avg_energy = 0.0f;
    
    // Warmup
    for (int i = 0; i < 10; ++i) {
        loss_module.compute_adaptive_torsion_loss(torsion_energies, avg_energy);
    }
    
    {
        Timer timer("Compute adaptive torsion (24 layers)");
        for (int i = 0; i < 1000; ++i) {
            loss_module.compute_adaptive_torsion_loss(torsion_energies, avg_energy);
        }
    }
}

// Benchmark 3: Entropy computation
void benchmark_entropy_loss() {
    std::cout << "\nBenchmark 3: Entropy Computation" << std::endl;
    
    PhaseLossConfig config;
    config.entropy_reg = 0.01f;
    
    PhaseAwareLoss loss_module(config, 4);
    
    // Different vocab sizes
    std::vector<int> vocab_sizes = {1000, 10000, 50000};
    
    for (int vocab_size : vocab_sizes) {
        torch::Tensor logits = torch::randn({8, 128, vocab_size});
        
        // Warmup
        for (int i = 0; i < 5; ++i) {
            loss_module.compute_entropy_loss(logits);
        }
        
        {
            Timer timer("Entropy loss (vocab=" + std::to_string(vocab_size) + ")");
            for (int i = 0; i < 100; ++i) {
                loss_module.compute_entropy_loss(logits);
            }
        }
    }
}

// Benchmark 4: Complete loss computation
void benchmark_complete_loss() {
    std::cout << "\nBenchmark 4: Complete Loss Integration" << std::endl;
    
    PhaseLossConfig config;
    config.torsion_coef = 0.001f;
    config.spectral_reg = 0.01f;
    config.entropy_reg = 0.01f;
    
    const int num_layers = 12;
    PhaseAwareLoss loss_module(config, num_layers);
    
    // Setup data
    torch::Tensor base_loss = torch::tensor(2.5f);
    
    std::vector<torch::Tensor> torsion_energies;
    for (int i = 0; i < num_layers; ++i) {
        torsion_energies.push_back(torch::tensor(2.0f + i * 0.1f));
    }
    
    torch::Tensor logits = torch::randn({4, 64, 10000});
    
    // Warmup
    for (int i = 0; i < 10; ++i) {
        loss_module.compute_loss(base_loss, torsion_energies, logits, 4.0f, 0);
    }
    
    {
        Timer timer("Complete loss computation");
        for (int i = 0; i < 100; ++i) {
            loss_module.compute_loss(base_loss, torsion_energies, logits, 4.0f, i);
        }
    }
}

// Benchmark 5: Capacity loss
void benchmark_capacity_loss() {
    std::cout << "\nBenchmark 5: Capacity Loss" << std::endl;
    
    PhaseLossConfig config;
    PhaseAwareLoss loss_module(config, 4);
    
    // Different hidden dimensions
    std::vector<int> hidden_dims = {256, 512, 768, 1024};
    
    for (int hidden_dim : hidden_dims) {
        torch::Tensor hidden = torch::randn({4, 64, hidden_dim});
        
        // Warmup
        for (int i = 0; i < 5; ++i) {
            loss_module.compute_capacity_loss(hidden, 0.8f);
        }
        
        {
            Timer timer("Capacity loss (hidden=" + std::to_string(hidden_dim) + ")");
            for (int i = 0; i < 100; ++i) {
                loss_module.compute_capacity_loss(hidden, 0.8f);
            }
        }
    }
}

// Benchmark 6: Spectral loss
void benchmark_spectral_loss() {
    std::cout << "\nBenchmark 6: Spectral Loss" << std::endl;
    
    PhaseLossConfig config;
    config.spectral_reg = 0.01f;
    
    PhaseAwareLoss loss_module(config, 4);
    
    // Warmup
    for (int i = 0; i < 100; ++i) {
        loss_module.compute_spectral_loss(4.0f);
    }
    
    {
        Timer timer("Spectral loss (1000 iterations)");
        for (int i = 0; i < 1000; ++i) {
            loss_module.compute_spectral_loss(2.0f + (i % 10) * 0.5f);
        }
    }
}

// Benchmark 7: Phase consistency loss
void benchmark_phase_consistency() {
    std::cout << "\nBenchmark 7: Phase Consistency Loss" << std::endl;
    
    PhaseLossConfig config;
    PhaseAwareLoss loss_module(config, 8);
    
    // Prepare phase tensors
    std::vector<torch::Tensor> phase_tensors;
    for (int i = 0; i < 8; ++i) {
        phase_tensors.push_back(torch::randn({64, 64}));
    }
    
    // Warmup
    for (int i = 0; i < 5; ++i) {
        loss_module.compute_phase_consistency_loss(phase_tensors);
    }
    
    {
        Timer timer("Phase consistency (8 layers, 64x64)");
        for (int i = 0; i < 100; ++i) {
            loss_module.compute_phase_consistency_loss(phase_tensors);
        }
    }
}

// Benchmark 8: Memory overhead
void benchmark_memory_overhead() {
    std::cout << "\nBenchmark 8: Memory Overhead" << std::endl;
    
    PhaseLossConfig config;
    config.torsion_coef = 0.001f;
    config.spectral_reg = 0.01f;
    config.entropy_reg = 0.01f;
    
    // Measure memory with different layer counts
    std::vector<int> layer_counts = {4, 8, 12, 24, 48};
    
    for (int num_layers : layer_counts) {
        auto start = high_resolution_clock::now();
        
        PhaseAwareLoss* loss_module = new PhaseAwareLoss(config, num_layers);
        
        auto end = high_resolution_clock::now();
        auto duration = duration_cast<microseconds>(end - start).count();
        
        std::cout << "  Layers=" << num_layers 
                  << ": init time=" << duration << " μs" << std::endl;
        
        delete loss_module;
    }
}

// Summary of all features
void print_feature_summary() {
    std::cout << "\n========================================" << std::endl;
    std::cout << "Phase-Aware Loss Module Features" << std::endl;
    std::cout << "========================================" << std::endl;
    std::cout << "1. Torsion Field Energy Regularization" << std::endl;
    std::cout << "   - Base regularization: coef * total_energy" << std::endl;
    std::cout << "   - Min energy constraint: 0.1 * relu(min - energy)^2" << std::endl;
    std::cout << "   - Target energy constraint: 0.01 * (energy - target)^2" << std::endl;
    std::cout << std::endl;
    std::cout << "2. Adaptive Regularization" << std::endl;
    std::cout << "   - Energy < 1.0: coef = 0.01 * (1.0 - energy)" << std::endl;
    std::cout << "   - Energy > 10.0: coef = 0.001" << std::endl;
    std::cout << "   - 1.0 <= energy <= 10.0: coef = 0.0001" << std::endl;
    std::cout << std::endl;
    std::cout << "3. Spectral Dimension Constraint" << std::endl;
    std::cout << "   - Target range: [3.0, 6.0]" << std::endl;
    std::cout << "   - Penalty: relu(3 - d_s) + relu(d_s - 6)" << std::endl;
    std::cout << std::endl;
    std::cout << "4. Entropy Regularization (Diversity)" << std::endl;
    std::cout << "   - Maximizes output distribution entropy" << std::endl;
    std::cout << "   - Loss = -entropy_reg * mean_entropy" << std::endl;
    std::cout << std::endl;
    std::cout << "5. Phase Consistency Loss" << std::endl;
    std::cout << "   - Encourages phase coherence across layers" << std::endl;
    std::cout << "   - Variance-based penalty" << std::endl;
    std::cout << std::endl;
    std::cout << "6. Capacity Maximization" << std::endl;
    std::cout << "   - Effective rank approximation" << std::endl;
    std::cout << "   - Variance-based capacity metric" << std::endl;
    std::cout << "========================================" << std::endl;
}

int main() {
    std::cout << "========================================" << std::endl;
    std::cout << "Phase-Aware Loss Module Benchmarks" << std::endl;
    std::cout << "========================================" << std::endl;
    
    print_feature_summary();
    
    std::cout << "\nStarting benchmarks..." << std::endl;
    
    // Run all benchmarks
    benchmark_torsion_regularization();
    benchmark_adaptive_torsion();
    benchmark_spectral_loss();
    benchmark_entropy_loss();
    benchmark_phase_consistency();
    benchmark_capacity_loss();
    benchmark_complete_loss();
    benchmark_memory_overhead();
    
    std::cout << "\n========================================" << std::endl;
    std::cout << "Benchmarks completed!" << std::endl;
    std::cout << "========================================" << std::endl;
    
    return 0;
}
