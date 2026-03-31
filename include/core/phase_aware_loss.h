/**
 * @file phase_aware_loss.h
 * @brief Phase-Aware Loss Module for TNN-Transformer Training
 * 
 * CUDA/C++ implementation of the PhaseAwareLoss module originally written in Python.
 * Provides regularization losses for torsion field energy, spectral dimension constraints,
 * and phase consistency in transformer training.
 */

#pragma once

#include <cuda_runtime.h>
#include <torch/torch.h>
#include <vector>
#include <memory>
#include <string>

namespace uft {

/**
 * @brief Configuration for phase-aware loss computation
 * Corresponds to Python LossConfig dataclass
 */
struct PhaseLossConfig {
    std::string name = "baseline";
    
    // Torsion field regularization coefficient
    float torsion_coef = 0.0001f;
    
    // Minimum energy constraint (0 means no constraint)
    float torsion_min_energy = 0.0f;
    
    // Target energy value (negative means no target)
    float torsion_target = -1.0f;
    
    // Spectral dimension regularization
    float spectral_reg = 0.0f;
    
    // Entropy regularization (encourages diversity)
    float entropy_reg = 0.0f;
    
    // Description of the configuration
    std::string description = "";
    
    // Adaptive mode flag (torsion_coef == -1.0 means adaptive)
    bool is_adaptive() const { return torsion_coef < 0.0f; }
};

/**
 * @brief Statistics for monitoring loss components
 */
struct LossStatistics {
    float total_loss = 0.0f;
    float base_loss = 0.0f;
    float torsion_loss = 0.0f;
    float spectral_loss = 0.0f;
    float entropy_loss = 0.0f;
    float phase_loss = 0.0f;
    float torsion_energy = 0.0f;
    float spectral_dimension = 0.0f;
    float capacity_score = 0.0f;
};

/**
 * @brief Torsion energy statistics per layer
 */
struct TorsionLayerStats {
    float energy = 0.0f;
    float mean_phase = 0.0f;
    float phase_variance = 0.0f;
    float coherence = 0.0f;
};

/**
 * @brief Phase-Aware Loss Module
 * 
 * Implements the following loss components:
 * 1. Torsion field energy regularization
 * 2. Capacity maximization loss
 * 3. Spectral dimension constraint loss
 * 4. Phase consistency loss
 */
class PhaseAwareLoss {
public:
    /**
     * @brief Constructor
     * @param config Loss configuration
     * @param num_layers Number of transformer layers
     * @param device CUDA device ID
     */
    PhaseAwareLoss(const PhaseLossConfig& config, int num_layers, int device = 0);
    
    /**
     * @brief Destructor
     */
    ~PhaseAwareLoss();

    /**
     * @brief Compute total loss with all regularization terms
     * @param base_loss Base cross-entropy loss from language modeling
     * @param torsion_energies Per-layer torsion energies
     * @param logits Model output logits [batch_size, seq_len, vocab_size]
     * @param current_spectral_dim Current spectral dimension value
     * @param step Current training step (for adaptive regularization)
     * @return Total loss including all regularization terms
     */
    torch::Tensor compute_loss(
        const torch::Tensor& base_loss,
        const std::vector<torch::Tensor>& torsion_energies,
        const torch::Tensor& logits,
        float current_spectral_dim,
        int64_t step = 0
    );

    /**
     * @brief Compute torsion field energy regularization loss
     * @param torsion_energies Per-layer torsion energies
     * @param avg_energy Output average torsion energy
     * @return Torsion regularization loss
     */
    torch::Tensor compute_torsion_regularization(
        const std::vector<torch::Tensor>& torsion_energies,
        float& avg_energy
    );

    /**
     * @brief Compute adaptive torsion regularization
     * @param torsion_energies Per-layer torsion energies
     * @param avg_energy Output average torsion energy
     * @return Adaptive torsion loss
     */
    torch::Tensor compute_adaptive_torsion_loss(
        const std::vector<torch::Tensor>& torsion_energies,
        float& avg_energy
    );

    /**
     * @brief Compute spectral dimension constraint loss
     * @param current_d_s Current spectral dimension
     * @return Spectral regularization loss
     */
    torch::Tensor compute_spectral_loss(float current_d_s);

    /**
     * @brief Compute entropy regularization (encourages diversity)
     * @param logits Model output logits
     * @return Entropy regularization loss
     */
    torch::Tensor compute_entropy_loss(const torch::Tensor& logits);

    /**
     * @brief Compute phase consistency loss
     * @param phase_tensors Per-layer phase tensors
     * @return Phase consistency loss
     */
    torch::Tensor compute_phase_consistency_loss(
        const std::vector<torch::Tensor>& phase_tensors
    );

    /**
     * @brief Compute capacity maximization loss
     * Encourages model to maximize effective memory capacity
     * @param hidden_states Hidden states from transformer
     * @param target_capacity Target capacity ratio (0.0 - 1.0)
     * @return Capacity loss
     */
    torch::Tensor compute_capacity_loss(
        const torch::Tensor& hidden_states,
        float target_capacity = 0.8f
    );

    /**
     * @brief Get current loss statistics
     * @return Loss statistics structure
     */
    LossStatistics get_statistics() const { return stats_; }

    /**
     * @brief Get per-layer torsion statistics
     * @return Vector of layer statistics
     */
    std::vector<TorsionLayerStats> get_layer_statistics() const { return layer_stats_; }

    /**
     * @brief Reset internal statistics
     */
    void reset_statistics();

    /**
     * @brief Update configuration during training
     * @param config New configuration
     */
    void set_config(const PhaseLossConfig& config) { config_ = config; }

    /**
     * @brief Get current configuration
     * @return Current configuration
     */
    const PhaseLossConfig& get_config() const { return config_; }

    /**
     * @brief Synchronize CUDA stream
     */
    void synchronize() const;

private:
    PhaseLossConfig config_;
    int num_layers_;
    int device_id_;
    LossStatistics stats_;
    std::vector<TorsionLayerStats> layer_stats_;
    
    // CUDA stream for asynchronous operations
    cudaStream_t cuda_stream_;
    
    // Internal buffers for CUDA operations
    float* d_torsion_buffer_ = nullptr;
    size_t torsion_buffer_size_ = 0;
    
    // Adaptive regularization state
    float adaptive_coef_ = 0.0001f;
    float energy_ema_ = 0.0f;  // Exponential moving average of energy
    
    // Initialize CUDA resources
    void init_cuda_resources();
    
    // Release CUDA resources
    void release_cuda_resources();
    
    // Update statistics from CUDA computation
    void update_statistics(
        float total_loss,
        float base_loss,
        float torsion_loss,
        float spectral_loss,
        float entropy_loss,
        float phase_loss,
        float torsion_energy,
        float spectral_dim
    );
};

/**
 * @brief CUDA kernel launcher functions (declarations)
 */
namespace cuda_kernels {

/**
 * @brief Compute torsion energy aggregation across layers
 * @param d_energies Input energy array
 * @param d_output Output aggregated energy
 * @param num_layers Number of layers
 * @param stream CUDA stream
 */
void launch_torsion_energy_aggregate(
    const float* d_energies,
    float* d_output,
    int num_layers,
    cudaStream_t stream = nullptr
);

/**
 * @brief Compute adaptive coefficient based on energy
 * @param avg_energy Average torsion energy
 * @param d_output Output coefficient
 * @param stream CUDA stream
 */
void launch_adaptive_coef_compute(
    float avg_energy,
    float* d_output,
    cudaStream_t stream = nullptr
);

/**
 * @brief Compute entropy from logits
 * @param d_logits Input logits [batch_size * seq_len, vocab_size]
 * @param d_entropy Output entropy [batch_size * seq_len]
 * @param batch_seq Batch size * sequence length
 * @param vocab_size Vocabulary size
 * @param stream CUDA stream
 */
void launch_entropy_compute(
    const float* d_logits,
    float* d_entropy,
    int batch_seq,
    int vocab_size,
    cudaStream_t stream = nullptr
);

/**
 * @brief Compute phase consistency metric
 * @param d_phases Input phase tensors
 * @param d_consistency Output consistency score
 * @param num_elements Total number of phase elements
 * @param stream CUDA stream
 */
void launch_phase_consistency_compute(
    const float* d_phases,
    float* d_consistency,
    int num_elements,
    cudaStream_t stream = nullptr
);

/**
 * @brief Compute capacity metric from hidden states
 * @param d_hidden Input hidden states
 * @param d_capacity Output capacity score
 * @param batch_size Batch size
 * @param seq_len Sequence length
 * @param hidden_dim Hidden dimension
 * @param stream CUDA stream
 */
void launch_capacity_compute(
    const float* d_hidden,
    float* d_capacity,
    int batch_size,
    int seq_len,
    int hidden_dim,
    cudaStream_t stream = nullptr
);

/**
 * @brief Apply spectral dimension penalty
 * @param current_d_s Current spectral dimension
 * @param target_min Target minimum dimension
 * @param target_max Target maximum dimension
 * @param d_output Output penalty
 * @param stream CUDA stream
 */
void launch_spectral_penalty_compute(
    float current_d_s,
    float target_min,
    float target_max,
    float* d_output,
    cudaStream_t stream = nullptr
);

} // namespace cuda_kernels

} // namespace uft
