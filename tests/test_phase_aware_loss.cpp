/**
 * @file test_phase_aware_loss.cpp
 * @brief Unit tests for Phase-Aware Loss module
 */

#include <core/phase_aware_loss.h>
#include <torch/torch.h>
#include <iostream>
#include <assert>
#include <math>

using namespace uft;

// Helper function to check if values are close
bool near(float a, float b, float tol = 1e-4f) {
    return std::abs(a - b) < tol;
}

// Test 1: Configuration creation
void test_config() {
    std::cout << "Test 1: Configuration... ";
    
    PhaseLossConfig config;
    config.name = "test_config";
    config.torsion_coef = 0.001f;
    config.torsion_min_energy = 1.0f;
    config.torsion_target = 3.0f;
    config.spectral_reg = 0.01f;
    config.entropy_reg = 0.01f;
    
    assert(config.name == "test_config");
    assert(near(config.torsion_coef, 0.001f));
    assert(near(config.torsion_min_energy, 1.0f));
    assert(near(config.torsion_target, 3.0f));
    assert(!config.is_adaptive());  // Not adaptive since coef > 0
    
    PhaseLossConfig adaptive_config;
    adaptive_config.torsion_coef = -1.0f;
    assert(adaptive_config.is_adaptive());
    
    std::cout << "PASSED" << std::endl;
}

// Test 2: Torsion regularization loss
void test_torsion_regularization() {
    std::cout << "Test 2: Torsion Regularization... ";
    
    PhaseLossConfig config;
    config.torsion_coef = 0.001f;
    config.torsion_min_energy = 0.0f;
    
    PhaseAwareLoss loss_module(config, 4);
    
    // Create mock torsion energies
    std::vector<torch::Tensor> torsion_energies;
    for (int i = 0; i < 4; ++i) {
        torsion_energies.push_back(torch::tensor(2.0f + i * 0.5f));
    }
    
    float avg_energy = 0.0f;
    torch::Tensor loss = loss_module.compute_torsion_regularization(torsion_energies, avg_energy);
    
    // Expected: avg_energy = (2.0 + 2.5 + 3.0 + 3.5) / 4 = 2.75
    assert(near(avg_energy, 2.75f));
    
    // Expected loss = coef * total_energy = 0.001 * 11.0 = 0.011
    float loss_val = loss.item<float>();
    assert(near(loss_val, 0.011f));
    
    std::cout << "PASSED" << std::endl;
}

// Test 3: Min energy constraint
void test_min_energy_constraint() {
    std::cout << "Test 3: Min Energy Constraint... ";
    
    PhaseLossConfig config;
    config.torsion_coef = 0.001f;
    config.torsion_min_energy = 5.0f;  // Require at least 5.0 energy
    
    PhaseAwareLoss loss_module(config, 2);
    
    // Create low energies (should trigger penalty)
    std::vector<torch::Tensor> low_energies;
    low_energies.push_back(torch::tensor(0.5f));
    low_energies.push_back(torch::tensor(0.5f));
    
    float avg_energy = 0.0f;
    torch::Tensor loss = loss_module.compute_torsion_regularization(low_energies, avg_energy);
    
    // Should have min energy penalty: 0.1 * (5.0 - 0.5)^2 = 0.1 * 20.25 = 2.025
    // Plus base: 0.001 * 1.0 = 0.001
    // Total = 2.026
    float loss_val = loss.item<float>();
    assert(loss_val > 2.0f);  // Should be dominated by penalty
    
    std::cout << "PASSED" << std::endl;
}

// Test 4: Target energy constraint
void test_target_energy_constraint() {
    std::cout << "Test 4: Target Energy Constraint... ";
    
    PhaseLossConfig config;
    config.torsion_coef = 0.001f;
    config.torsion_target = 3.0f;  // Target energy of 3.0
    
    PhaseAwareLoss loss_module(config, 2);
    
    // Create energies far from target
    std::vector<torch::Tensor> energies;
    energies.push_back(torch::tensor(1.0f));
    energies.push_back(torch::tensor(1.0f));
    
    float avg_energy = 0.0f;
    torch::Tensor loss = loss_module.compute_torsion_regularization(energies, avg_energy);
    
    // Should have target penalty: 0.01 * (1.0 - 3.0)^2 = 0.04
    float loss_val = loss.item<float>();
    assert(loss_val >= 0.04f);
    
    std::cout << "PASSED" << std::endl;
}

// Test 5: Adaptive torsion loss
void test_adaptive_torsion() {
    std::cout << "Test 5: Adaptive Torsion Loss... ";
    
    PhaseLossConfig config;
    config.torsion_coef = -1.0f;  // Adaptive mode
    
    PhaseAwareLoss loss_module(config, 2);
    
    // Test case 1: Low energy (< 1.0) - high regularization
    std::vector<torch::Tensor> low_energies;
    low_energies.push_back(torch::tensor(0.3f));
    low_energies.push_back(torch::tensor(0.3f));
    
    float avg_energy = 0.0f;
    torch::Tensor loss = loss_module.compute_adaptive_torsion_loss(low_energies, avg_energy);
    
    // Expected: avg = 0.3, coef = 0.01 * (1.0 - 0.3) = 0.007
    // loss = 0.007 * 0.6 = 0.0042
    float loss_val_low = loss.item<float>();
    
    // Test case 2: High energy (> 10.0) - moderate regularization
    std::vector<torch::Tensor> high_energies;
    high_energies.push_back(torch::tensor(6.0f));
    high_energies.push_back(torch::tensor(6.0f));
    
    torch::Tensor loss_high = loss_module.compute_adaptive_torsion_loss(high_energies, avg_energy);
    
    // Energy = 6.0, in sweet spot [1, 10], coef = 0.0001
    // loss = 0.0001 * 12.0 = 0.0012
    float loss_val_high = loss_high.item<float>();
    
    // Low energy should have higher regularization than moderate
    assert(loss_val_low > loss_val_high);
    
    std::cout << "PASSED" << std::endl;
}

// Test 6: Spectral loss
void test_spectral_loss() {
    std::cout << "Test 6: Spectral Loss... ";
    
    PhaseLossConfig config;
    config.spectral_reg = 0.01f;
    
    PhaseAwareLoss loss_module(config, 2);
    
    // Test: d_s = 2.0 (< 3.0, should have penalty)
    torch::Tensor loss_low = loss_module.compute_spectral_loss(2.0f);
    float loss_low_val = loss_low.item<float>();
    // Expected: 0.01 * (3.0 - 2.0)^2 = 0.01
    assert(near(loss_low_val, 0.01f, 1e-3f));
    
    // Test: d_s = 4.0 (in range [3, 6], no penalty)
    torch::Tensor loss_mid = loss_module.compute_spectral_loss(4.0f);
    float loss_mid_val = loss_mid.item<float>();
    assert(near(loss_mid_val, 0.0f, 1e-6f));
    
    // Test: d_s = 7.0 (> 6.0, should have penalty)
    torch::Tensor loss_high = loss_module.compute_spectral_loss(7.0f);
    float loss_high_val = loss_high.item<float>();
    // Expected: 0.01 * (7.0 - 6.0)^2 = 0.01
    assert(near(loss_high_val, 0.01f, 1e-3f));
    
    std::cout << "PASSED" << std::endl;
}

// Test 7: Entropy loss
void test_entropy_loss() {
    std::cout << "Test 7: Entropy Loss... ";
    
    PhaseLossConfig config;
    config.entropy_reg = 0.1f;
    
    PhaseAwareLoss loss_module(config, 2);
    
    // Create logits with high diversity (high entropy)
    // Shape: [batch=2, seq_len=4, vocab_size=8]
    torch::Tensor logits = torch::randn({2, 4, 8});
    
    torch::Tensor loss = loss_module.compute_entropy_loss(logits);
    
    // Entropy loss should be negative (we maximize entropy)
    float loss_val = loss.item<float>();
    assert(loss_val < 0.0f);  // Negative because we want to maximize entropy
    
    std::cout << "PASSED" << std::endl;
}

// Test 8: Complete loss computation
void test_complete_loss() {
    std::cout << "Test 8: Complete Loss Integration... ";
    
    PhaseLossConfig config;
    config.name = "integration_test";
    config.torsion_coef = 0.001f;
    config.spectral_reg = 0.01f;
    config.entropy_reg = 0.01f;
    
    PhaseAwareLoss loss_module(config, 4);
    
    // Base loss
    torch::Tensor base_loss = torch::tensor(2.5f);
    
    // Torsion energies
    std::vector<torch::Tensor> torsion_energies;
    for (int i = 0; i < 4; ++i) {
        torsion_energies.push_back(torch::tensor(2.0f + i * 0.5f));
    }
    
    // Logits
    torch::Tensor logits = torch::randn({2, 4, 100});
    
    // Compute total loss
    torch::Tensor total_loss = loss_module.compute_loss(
        base_loss, torsion_energies, logits, 4.0f, 100
    );
    
    float total_val = total_loss.item<float>();
    
    // Should be base_loss + regularization terms
    // Base is 2.5, so total should be > 2.5
    assert(total_val > 2.5f);
    
    // Check statistics
    LossStatistics stats = loss_module.get_statistics();
    assert(stats.base_loss == 2.5f);
    assert(stats.total_loss == total_val);
    assert(stats.torsion_energy > 0.0f);
    assert(stats.spectral_dimension == 4.0f);
    
    std::cout << "PASSED" << std::endl;
}

// Test 9: Capacity loss
void test_capacity_loss() {
    std::cout << "Test 9: Capacity Loss... ";
    
    PhaseLossConfig config;
    PhaseAwareLoss loss_module(config, 2);
    
    // Create hidden states
    torch::Tensor hidden = torch::randn({2, 4, 64});
    
    torch::Tensor loss = loss_module.compute_capacity_loss(hidden, 0.8f);
    
    // Loss should be non-negative
    float loss_val = loss.item<float>();
    assert(loss_val >= 0.0f);
    
    std::cout << "PASSED" << std::endl;
}

// Test 10: Statistics tracking
void test_statistics() {
    std::cout << "Test 10: Statistics Tracking... ";
    
    PhaseLossConfig config;
    config.torsion_coef = 0.001f;
    
    PhaseAwareLoss loss_module(config, 2);
    
    // Reset and verify
    loss_module.reset_statistics();
    LossStatistics stats = loss_module.get_statistics();
    assert(stats.total_loss == 0.0f);
    assert(stats.base_loss == 0.0f);
    
    // Run a computation and check stats updated
    torch::Tensor base_loss = torch::tensor(1.0f);
    std::vector<torch::Tensor> energies = {torch::tensor(1.0f), torch::tensor(2.0f)};
    torch::Tensor logits = torch::randn({1, 2, 10});
    
    loss_module.compute_loss(base_loss, energies, logits, 4.0f, 0);
    
    stats = loss_module.get_statistics();
    assert(stats.base_loss == 1.0f);
    assert(stats.total_loss > 0.0f);
    assert(stats.torsion_energy > 0.0f);
    
    std::cout << "PASSED" << std::endl;
}

// Main test runner
int main() {
    std::cout << "==============================================" << std::endl;
    std::cout << "Phase-Aware Loss Module Unit Tests" << std::endl;
    std::cout << "==============================================" << std::endl;
    std::cout << std::endl;
    
    try {
        test_config();
        test_torsion_regularization();
        test_min_energy_constraint();
        test_target_energy_constraint();
        test_adaptive_torsion();
        test_spectral_loss();
        test_entropy_loss();
        test_complete_loss();
        test_capacity_loss();
        test_statistics();
        
        std::cout << std::endl;
        std::cout << "==============================================" << std::endl;
        std::cout << "All tests PASSED!" << std::endl;
        std::cout << "==============================================" << std::endl;
        
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "Test FAILED with exception: " << e.what() << std::endl;
        return 1;
    }
}
