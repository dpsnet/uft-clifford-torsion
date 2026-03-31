/**
 * @file phase_aware_loss.cpp
 * @brief C++ implementation of Phase-Aware Loss module
 */

#include "core/phase_aware_loss.h"
#include <aten/ATen.h>
#include <torch/cuda.h>
#include <math>
#include <iostream>

namespace uft {

//=============================================================================
// Constructor / Destructor
//=============================================================================

PhaseAwareLoss::PhaseAwareLoss(const PhaseLossConfig& config, int num_layers, int device)
    : config_(config)
    , num_layers_(num_layers)
    , device_id_(device)
    , adaptive_coef_(0.0001f)
    , energy_ema_(0.0f)
{
    layer_stats_.resize(num_layers);
    reset_statistics();
    init_cuda_resources();
}

PhaseAwareLoss::~PhaseAwareLoss() {
    release_cuda_resources();
}

void PhaseAwareLoss::init_cuda_resources() {
    // Allocate small buffer for intermediate CUDA results
    torsion_buffer_size_ = 128;  // Enough for energy values and scratch space
    cudaMalloc(&d_torsion_buffer_, torsion_buffer_size_ * sizeof(float));
    
    // Create CUDA stream
    cudaStreamCreate(&cuda_stream_);
}

void PhaseAwareLoss::release_cuda_resources() {
    if (d_torsion_buffer_) {
        cudaFree(d_torsion_buffer_);
        d_torsion_buffer_ = nullptr;
    }
    if (cuda_stream_) {
        cudaStreamDestroy(cuda_stream_);
        cuda_stream_ = nullptr;
    }
}

void PhaseAwareLoss::reset_statistics() {
    stats_ = LossStatistics{};
    for (auto& layer_stat : layer_stats_) {
        layer_stat = TorsionLayerStats{};
    }
}

void PhaseAwareLoss::synchronize() const {
    if (cuda_stream_) {
        cudaStreamSynchronize(cuda_stream_);
    }
}

//=============================================================================
// Main Loss Computation
//=============================================================================

torch::Tensor PhaseAwareLoss::compute_loss(
    const torch::Tensor& base_loss,
    const std::vector<torch::Tensor>& torsion_energies,
    const torch::Tensor& logits,
    float current_spectral_dim,
    int64_t step
) {
    // Ensure base_loss requires grad if we need gradients
    torch::Tensor total_loss = base_loss.clone();
    
    // Track individual loss components
    torch::Tensor torsion_loss = torch::zeros_like(base_loss);
    torch::Tensor spectral_loss = torch::zeros_like(base_loss);
    torch::Tensor entropy_loss = torch::zeros_like(base_loss);
    torch::Tensor phase_loss = torch::zeros_like(base_loss);
    
    float avg_torsion_energy = 0.0f;
    
    // 1. Torsion field regularization
    if (config_.is_adaptive()) {
        torsion_loss = compute_adaptive_torsion_loss(torsion_energies, avg_torsion_energy);
    } else if (config_.torsion_coef > 0.0f) {
        torsion_loss = compute_torsion_regularization(torsion_energies, avg_torsion_energy);
    }
    
    // 2. Spectral dimension regularization
    if (config_.spectral_reg > 0.0f) {
        spectral_loss = compute_spectral_loss(current_spectral_dim);
    }
    
    // 3. Entropy regularization
    if (config_.entropy_reg > 0.0f) {
        entropy_loss = compute_entropy_loss(logits);
    }
    
    // Sum all losses
    total_loss = total_loss + torsion_loss + spectral_loss + entropy_loss + phase_loss;
    
    // Update statistics
    update_statistics(
        total_loss.item<float>(),
        base_loss.item<float>(),
        torsion_loss.item<float>(),
        spectral_loss.item<float>(),
        entropy_loss.item<float>(),
        phase_loss.item<float>(),
        avg_torsion_energy,
        current_spectral_dim
    );
    
    return total_loss;
}

//=============================================================================
// Torsion Field Regularization
//=============================================================================

torch::Tensor PhaseAwareLoss::compute_torsion_regularization(
    const std::vector<torch::Tensor>& torsion_energies,
    float& avg_energy
) {
    if (torsion_energies.empty()) {
        avg_energy = 0.0f;
        return torch::zeros({1}, 
            torch::TensorOptions().device(base_loss_device(torsion_energies)));
    }
    
    // Stack all layer energies and compute total
    torch::Tensor stacked = torch::stack(torsion_energies);
    torch::Tensor total_energy = stacked.sum();
    avg_energy = total_energy.item<float>() / num_layers_;
    
    // Base regularization: coef * total_energy
    torch::Tensor loss = config_.torsion_coef * total_energy;
    
    // Minimum energy constraint
    if (config_.torsion_min_energy > 0.0f) {
        float min_energy = config_.torsion_min_energy;
        float penalty_val = std::max(0.0f, min_energy - avg_energy);
        torch::Tensor min_penalty = torch::tensor(
            0.1f * penalty_val * penalty_val,
            torch::TensorOptions().dtype(loss.dtype()).device(loss.device())
        );
        loss = loss + min_penalty;
    }
    
    // Target energy constraint
    if (config_.torsion_target >= 0.0f) {
        float diff = avg_energy - config_.torsion_target;
        torch::Tensor target_penalty = torch::tensor(
            0.01f * diff * diff,
            torch::TensorOptions().dtype(loss.dtype()).device(loss.device())
        );
        loss = loss + target_penalty;
    }
    
    // Update EMA for adaptive mode
    const float alpha = 0.01f;
    energy_ema_ = alpha * avg_energy + (1.0f - alpha) * energy_ema_;
    
    // Update per-layer statistics
    for (int i = 0; i < num_layers_ && i < static_cast<int>(torsion_energies.size()); ++i) {
        layer_stats_[i].energy = torsion_energies[i].item<float>();
    }
    
    return loss;
}

torch::Tensor PhaseAwareLoss::compute_adaptive_torsion_loss(
    const std::vector<torch::Tensor>& torsion_energies,
    float& avg_energy
) {
    if (torsion_energies.empty()) {
        avg_energy = 0.0f;
        return torch::zeros({1},
            torch::TensorOptions().device(base_loss_device(torsion_energies)));
    }
    
    // Compute average energy
    torch::Tensor stacked = torch::stack(torsion_energies);
    torch::Tensor total_energy = stacked.sum();
    avg_energy = total_energy.item<float>() / num_layers_;
    
    // Compute adaptive coefficient based on energy level
    // Ported from Python:
    // if avg_energy < 1.0: coef = 0.01 * (1.0 - avg_energy)
    // elif avg_energy > 10.0: coef = 0.001
    // else: coef = 0.0001
    
    float adaptive_coef;
    if (avg_energy < 1.0f) {
        adaptive_coef = 0.01f * (1.0f - avg_energy);
    } else if (avg_energy > 10.0f) {
        adaptive_coef = 0.001f;
    } else {
        adaptive_coef = 0.0001f;
    }
    
    adaptive_coef_ = adaptive_coef;  // Store for statistics
    
    torch::Tensor loss = adaptive_coef * total_energy;
    
    return loss;
}

//=============================================================================
// Spectral Dimension Regularization
//=============================================================================

torch::Tensor PhaseAwareLoss::compute_spectral_loss(float current_d_s) {
    // Target spectral dimension range: [3.0, 6.0]
    // Penalty = relu(3.0 - d_s) + relu(d_s - 6.0)
    // This encourages spectral dimension to stay in the range [3, 6]
    
    float penalty = 0.0f;
    
    if (current_d_s < 3.0f) {
        float diff = 3.0f - current_d_s;
        penalty = diff * diff;
    } else if (current_d_s > 6.0f) {
        float diff = current_d_s - 6.0f;
        penalty = diff * diff;
    }
    
    torch::Tensor loss = torch::tensor(
        config_.spectral_reg * penalty,
        torch::TensorOptions().dtype(torch::kFloat32)
    );
    
    // Ensure loss is on the same device as the model
    if (torch::cuda::is_available()) {
        loss = loss.cuda(device_id_);
    }
    
    return loss;
}

//=============================================================================
// Entropy Regularization
//=============================================================================

torch::Tensor PhaseAwareLoss::compute_entropy_loss(const torch::Tensor& logits) {
    // Compute entropy of output distribution to encourage diversity
    // entropy = -sum(p * log(p))
    // loss = -entropy_reg * entropy (negative because we want to maximize entropy)
    
    // logits shape: [batch_size, seq_len, vocab_size]
    auto shape = logits.sizes();
    int64_t batch_size = shape[0];
    int64_t seq_len = shape[1];
    int64_t vocab_size = shape[2];
    
    // Reshape to [batch_size * seq_len, vocab_size]
    torch::Tensor flat_logits = logits.reshape({-1, vocab_size});
    
    // Compute log softmax
    torch::Tensor log_probs = torch::log_softmax(flat_logits, /*dim=*/1);
    
    // Compute probabilities
    torch::Tensor probs = torch::exp(log_probs);
    
    // Compute entropy: -sum(p * log(p))
    torch::Tensor entropy = -(probs * log_probs).sum(/*dim=*/1);
    
    // Mean across all positions
    torch::Tensor mean_entropy = entropy.mean();
    
    // Negative sign because we want to maximize entropy (increase diversity)
    torch::Tensor loss = -config_.entropy_reg * mean_entropy;
    
    return loss;
}

//=============================================================================
// Phase Consistency Loss
//=============================================================================

torch::Tensor PhaseAwareLoss::compute_phase_consistency_loss(
    const std::vector<torch::Tensor>& phase_tensors
) {
    if (phase_tensors.size() < 2) {
        return torch::zeros({1},
            torch::TensorOptions().device(base_loss_device(phase_tensors)));
    }
    
    // Compute variance of phases across layers
    // Lower variance = higher consistency = lower loss
    
    torch::Tensor total_variance = torch::zeros({1}, 
        torch::TensorOptions().dtype(torch::kFloat32));
    
    if (torch::cuda::is_available()) {
        total_variance = total_variance.cuda(device_id_);
    }
    
    int valid_layers = 0;
    
    // Compute mean phase across all layers
    torch::Tensor mean_phase = torch::zeros_like(phase_tensors[0]);
    for (const auto& phase : phase_tensors) {
        mean_phase = mean_phase + phase;
    }
    mean_phase = mean_phase / static_cast<float>(phase_tensors.size());
    
    // Compute variance from mean
    for (const auto& phase : phase_tensors) {
        torch::Tensor diff = phase - mean_phase;
        torch::Tensor variance = (diff * diff).mean();
        total_variance = total_variance + variance;
        valid_layers++;
    }
    
    if (valid_layers > 0) {
        total_variance = total_variance / valid_layers;
    }
    
    // Consistency loss encourages lower variance (higher consistency)
    // Using a small coefficient to not dominate training
    const float consistency_coef = 0.001f;
    torch::Tensor loss = consistency_coef * total_variance;
    
    return loss;
}

//=============================================================================
// Capacity Maximization Loss
//=============================================================================

torch::Tensor PhaseAwareLoss::compute_capacity_loss(
    const torch::Tensor& hidden_states,
    float target_capacity
) {
    // hidden_states shape: [batch_size, seq_len, hidden_dim]
    auto shape = hidden_states.sizes();
    int64_t batch_size = shape[0];
    int64_t seq_len = shape[1];
    int64_t hidden_dim = shape[2];
    
    // Flatten batch and sequence dimensions
    torch::Tensor flat_hidden = hidden_states.reshape({-1, hidden_dim});
    
    // Compute covariance matrix approximation
    // Capacity is related to effective rank of hidden state matrix
    
    // Method: Use variance along each dimension as proxy for capacity
    torch::Tensor mean_hidden = flat_hidden.mean(/*dim=*/0, /*keepdim=*/true);
    torch::Tensor centered = flat_hidden - mean_hidden;
    
    // Compute variance per dimension
    torch::Tensor variance = (centered * centered).mean(/*dim=*/0);
    
    // Effective capacity: ratio of high-variance dimensions
    // We want to maximize the number of dimensions with significant variance
    float threshold = 0.01f;  // Threshold for "active" dimension
    torch::Tensor active_dims = (variance > threshold).to(torch::kFloat32).sum();
    
    float capacity_ratio = active_dims.item<float>() / hidden_dim;
    
    // Loss: encourage capacity to approach target
    float capacity_diff = target_capacity - capacity_ratio;
    torch::Tensor loss = torch::tensor(
        capacity_diff * capacity_diff * 0.1f,
        torch::TensorOptions().dtype(hidden_states.dtype())
            .device(hidden_states.device())
    );
    
    // Also add small regularization to prevent collapse
    torch::Tensor variance_penalty = -variance.mean() * 0.0001f;
    
    return loss + variance_penalty;
}

//=============================================================================
// Statistics Update
//=============================================================================

void PhaseAwareLoss::update_statistics(
    float total_loss,
    float base_loss,
    float torsion_loss,
    float spectral_loss,
    float entropy_loss,
    float phase_loss,
    float torsion_energy,
    float spectral_dim
) {
    stats_.total_loss = total_loss;
    stats_.base_loss = base_loss;
    stats_.torsion_loss = torsion_loss;
    stats_.spectral_loss = spectral_loss;
    stats_.entropy_loss = entropy_loss;
    stats_.phase_loss = phase_loss;
    stats_.torsion_energy = torsion_energy;
    stats_.spectral_dimension = spectral_dim;
}

//=============================================================================
// Helper Functions
//=============================================================================

at::Device base_loss_device(const std::vector<torch::Tensor>& tensors) {
    if (!tensors.empty()) {
        return tensors[0].device();
    }
    if (torch::cuda::is_available()) {
        return at::Device(at::kCUDA, 0);
    }
    return at::Device(at::kCPU);
}

} // namespace uft

// Explicit instantiations for common types (if needed)
// template class uft::PhaseAwareLoss<float>;
// template class uft::PhaseAwareLoss<double>;
