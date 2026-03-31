/**
 * @file v7_brain_kernels.cu
 * @brief CUDA kernels for V7Brain architecture
 * 
 * Contains GPU-accelerated operations for:
 * - Embedding lookup
 * - Linear transformations
 * - Activation functions (ReLU, Tanh)
 * - Tensor operations
 * - Torsion field modulation
 */

#include <cuda_runtime.h>
#include <cuda_fp16.h>
#include <math.h>

namespace v7 {

// Kernel configuration constants
constexpr int BLOCK_SIZE = 256;
constexpr int WARP_SIZE = 32;

// ============================================================================
// Embedding Kernels
// ============================================================================

/**
 * @brief Embedding lookup kernel
 * Each thread handles one embedding vector
 */
__global__ void embeddingLookupKernel(const float* embedding_weights,  // [vocab_size, embed_dim]
                                       const int* tokens,                // [batch_size]
                                       float* output,                    // [batch_size, embed_dim]
                                       int batch_size,
                                       int vocab_size,
                                       int embed_dim) {
    const int idx = blockIdx.x * blockDim.x + threadIdx.x;
    const int total = batch_size * embed_dim;
    
    if (idx >= total) return;
    
    const int batch_idx = idx / embed_dim;
    const int embed_idx = idx % embed_dim;
    
    const int token = tokens[batch_idx];
    // Clamp token to valid range
    const int clamped_token = max(0, min(token, vocab_size - 1));
    
    output[idx] = embedding_weights[clamped_token * embed_dim + embed_idx];
}

/**
 * @brief Optimized embedding lookup using shared memory
 */
__global__ void embeddingLookupSharedKernel(const float* embedding_weights,
                                            const int* tokens,
                                            float* output,
                                            int batch_size,
                                            int vocab_size,
                                            int embed_dim) {
    __shared__ int shared_tokens[BLOCK_SIZE];
    
    const int tid = threadIdx.x;
    const int batch_idx = blockIdx.x;
    
    // Load token into shared memory (one token per block)
    if (tid == 0 && batch_idx < batch_size) {
        shared_tokens[0] = tokens[batch_idx];
    }
    __syncthreads();
    
    if (batch_idx >= batch_size) return;
    
    const int token = shared_tokens[0];
    const int clamped_token = max(0, min(token, vocab_size - 1));
    
    // Each thread handles part of the embedding vector
    for (int i = tid; i < embed_dim; i += blockDim.x) {
        output[batch_idx * embed_dim + i] = embedding_weights[clamped_token * embed_dim + i];
    }
}

// ============================================================================
// Linear Layer Kernels
// ============================================================================

/**
 * @brief Add bias to output (in-place)
 */
__global__ void addBiasKernel(float* output,           // [batch_size, out_dim]
                              const float* bias,       // [out_dim]
                              int batch_size,
                              int out_dim) {
    const int idx = blockIdx.x * blockDim.x + threadIdx.x;
    const int total = batch_size * out_dim;
    
    if (idx >= total) return;
    
    const int bias_idx = idx % out_dim;
    output[idx] += bias[bias_idx];
}

/**
 * @brief Fused linear + ReLU kernel
 * For small matrices, avoids cuBLAS overhead
 */
__global__ void linearReluKernel(const float* input,      // [batch_size, in_dim]
                                  const float* weights,    // [in_dim, out_dim]
                                  const float* bias,       // [out_dim]
                                  float* output,           // [batch_size, out_dim]
                                  int batch_size,
                                  int in_dim,
                                  int out_dim) {
    const int idx = blockIdx.x * blockDim.x + threadIdx.x;
    const int total = batch_size * out_dim;
    
    if (idx >= total) return;
    
    const int batch_idx = idx / out_dim;
    const int out_idx = idx % out_dim;
    
    float sum = bias ? bias[out_idx] : 0.0f;
    
    #pragma unroll 4
    for (int i = 0; i < in_dim; ++i) {
        sum += input[batch_idx * in_dim + i] * weights[i * out_dim + out_idx];
    }
    
    // ReLU activation
    output[idx] = fmaxf(0.0f, sum);
}

/**
 * @brief Fused linear + Tanh kernel
 */
__global__ void linearTanhKernel(const float* input,
                                  const float* weights,
                                  const float* bias,
                                  float* output,
                                  int batch_size,
                                  int in_dim,
                                  int out_dim) {
    const int idx = blockIdx.x * blockDim.x + threadIdx.x;
    const int total = batch_size * out_dim;
    
    if (idx >= total) return;
    
    const int batch_idx = idx / out_dim;
    const int out_idx = idx % out_dim;
    
    float sum = bias ? bias[out_idx] : 0.0f;
    
    #pragma unroll 4
    for (int i = 0; i < in_dim; ++i) {
        sum += input[batch_idx * in_dim + i] * weights[i * out_dim + out_idx];
    }
    
    // Tanh activation
    output[idx] = tanhf(sum);
}

// ============================================================================
// Activation Kernels
// ============================================================================

/**
 * @brief ReLU activation (in-place)
 */
__global__ void reluKernel(float* data, int count) {
    const int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= count) return;
    
    data[idx] = fmaxf(0.0f, data[idx]);
}

/**
 * @brief Tanh activation (in-place)
 */
__global__ void tanhKernel(float* data, int count) {
    const int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= count) return;
    
    data[idx] = tanhf(data[idx]);
}

/**
 * @brief Fast tanh approximation (faster but less accurate)
 */
__global__ void tanhFastKernel(float* data, int count) {
    const int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= count) return;
    
    float x = data[idx];
    // Approximation: tanh(x) ≈ x / (1 + |x|) for fast compute
    data[idx] = x / (1.0f + fabsf(x));
}

// ============================================================================
// Tensor Operation Kernels
// ============================================================================

/**
 * @brief Element-wise addition: out = a + b
 */
__global__ void addKernel(const float* a, const float* b, float* out, int count) {
    const int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= count) return;
    
    out[idx] = a[idx] + b[idx];
}

/**
 * @brief Fused addition + tanh: out = tanh(a + b + c)
 * Used for final motor output computation
 */
__global__ void add3TanhKernel(const float* a,      // lang_motor
                                const float* b,      // sense_motor
                                const float* c,      // fusion_out
                                float* out,
                                int batch_size,
                                int dim) {
    const int idx = blockIdx.x * blockDim.x + threadIdx.x;
    const int total = batch_size * dim;
    
    if (idx >= total) return;
    
    float sum = a[idx] + b[idx] + c[idx];
    out[idx] = tanhf(sum);
}

/**
 * @brief Concatenate two tensors along last dimension
 * out = [a | b] where a is [batch, dim_a], b is [batch, dim_b]
 */
__global__ void concatKernel(const float* a,        // [batch, dim_a]
                              const float* b,        // [batch, dim_b]
                              float* out,            // [batch, dim_a + dim_b]
                              int batch_size,
                              int dim_a,
                              int dim_b) {
    const int idx = blockIdx.x * blockDim.x + threadIdx.x;
    const int total = batch_size * (dim_a + dim_b);
    
    if (idx >= total) return;
    
    const int batch_idx = idx / (dim_a + dim_b);
    const int dim_idx = idx % (dim_a + dim_b);
    
    if (dim_idx < dim_a) {
        out[idx] = a[batch_idx * dim_a + dim_idx];
    } else {
        out[idx] = b[batch_idx * dim_b + (dim_idx - dim_a)];
    }
}

// ============================================================================
// Torsion Field Kernels
// ============================================================================

/**
 * @brief Apply torsion field modulation
 * thalamic = ReLU(thalamic + tanh(torsion) * scale)
 */
__global__ void torsionModulateKernel(float* thalamic,           // [batch, hidden_dim]
                                       const float* torsion,      // [hidden_dim]
                                       int batch_size,
                                       int hidden_dim,
                                       float scale) {
    const int idx = blockIdx.x * blockDim.x + threadIdx.x;
    const int total = batch_size * hidden_dim;
    
    if (idx >= total) return;
    
    const int hidden_idx = idx % hidden_dim;
    
    float modulated = thalamic[idx] + tanhf(torsion[hidden_idx]) * scale;
    thalamic[idx] = fmaxf(0.0f, modulated);
}

/**
 * @brief Compute torsion field gradients (for backprop)
 */
__global__ void torsionGradKernel(const float* grad_output,     // [batch, hidden_dim]
                                   const float* torsion,         // [hidden_dim]
                                   float* grad_torsion,          // [hidden_dim]
                                   int batch_size,
                                   int hidden_dim,
                                   float scale) {
    const int hidden_idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (hidden_idx >= hidden_dim) return;
    
    float t_val = torsion[hidden_idx];
    float dtanh = 1.0f - tanhf(t_val) * tanhf(t_val);  // derivative of tanh
    
    float grad = 0.0f;
    for (int b = 0; b < batch_size; ++b) {
        grad += grad_output[b * hidden_dim + hidden_idx] * dtanh * scale;
    }
    
    grad_torsion[hidden_idx] = grad;
}

// ============================================================================
// Zero/Fill Kernels
// ============================================================================

__global__ void fillZeroKernel(float* data, int count) {
    const int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= count) return;
    data[idx] = 0.0f;
}

// ============================================================================
// Host Interface Functions
// ============================================================================

extern "C" {

// Embedding lookup
void v7EmbeddingLookup(const float* embedding_weights,
                       const int* tokens,
                       float* output,
                       int batch_size,
                       int vocab_size,
                       int embed_dim,
                       cudaStream_t stream) {
    const int total = batch_size * embed_dim;
    const int blocks = (total + BLOCK_SIZE - 1) / BLOCK_SIZE;
    embeddingLookupKernel<<<blocks, BLOCK_SIZE, 0, stream>>>(
        embedding_weights, tokens, output, batch_size, vocab_size, embed_dim);
}

// Optimized embedding lookup for larger batches
void v7EmbeddingLookupOptimized(const float* embedding_weights,
                                 const int* tokens,
                                 float* output,
                                 int batch_size,
                                 int vocab_size,
                                 int embed_dim,
                                 cudaStream_t stream) {
    if (batch_size >= 32) {
        // Use shared memory version for larger batches
        embeddingLookupSharedKernel<<<batch_size, BLOCK_SIZE, 0, stream>>>(
            embedding_weights, tokens, output, batch_size, vocab_size, embed_dim);
    } else {
        v7EmbeddingLookup(embedding_weights, tokens, output, batch_size, vocab_size, embed_dim, stream);
    }
}

// Linear layer forward (small matrices, fused with activation)
void v7LinearRelu(const float* input,
                  const float* weights,
                  const float* bias,
                  float* output,
                  int batch_size,
                  int in_dim,
                  int out_dim,
                  cudaStream_t stream) {
    const int total = batch_size * out_dim;
    const int blocks = (total + BLOCK_SIZE - 1) / BLOCK_SIZE;
    linearReluKernel<㰼blocks, BLOCK_SIZE, 0, stream>>>(
        input, weights, bias, output, batch_size, in_dim, out_dim);
}

void v7LinearTanh(const float* input,
                  const float* weights,
                  const float* bias,
                  float* output,
                  int batch_size,
                  int in_dim,
                  int out_dim,
                  cudaStream_t stream) {
    const int total = batch_size * out_dim;
    const int blocks = (total + BLOCK_SIZE - 1) / BLOCK_SIZE;
    linearTanhKernel<<<blocks, BLOCK_SIZE, 0, stream>>>(
        input, weights, bias, output, batch_size, in_dim, out_dim);
}

// Add bias
void v7AddBias(float* output,
               const float* bias,
               int batch_size,
               int out_dim,
               cudaStream_t stream) {
    const int total = batch_size * out_dim;
    const int blocks = (total + BLOCK_SIZE - 1) / BLOCK_SIZE;
    addBiasKernel<<<blocks, BLOCK_SIZE, 0, stream>>>(
        output, bias, batch_size, out_dim);
}

// Activation functions
void v7Relu(float* data, int count, cudaStream_t stream) {
    const int blocks = (count + BLOCK_SIZE - 1) / BLOCK_SIZE;
    reluKernel<<<blocks, BLOCK_SIZE, 0, stream>>>(data, count);
}

void v7Tanh(float* data, int count, cudaStream_t stream) {
    const int blocks = (count + BLOCK_SIZE - 1) / BLOCK_SIZE;
    tanhKernel<<<blocks, BLOCK_SIZE, 0, stream>>>(data, count);
}

void v7TanhFast(float* data, int count, cudaStream_t stream) {
    const int blocks = (count + BLOCK_SIZE - 1) / BLOCK_SIZE;
    tanhFastKernel<<<blocks, BLOCK_SIZE, 0, stream>>>(data, count);
}

// Tensor operations
void v7Add(const float* a, const float* b, float* out, int count, cudaStream_t stream) {
    const int blocks = (count + BLOCK_SIZE - 1) / BLOCK_SIZE;
    addKernel<<<blocks, BLOCK_SIZE, 0, stream>>>(a, b, out, count);
}

void v7Add3Tanh(const float* a,
                const float* b,
                const float* c,
                float* out,
                int batch_size,
                int dim,
                cudaStream_t stream) {
    const int total = batch_size * dim;
    const int blocks = (total + BLOCK_SIZE - 1) / BLOCK_SIZE;
    add3TanhKernel<<<blocks, BLOCK_SIZE, 0, stream>>>(a, b, c, out, batch_size, dim);
}

void v7Concat(const float* a,
              const float* b,
              float* out,
              int batch_size,
              int dim_a,
              int dim_b,
              cudaStream_t stream) {
    const int total = batch_size * (dim_a + dim_b);
    const int blocks = (total + BLOCK_SIZE - 1) / BLOCK_SIZE;
    concatKernel<<<blocks, BLOCK_SIZE, 0, stream>>>(
        a, b, out, batch_size, dim_a, dim_b);
}

// Torsion modulation
void v7TorsionModulate(float* thalamic,
                       const float* torsion,
                       int batch_size,
                       int hidden_dim,
                       float scale,
                       cudaStream_t stream) {
    const int total = batch_size * hidden_dim;
    const int blocks = (total + BLOCK_SIZE - 1) / BLOCK_SIZE;
    torsionModulateKernel<<<blocks, BLOCK_SIZE, 0, stream>>>(
        thalamic, torsion, batch_size, hidden_dim, scale);
}

// Zero fill
void v7FillZero(float* data, int count, cudaStream_t stream) {
    const int blocks = (count + BLOCK_SIZE - 1) / BLOCK_SIZE;
    fillZeroKernel<<<blocks, BLOCK_SIZE, 0, stream>>>(data, count);
}

} // extern "C"

} // namespace v7
