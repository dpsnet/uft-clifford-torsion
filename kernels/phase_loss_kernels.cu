/**
 * @file phase_loss_kernels.cu
 * @brief CUDA kernel implementations for Phase-Aware Loss computations
 */

#include <cuda_runtime.h>
#include <cuda_fp16.h>
#include <math>
#include <float.h>

namespace uft {
namespace cuda_kernels {

// Constants
constexpr int BLOCK_SIZE = 256;
constexpr float EPSILON = 1e-10f;

/**
 * @brief Warp-level reduction for sum
 */
__inline__ __device__ float warp_reduce_sum(float val) {
    for (int offset = 16; offset > 0; offset /= 2) {
        val += __shfl_down_sync(0xFFFFFFFF, val, offset);
    }
    return val;
}

/**
 * @brief Block-level reduction for sum using shared memory
 */
__inline__ __device__ float block_reduce_sum(float val, float* shared_mem) {
    const int lane_id = threadIdx.x % 32;
    const int warp_id = threadIdx.x / 32;
    
    // Warp-level reduction
    val = warp_reduce_sum(val);
    
    // Write to shared memory
    if (lane_id == 0) {
        shared_mem[warp_id] = val;
    }
    __syncthreads();
    
    // Final reduction across warps
    if (warp_id == 0) {
        val = (lane_id < (blockDim.x + 31) / 32) ? shared_mem[lane_id] : 0.0f;
        val = warp_reduce_sum(val);
    }
    
    return val;
}

/**
 * @brief Kernel: Aggregate torsion energies across layers
 */
__global__ void torsion_energy_aggregate_kernel(
    const float* __restrict__ d_energies,
    float* __restrict__ d_output,
    int num_layers
) {
    __shared__ float shared_mem[BLOCK_SIZE / 32];
    
    float sum = 0.0f;
    for (int i = threadIdx.x; i < num_layers; i += blockDim.x) {
        sum += d_energies[i];
    }
    
    sum = block_reduce_sum(sum, shared_mem);
    
    if (threadIdx.x == 0) {
        d_output[0] = sum;
        d_output[1] = sum / static_cast<float>(num_layers);  // Average
    }
}

/**
 * @brief Kernel: Compute adaptive coefficient based on energy level
 * 
 * Energy < 1.0: High regularization needed (energy too low)
 * Energy > 10.0: Moderate regularization (energy acceptable)
 * 1.0 <= Energy <= 10.0: Low regularization (energy in sweet spot)
 */
__global__ void adaptive_coef_compute_kernel(
    float avg_energy,
    float* __restrict__ d_output
) {
    float coef;
    if (avg_energy < 1.0f) {
        // Energy too low - increase regularization
        coef = 0.01f * (1.0f - avg_energy);
    } else if (avg_energy > 10.0f) {
        // Energy acceptable but high
        coef = 0.001f;
    } else {
        // Energy in sweet spot
        coef = 0.0001f;
    }
    d_output[0] = coef;
}

/**
 * @brief Kernel: Compute softmax probabilities and entropy for a row
 */
__global__ void entropy_compute_kernel(
    const float* __restrict__ d_logits,
    float* __restrict__ d_entropy,
    int batch_seq,
    int vocab_size
) {
    __shared__ float shared_mem[BLOCK_SIZE];
    
    const int row_idx = blockIdx.x;
    if (row_idx >= batch_seq) return;
    
    const float* row_logits = d_logits + row_idx * vocab_size;
    
    // Step 1: Find max for numerical stability
    float max_val = -FLT_MAX;
    for (int i = threadIdx.x; i < vocab_size; i += blockDim.x) {
        max_val = fmaxf(max_val, row_logits[i]);
    }
    
    // Warp reduction for max
    for (int offset = 16; offset > 0; offset /= 2) {
        max_val = fmaxf(max_val, __shfl_down_sync(0xFFFFFFFF, max_val, offset));
    }
    
    if (threadIdx.x % 32 == 0) {
        shared_mem[threadIdx.x / 32] = max_val;
    }
    __syncthreads();
    
    if (threadIdx.x < (blockDim.x + 31) / 32) {
        max_val = shared_mem[threadIdx.x];
    }
    for (int offset = 16; offset > 0; offset /= 2) {
        max_val = fmaxf(max_val, __shfl_down_sync(0xFFFFFFFF, max_val, offset));
    }
    max_val = __shfl_sync(0xFFFFFFFF, max_val, 0);
    
    // Step 2: Compute exp(logit - max) and sum
    float sum_exp = 0.0f;
    float entropy_sum = 0.0f;
    
    for (int i = threadIdx.x; i < vocab_size; i += blockDim.x) {
        float exp_val = expf(row_logits[i] - max_val);
        sum_exp += exp_val;
        // For entropy: -p * log(p) = -exp(logit - max) / sum * (logit - max - log(sum))
        // We'll compute this in second pass
    }
    
    // Reduce sum_exp
    sum_exp = warp_reduce_sum(sum_exp);
    if (threadIdx.x % 32 == 0) {
        shared_mem[threadIdx.x / 32] = sum_exp;
    }
    __syncthreads();
    
    if (threadIdx.x < (blockDim.x + 31) / 32) {
        sum_exp = shared_mem[threadIdx.x];
    }
    for (int offset = 16; offset > 0; offset /= 2) {
        sum_exp = warp_reduce_sum(sum_exp);
    }
    sum_exp = __shfl_sync(0xFFFFFFFF, sum_exp, 0);
    
    // Step 3: Compute entropy
    float log_sum = logf(sum_exp);
    
    for (int i = threadIdx.x; i < vocab_size; i += blockDim.x) {
        float exp_val = expf(row_logits[i] - max_val);
        float prob = exp_val / sum_exp;
        if (prob > EPSILON) {
            float log_prob = (row_logits[i] - max_val) - log_sum;
            entropy_sum -= prob * log_prob;
        }
    }
    
    // Reduce entropy
    entropy_sum = warp_reduce_sum(entropy_sum);
    if (threadIdx.x % 32 == 0) {
        shared_mem[threadIdx.x / 32] = entropy_sum;
    }
    __syncthreads();
    
    if (threadIdx.x < (blockDim.x + 31) / 32) {
        entropy_sum = shared_mem[threadIdx.x];
    }
    for (int offset = 16; offset > 0; offset /= 2) {
        entropy_sum = warp_reduce_sum(entropy_sum);
    }
    
    if (threadIdx.x == 0) {
        d_entropy[row_idx] = entropy_sum;
    }
}

/**
 * @brief Kernel: Compute phase consistency (coherence) metric
 * Measures how similar phases are across elements
 */
__global__ void phase_consistency_kernel(
    const float* __restrict__ d_phases,
    float* __restrict__ d_consistency,
    int num_elements
) {
    __shared__ float shared_mem[BLOCK_SIZE / 32];
    
    // Compute mean phase
    float sum = 0.0f;
    for (int i = blockIdx.x * blockDim.x + threadIdx.x; 
         i < num_elements; 
         i += gridDim.x * blockDim.x) {
        sum += d_phases[i];
    }
    
    sum = block_reduce_sum(sum, shared_mem);
    
    __shared__ float mean_phase;
    if (threadIdx.x == 0) {
        mean_phase = sum / num_elements;
    }
    __syncthreads();
    
    // Compute variance
    float var_sum = 0.0f;
    for (int i = blockIdx.x * blockDim.x + threadIdx.x; 
         i < num_elements; 
         i += gridDim.x * blockDim.x) {
        float diff = d_phases[i] - mean_phase;
        var_sum += diff * diff;
    }
    
    var_sum = block_reduce_sum(var_sum, shared_mem);
    
    if (threadIdx.x == 0) {
        float variance = var_sum / num_elements;
        // Consistency is inverse of variance (normalized)
        d_consistency[0] = 1.0f / (1.0f + variance);
    }
}

/**
 * @brief Kernel: Compute memory capacity metric from hidden states
 * Uses effective rank approximation
 */
__global__ void capacity_compute_kernel(
    const float* __restrict__ d_hidden,
    float* __restrict__ d_capacity,
    int batch_size,
    int seq_len,
    int hidden_dim
) {
    __shared__ float shared_mem[BLOCK_SIZE / 32];
    
    const int total_tokens = batch_size * seq_len;
    
    // Compute mean activation per dimension
    float mean_sum = 0.0f;
    for (int i = threadIdx.x; i < total_tokens; i += blockDim.x) {
        mean_sum += d_hidden[i * hidden_dim + blockIdx.x];
    }
    
    mean_sum = block_reduce_sum(mean_sum, shared_mem);
    
    __shared__ float mean_val;
    if (threadIdx.x == 0) {
        mean_val = mean_sum / total_tokens;
    }
    __syncthreads();
    
    // Compute variance (approximation of signal strength)
    float var_sum = 0.0f;
    for (int i = threadIdx.x; i < total_tokens; i += blockDim.x) {
        float diff = d_hidden[i * hidden_dim + blockIdx.x] - mean_val;
        var_sum += diff * diff;
    }
    
    var_sum = block_reduce_sum(var_sum, shared_mem);
    
    if (threadIdx.x == 0) {
        // Store variance for this dimension
        d_capacity[blockIdx.x] = var_sum / total_tokens;
    }
}

/**
 * @brief Kernel: Apply spectral dimension penalty
 * Penalizes dimensions outside target range [3, 6]
 */
__global__ void spectral_penalty_kernel(
    float current_d_s,
    float target_min,
    float target_max,
    float* __restrict__ d_output
) {
    float penalty = 0.0f;
    
    if (current_d_s < target_min) {
        float diff = target_min - current_d_s;
        penalty = diff * diff;
    } else if (current_d_s > target_max) {
        float diff = current_d_s - target_max;
        penalty = diff * diff;
    }
    
    d_output[0] = penalty;
}

/**
 * @brief Kernel: Min energy penalty (ReLU-based)
 * Penalizes when energy is below minimum threshold
 */
__global__ void min_energy_penalty_kernel(
    float energy,
    float min_energy,
    float* __restrict__ d_output
) {
    float diff = min_energy - energy;
    float penalty = (diff > 0.0f) ? diff * diff : 0.0f;
    d_output[0] = 0.1f * penalty;  // 0.1 coefficient from Python code
}

/**
 * @brief Kernel: Target energy penalty
 * Penalizes deviation from target energy
 */
__global__ void target_energy_penalty_kernel(
    float energy,
    float target,
    float* __restrict__ d_output
) {
    float diff = energy - target;
    d_output[0] = 0.01f * diff * diff;  // 0.01 coefficient from Python code
}

//=============================================================================
// Launcher functions
//=============================================================================

void launch_torsion_energy_aggregate(
    const float* d_energies,
    float* d_output,
    int num_layers,
    cudaStream_t stream
) {
    torsion_energy_aggregate_kernel<<<1, BLOCK_SIZE, 0, stream>>>(
        d_energies, d_output, num_layers
    );
}

void launch_adaptive_coef_compute(
    float avg_energy,
    float* d_output,
    cudaStream_t stream
) {
    adaptive_coef_compute_kernel<<<1, 1, 0, stream>>>(
        avg_energy, d_output
    );
}

void launch_entropy_compute(
    const float* d_logits,
    float* d_entropy,
    int batch_seq,
    int vocab_size,
    cudaStream_t stream
) {
    dim3 grid(batch_seq);
    dim3 block(BLOCK_SIZE);
    
    entropy_compute_kernel<<<grid, block, 0, stream>>>(
        d_logits, d_entropy, batch_seq, vocab_size
    );
}

void launch_phase_consistency_compute(
    const float* d_phases,
    float* d_consistency,
    int num_elements,
    cudaStream_t stream
) {
    int num_blocks = (num_elements + BLOCK_SIZE - 1) / BLOCK_SIZE;
    num_blocks = min(num_blocks, 1024);  // Limit number of blocks
    
    phase_consistency_kernel<<<num_blocks, BLOCK_SIZE, 0, stream>>>(
        d_phases, d_consistency, num_elements
    );
}

void launch_capacity_compute(
    const float* d_hidden,
    float* d_capacity,
    int batch_size,
    int seq_len,
    int hidden_dim,
    cudaStream_t stream
) {
    // Launch one block per hidden dimension
    capacity_compute_kernel<<<hidden_dim, BLOCK_SIZE, 0, stream>>>(
        d_hidden, d_capacity, batch_size, seq_len, hidden_dim
    );
}

void launch_spectral_penalty_compute(
    float current_d_s,
    float target_min,
    float target_max,
    float* d_output,
    cudaStream_t stream
) {
    spectral_penalty_kernel<<<1, 1, 0, stream>>>(
        current_d_s, target_min, target_max, d_output
    );
}

// Additional launcher for min energy constraint
void launch_min_energy_penalty(
    float energy,
    float min_energy,
    float* d_output,
    cudaStream_t stream
) {
    min_energy_penalty_kernel<<<1, 1, 0, stream>>>(
        energy, min_energy, d_output
    );
}

// Additional launcher for target energy constraint
void launch_target_energy_penalty(
    float energy,
    float target,
    float* d_output,
    cudaStream_t stream
) {
    target_energy_penalty_kernel<<<1, 1, 0, stream>>>(
        energy, target, d_output
    );
}

} // namespace cuda_kernels
} // namespace uft
