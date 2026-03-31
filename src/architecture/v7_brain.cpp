/**
 * @file v7_brain.cpp
 * @brief C++ implementation of V7Brain architecture
 * 
 * Implements the Cortex, Brainstem, Thalamus, and V7Brain classes
 * using CUDA for GPU acceleration and cuBLAS for matrix operations.
 */

#include "architecture/v7_brain.h"
#include <cstring>
#include <cstdlib>
#include <time.h>
#include <math.h>
#include <iostream>

namespace v7 {

// ============================================================================
// External CUDA kernel interfaces
// ============================================================================

extern "C" {
    void v7EmbeddingLookup(const float* embedding_weights,
                           const int* tokens,
                           float* output,
                           int batch_size,
                           int vocab_size,
                           int embed_dim,
                           cudaStream_t stream);
    
    void v7EmbeddingLookupOptimized(const float* embedding_weights,
                                     const int* tokens,
                                     float* output,
                                     int batch_size,
                                     int vocab_size,
                                     int embed_dim,
                                     cudaStream_t stream);
    
    void v7LinearRelu(const float* input,
                      const float* weights,
                      const float* bias,
                      float* output,
                      int batch_size,
                      int in_dim,
                      int out_dim,
                      cudaStream_t stream);
    
    void v7LinearTanh(const float* input,
                      const float* weights,
                      const float* bias,
                      float* output,
                      int batch_size,
                      int in_dim,
                      int out_dim,
                      cudaStream_t stream);
    
    void v7AddBias(float* output,
                   const float* bias,
                   int batch_size,
                   int out_dim,
                   cudaStream_t stream);
    
    void v7Relu(float* data, int count, cudaStream_t stream);
    void v7Tanh(float* data, int count, cudaStream_t stream);
    void v7TanhFast(float* data, int count, cudaStream_t stream);
    
    void v7Add(const float* a, const float* b, float* out, int count, cudaStream_t stream);
    
    void v7Add3Tanh(const float* a,
                    const float* b,
                    const float* c,
                    float* out,
                    int batch_size,
                    int dim,
                    cudaStream_t stream);
    
    void v7Concat(const float* a,
                  const float* b,
                  float* out,
                  int batch_size,
                  int dim_a,
                  int dim_b,
                  cudaStream_t stream);
    
    void v7TorsionModulate(float* thalamic,
                           const float* torsion,
                           int batch_size,
                           int hidden_dim,
                           float scale,
                           cudaStream_t stream);
    
    void v7FillZero(float* data, int count, cudaStream_t stream);
}

// ============================================================================
// Utility Functions Implementation
// ============================================================================

namespace utils {

void xavierInit(float* weights, int fan_in, int fan_out, unsigned seed) {
    srand(seed);
    float scale = sqrtf(6.0f / (fan_in + fan_out));
    
    int count = fan_in * fan_out;
    for (int i = 0; i < count; ++i) {
        float r = static_cast<float>(rand()) / RAND_MAX;  // [0, 1]
        weights[i] = (2.0f * r - 1.0f) * scale;            // [-scale, scale]
    }
}

void zeroInit(float* data, int count) {
    memset(data, 0, count * sizeof(float));
}

void hostToDevice(float* d_dst, const float* h_src, size_t count) {
    cudaMemcpy(d_dst, h_src, count * sizeof(float), cudaMemcpyHostToDevice);
}

void deviceToHost(float* h_dst, const float* d_src, size_t count) {
    cudaMemcpy(h_dst, d_src, count * sizeof(float), cudaMemcpyDeviceToHost);
}

void tanhActivation(float* data, int count, cudaStream_t stream) {
    v7Tanh(data, count, stream);
}

void reluActivation(float* data, int count, cudaStream_t stream) {
    v7Relu(data, count, stream);
}

} // namespace utils

// ============================================================================
// Cortex Implementation
// ============================================================================

Cortex::Cortex() 
    : h_embedding_weights_(nullptr)
    , h_lang_to_motor_weights_(nullptr)
    , h_lang_to_motor_bias_(nullptr)
    , d_embedding_weights_(nullptr)
    , d_lang_to_motor_weights_(nullptr)
    , d_lang_to_motor_bias_(nullptr)
    , initialized_(false) {
}

Cortex::~Cortex() {
    // Free host memory
    delete[] h_embedding_weights_;
    delete[] h_lang_to_motor_weights_;
    delete[] h_lang_to_motor_bias_;
    
    // Free device memory
    if (d_embedding_weights_) cudaFree(d_embedding_weights_);
    if (d_lang_to_motor_weights_) cudaFree(d_lang_to_motor_weights_);
    if (d_lang_to_motor_bias_) cudaFree(d_lang_to_motor_bias_);
    
    if (initialized_) {
        cublasDestroy(cublas_handle_);
    }
}

void Cortex::initialize() {
    // Allocate host memory
    h_embedding_weights_ = new float[V7_VOCAB_SIZE * V7_EMBED_DIM];
    h_lang_to_motor_weights_ = new float[V7_EMBED_DIM * V7_MOTOR_DIM];
    h_lang_to_motor_bias_ = new float[V7_MOTOR_DIM];
    
    // Initialize weights with Xavier initialization
    utils::xavierInit(h_embedding_weights_, V7_VOCAB_SIZE, V7_EMBED_DIM);
    utils::xavierInit(h_lang_to_motor_weights_, V7_EMBED_DIM, V7_MOTOR_DIM);
    utils::zeroInit(h_lang_to_motor_bias_, V7_MOTOR_DIM);
    
    // Allocate device memory
    cudaMalloc(&d_embedding_weights_, V7_VOCAB_SIZE * V7_EMBED_DIM * sizeof(float));
    cudaMalloc(&d_lang_to_motor_weights_, V7_EMBED_DIM * V7_MOTOR_DIM * sizeof(float));
    cudaMalloc(&d_lang_to_motor_bias_, V7_MOTOR_DIM * sizeof(float));
    
    // Copy to device
    utils::hostToDevice(d_embedding_weights_, h_embedding_weights_, 
                        V7_VOCAB_SIZE * V7_EMBED_DIM);
    utils::hostToDevice(d_lang_to_motor_weights_, h_lang_to_motor_weights_,
                        V7_EMBED_DIM * V7_MOTOR_DIM);
    utils::hostToDevice(d_lang_to_motor_bias_, h_lang_to_motor_bias_, V7_MOTOR_DIM);
    
    // Initialize cuBLAS
    cublasCreate(&cublas_handle_);
    
    initialized_ = true;
}

void Cortex::forward(const int* language_tokens,
                     float* lang_hidden,
                     float* lang_motor,
                     int batch_size,
                     cudaStream_t stream) {
    if (!initialized_) {
        std::cerr << "Cortex not initialized!\n";
        return;
    }
    
    // Step 1: Embedding lookup
    v7EmbeddingLookupOptimized(d_embedding_weights_,
                                language_tokens,
                                lang_hidden,
                                batch_size,
                                V7_VOCAB_SIZE,
                                V7_EMBED_DIM,
                                stream);
    
    // Step 2: Linear transformation to motor space
    // Use cuBLAS for matrix multiplication: lang_motor = lang_hidden @ W + b
    const float alpha = 1.0f;
    const float beta = 0.0f;
    
    // Note: cuBLAS uses column-major order
    // C = A * B where A is [batch, embed], B is [embed, motor], C is [batch, motor]
    cublasSetStream(cublas_handle_, stream);
    cublasSgemm(cublas_handle_,
                CUBLAS_OP_N, CUBLAS_OP_N,
                V7_MOTOR_DIM, batch_size, V7_EMBED_DIM,
                &alpha,
                d_lang_to_motor_weights_, V7_MOTOR_DIM,
                lang_hidden, V7_EMBED_DIM,
                &beta,
                lang_motor, V7_MOTOR_DIM);
    
    // Add bias
    v7AddBias(lang_motor, d_lang_to_motor_bias_, batch_size, V7_MOTOR_DIM, stream);
}

size_t Cortex::getParamCount() const {
    return V7_VOCAB_SIZE * V7_EMBED_DIM +           // embedding
           V7_EMBED_DIM * V7_MOTOR_DIM +            // lang_to_motor weights
           V7_MOTOR_DIM;                             // lang_to_motor bias
}

// ============================================================================
// Brainstem Implementation
// ============================================================================

Brainstem::Brainstem()
    : h_sensor_weights_(nullptr)
    , h_sensor_bias_(nullptr)
    , h_sensor_to_motor_weights_(nullptr)
    , h_sensor_to_motor_bias_(nullptr)
    , d_sensor_weights_(nullptr)
    , d_sensor_bias_(nullptr)
    , d_sensor_to_motor_weights_(nullptr)
    , d_sensor_to_motor_bias_(nullptr)
    , initialized_(false) {
}

Brainstem::~Brainstem() {
    delete[] h_sensor_weights_;
    delete[] h_sensor_bias_;
    delete[] h_sensor_to_motor_weights_;
    delete[] h_sensor_to_motor_bias_;
    
    if (d_sensor_weights_) cudaFree(d_sensor_weights_);
    if (d_sensor_bias_) cudaFree(d_sensor_bias_);
    if (d_sensor_to_motor_weights_) cudaFree(d_sensor_to_motor_weights_);
    if (d_sensor_to_motor_bias_) cudaFree(d_sensor_to_motor_bias_);
    
    if (initialized_) {
        cublasDestroy(cublas_handle_);
    }
}

void Brainstem::initialize() {
    // Allocate host memory
    h_sensor_weights_ = new float[V7_SENSOR_DIM * V7_HIDDEN_DIM];
    h_sensor_bias_ = new float[V7_HIDDEN_DIM];
    h_sensor_to_motor_weights_ = new float[V7_HIDDEN_DIM * V7_MOTOR_DIM];
    h_sensor_to_motor_bias_ = new float[V7_MOTOR_DIM];
    
    // Initialize weights
    utils::xavierInit(h_sensor_weights_, V7_SENSOR_DIM, V7_HIDDEN_DIM);
    utils::zeroInit(h_sensor_bias_, V7_HIDDEN_DIM);
    utils::xavierInit(h_sensor_to_motor_weights_, V7_HIDDEN_DIM, V7_MOTOR_DIM);
    utils::zeroInit(h_sensor_to_motor_bias_, V7_MOTOR_DIM);
    
    // Allocate device memory
    cudaMalloc(&d_sensor_weights_, V7_SENSOR_DIM * V7_HIDDEN_DIM * sizeof(float));
    cudaMalloc(&d_sensor_bias_, V7_HIDDEN_DIM * sizeof(float));
    cudaMalloc(&d_sensor_to_motor_weights_, V7_HIDDEN_DIM * V7_MOTOR_DIM * sizeof(float));
    cudaMalloc(&d_sensor_to_motor_bias_, V7_MOTOR_DIM * sizeof(float));
    
    // Copy to device
    utils::hostToDevice(d_sensor_weights_, h_sensor_weights_, 
                        V7_SENSOR_DIM * V7_HIDDEN_DIM);
    utils::hostToDevice(d_sensor_bias_, h_sensor_bias_, V7_HIDDEN_DIM);
    utils::hostToDevice(d_sensor_to_motor_weights_, h_sensor_to_motor_weights_,
                        V7_HIDDEN_DIM * V7_MOTOR_DIM);
    utils::hostToDevice(d_sensor_to_motor_bias_, h_sensor_to_motor_bias_, V7_MOTOR_DIM);
    
    cublasCreate(&cublas_handle_);
    initialized_ = true;
}

void Brainstem::forward(const float* sensory_input,
                        float* sense_hidden,
                        float* sense_motor,
                        int batch_size,
                        cudaStream_t stream) {
    if (!initialized_) {
        std::cerr << "Brainstem not initialized!\n";
        return;
    }
    
    // Step 1: Sensor -> Hidden with ReLU
    // Using fused kernel for small matrix
    v7LinearRelu(sensory_input,
                 d_sensor_weights_,
                 d_sensor_bias_,
                 sense_hidden,
                 batch_size,
                 V7_SENSOR_DIM,
                 V7_HIDDEN_DIM,
                 stream);
    
    // Step 2: Hidden -> Motor (linear, no activation)
    const float alpha = 1.0f;
    const float beta = 0.0f;
    
    cublasSetStream(cublas_handle_, stream);
    cublasSgemm(cublas_handle_,
                CUBLAS_OP_N, CUBLAS_OP_N,
                V7_MOTOR_DIM, batch_size, V7_HIDDEN_DIM,
                &alpha,
                d_sensor_to_motor_weights_, V7_MOTOR_DIM,
                sense_hidden, V7_HIDDEN_DIM,
                &beta,
                sense_motor, V7_MOTOR_DIM);
    
    // Add bias
    v7AddBias(sense_motor, d_sensor_to_motor_bias_, batch_size, V7_MOTOR_DIM, stream);
}

size_t Brainstem::getParamCount() const {
    return V7_SENSOR_DIM * V7_HIDDEN_DIM + V7_HIDDEN_DIM +    // sensor layer
           V7_HIDDEN_DIM * V7_MOTOR_DIM + V7_MOTOR_DIM;       // sensor_to_motor layer
}

// ============================================================================
// Thalamus Implementation
// ============================================================================

Thalamus::Thalamus()
    : h_torsion_field_(nullptr)
    , d_torsion_field_(nullptr)
    , h_thalamus_weights_(nullptr)
    , h_thalamus_bias_(nullptr)
    , d_thalamus_weights_(nullptr)
    , d_thalamus_bias_(nullptr)
    , h_fusion_weights_(nullptr)
    , h_fusion_bias_(nullptr)
    , d_fusion_weights_(nullptr)
    , d_fusion_bias_(nullptr)
    , initialized_(false) {
}

Thalamus::~Thalamus() {
    delete[] h_torsion_field_;
    delete[] h_thalamus_weights_;
    delete[] h_thalamus_bias_;
    delete[] h_fusion_weights_;
    delete[] h_fusion_bias_;
    
    if (d_torsion_field_) cudaFree(d_torsion_field_);
    if (d_thalamus_weights_) cudaFree(d_thalamus_weights_);
    if (d_thalamus_bias_) cudaFree(d_thalamus_bias_);
    if (d_fusion_weights_) cudaFree(d_fusion_weights_);
    if (d_fusion_bias_) cudaFree(d_fusion_bias_);
    
    if (initialized_) {
        cublasDestroy(cublas_handle_);
    }
}

void Thalamus::initialize() {
    // Torsion field (learnable)
    h_torsion_field_ = new float[V7_HIDDEN_DIM];
    utils::zeroInit(h_torsion_field_, V7_HIDDEN_DIM);
    cudaMalloc(&d_torsion_field_, V7_HIDDEN_DIM * sizeof(float));
    utils::hostToDevice(d_torsion_field_, h_torsion_field_, V7_HIDDEN_DIM);
    
    // Thalamus transformation: 32 -> 16
    h_thalamus_weights_ = new float[V7_THALAMUS_DIM * V7_HIDDEN_DIM];
    h_thalamus_bias_ = new float[V7_HIDDEN_DIM];
    utils::xavierInit(h_thalamus_weights_, V7_THALAMUS_DIM, V7_HIDDEN_DIM);
    utils::zeroInit(h_thalamus_bias_, V7_HIDDEN_DIM);
    cudaMalloc(&d_thalamus_weights_, V7_THALAMUS_DIM * V7_HIDDEN_DIM * sizeof(float));
    cudaMalloc(&d_thalamus_bias_, V7_HIDDEN_DIM * sizeof(float));
    utils::hostToDevice(d_thalamus_weights_, h_thalamus_weights_, 
                        V7_THALAMUS_DIM * V7_HIDDEN_DIM);
    utils::hostToDevice(d_thalamus_bias_, h_thalamus_bias_, V7_HIDDEN_DIM);
    
    // Fusion transformation: 16 -> 2
    h_fusion_weights_ = new float[V7_HIDDEN_DIM * V7_MOTOR_DIM];
    h_fusion_bias_ = new float[V7_MOTOR_DIM];
    utils::xavierInit(h_fusion_weights_, V7_HIDDEN_DIM, V7_MOTOR_DIM);
    utils::zeroInit(h_fusion_bias_, V7_MOTOR_DIM);
    cudaMalloc(&d_fusion_weights_, V7_HIDDEN_DIM * V7_MOTOR_DIM * sizeof(float));
    cudaMalloc(&d_fusion_bias_, V7_MOTOR_DIM * sizeof(float));
    utils::hostToDevice(d_fusion_weights_, h_fusion_weights_, 
                        V7_HIDDEN_DIM * V7_MOTOR_DIM);
    utils::hostToDevice(d_fusion_bias_, h_fusion_bias_, V7_MOTOR_DIM);
    
    cublasCreate(&cublas_handle_);
    initialized_ = true;
}

void Thalamus::forward(const float* lang_hidden,
                       const float* sense_hidden,
                       float* thalamic_output,
                       int batch_size,
                       cudaStream_t stream) {
    if (!initialized_) {
        std::cerr << "Thalamus not initialized!\n";
        return;
    }
    
    // Temporary buffer for concatenated input
    float* d_combined;
    cudaMalloc(&d_combined, batch_size * V7_THALAMUS_DIM * sizeof(float));
    
    // Concatenate lang_hidden and sense_hidden
    v7Concat(lang_hidden, sense_hidden, d_combined, 
             batch_size, V7_EMBED_DIM, V7_HIDDEN_DIM, stream);
    
    // Linear transformation: combined -> thalamic
    const float alpha = 1.0f;
    const float beta = 0.0f;
    
    cublasSetStream(cublas_handle_, stream);
    cublasSgemm(cublas_handle_,
                CUBLAS_OP_N, CUBLAS_OP_N,
                V7_HIDDEN_DIM, batch_size, V7_THALAMUS_DIM,
                &alpha,
                d_thalamus_weights_, V7_HIDDEN_DIM,
                d_combined, V7_THALAMUS_DIM,
                &beta,
                thalamic_output, V7_HIDDEN_DIM);
    
    // Add bias
    v7AddBias(thalamic_output, d_thalamus_bias_, batch_size, V7_HIDDEN_DIM, stream);
    
    cudaFree(d_combined);
}

void Thalamus::applyTorsionModulation(float* thalamic_output,
                                       int batch_size,
                                       float modulation_scale,
                                       cudaStream_t stream) {
    v7TorsionModulate(thalamic_output, d_torsion_field_, 
                      batch_size, V7_HIDDEN_DIM, modulation_scale, stream);
}

void Thalamus::setTorsionField(const float* values) {
    memcpy(h_torsion_field_, values, V7_HIDDEN_DIM * sizeof(float));
    utils::hostToDevice(d_torsion_field_, h_torsion_field_, V7_HIDDEN_DIM);
}

size_t Thalamus::getParamCount() const {
    return V7_HIDDEN_DIM +                                 // torsion field
           V7_THALAMUS_DIM * V7_HIDDEN_DIM + V7_HIDDEN_DIM +  // thalamus layer
           V7_HIDDEN_DIM * V7_MOTOR_DIM + V7_MOTOR_DIM;       // fusion layer
}

// ============================================================================
// V7Brain Implementation
// ============================================================================

V7Brain::V7Brain()
    : d_lang_hidden_(nullptr)
    , d_lang_motor_(nullptr)
    , d_sense_hidden_(nullptr)
    , d_sense_motor_(nullptr)
    , d_thalamic_(nullptr)
    , d_fusion_out_(nullptr)
    , d_motor_output_(nullptr)
    , max_batch_size_(256)
    , initialized_(false)
    , is_training_(false) {
}

V7Brain::~V7Brain() {
    // Free intermediate buffers
    if (d_lang_hidden_) cudaFree(d_lang_hidden_);
    if (d_lang_motor_) cudaFree(d_lang_motor_);
    if (d_sense_hidden_) cudaFree(d_sense_hidden_);
    if (d_sense_motor_) cudaFree(d_sense_motor_);
    if (d_thalamic_) cudaFree(d_thalamic_);
    if (d_fusion_out_) cudaFree(d_fusion_out_);
    if (d_motor_output_) cudaFree(d_motor_output_);
}

void V7Brain::initialize() {
    // Create sub-modules
    cortex_ = std::make_unique<Cortex>();
    brainstem_ = std::make_unique<Brainstem>();
    thalamus_ = std::make_unique<Thalamus>();
    
    // Initialize each module
    cortex_->initialize();
    brainstem_->initialize();
    thalamus_->initialize();
    
    // Allocate intermediate buffers
    cudaMalloc(&d_lang_hidden_, max_batch_size_ * V7_EMBED_DIM * sizeof(float));
    cudaMalloc(&d_lang_motor_, max_batch_size_ * V7_MOTOR_DIM * sizeof(float));
    cudaMalloc(&d_sense_hidden_, max_batch_size_ * V7_HIDDEN_DIM * sizeof(float));
    cudaMalloc(&d_sense_motor_, max_batch_size_ * V7_MOTOR_DIM * sizeof(float));
    cudaMalloc(&d_thalamic_, max_batch_size_ * V7_HIDDEN_DIM * sizeof(float));
    cudaMalloc(&d_fusion_out_, max_batch_size_ * V7_MOTOR_DIM * sizeof(float));
    cudaMalloc(&d_motor_output_, max_batch_size_ * V7_MOTOR_DIM * sizeof(float));
    
    initialized_ = true;
}

bool V7Brain::isCudaAvailable() const {
    int deviceCount;
    cudaError_t err = cudaGetDeviceCount(&deviceCount);
    return (err == cudaSuccess && deviceCount > 0);
}

V7Brain::ForwardOutput V7Brain::forward(const float* sensory_input,
                                         const int* language_tokens,
                                         int batch_size,
                                         cudaStream_t stream) {
    ForwardOutput output = {nullptr, nullptr, nullptr, nullptr};
    
    if (!initialized_) {
        std::cerr << "V7Brain not initialized!\n";
        return output;
    }
    
    if (batch_size > max_batch_size_) {
        std::cerr << "Batch size too large! Max: " << max_batch_size_ << "\n";
        return output;
    }
    
    // Initialize intermediate buffers to zero (for optional inputs)
    v7FillZero(d_lang_hidden_, batch_size * V7_EMBED_DIM, stream);
    v7FillZero(d_lang_motor_, batch_size * V7_MOTOR_DIM, stream);
    v7FillZero(d_sense_hidden_, batch_size * V7_HIDDEN_DIM, stream);
    v7FillZero(d_sense_motor_, batch_size * V7_MOTOR_DIM, stream);
    
    // Cortical path (language processing)
    if (language_tokens != nullptr) {
        cortex_->forward(language_tokens, d_lang_hidden_, d_lang_motor_, 
                         batch_size, stream);
    }
    
    // Brainstem path (sensory processing)
    if (sensory_input != nullptr) {
        brainstem_->forward(sensory_input, d_sense_hidden_, d_sense_motor_,
                            batch_size, stream);
    }
    
    // Thalamic integration
    thalamus_->forward(d_lang_hidden_, d_sense_hidden_, d_thalamic_,
                       batch_size, stream);
    
    // Apply torsion field modulation
    thalamus_->applyTorsionModulation(d_thalamic_, batch_size, 0.2f, stream);
    
    // Fusion: thalamic -> motor contribution
    const float alpha = 1.0f;
    const float beta = 0.0f;
    
    cublasHandle_t cublas_handle;
    cublasCreate(&cublas_handle);
    cublasSetStream(cublas_handle, stream);
    
    cublasSgemm(cublas_handle,
                CUBLAS_OP_N, CUBLAS_OP_N,
                V7_MOTOR_DIM, batch_size, V7_HIDDEN_DIM,
                &alpha,
                thalamus_->getFusionWeights(), V7_MOTOR_DIM,
                d_thalamic_, V7_HIDDEN_DIM,
                &beta,
                d_fusion_out_, V7_MOTOR_DIM);
    
    // Add fusion bias
    v7AddBias(d_fusion_out_, thalamus_->getFusionBias(), 
              batch_size, V7_MOTOR_DIM, stream);
    
    // Final combination: motor = tanh(lang_motor + sense_motor + fusion_out)
    v7Add3Tanh(d_lang_motor_, d_sense_motor_, d_fusion_out_,
               d_motor_output_, batch_size, V7_MOTOR_DIM, stream);
    
    cublasDestroy(cublas_handle);
    
    // Set output pointers
    output.motor = d_motor_output_;
    output.lang_hidden = d_lang_hidden_;
    output.sense_hidden = d_sense_hidden_;
    output.thalamic = d_thalamic_;
    
    return output;
}

V7Brain::ForwardOutput V7Brain::forwardSensory(const float* sensory_input, 
                                                int batch_size) {
    return forward(sensory_input, nullptr, batch_size);
}

V7Brain::ForwardOutput V7Brain::forwardLanguage(const int* language_tokens, 
                                                 int batch_size) {
    return forward(nullptr, language_tokens, batch_size);
}

V7Brain::ForwardOutput V7Brain::forwardFused(const float* sensory_input,
                                              const int* language_tokens,
                                              int batch_size) {
    return forward(sensory_input, language_tokens, batch_size);
}

float* V7Brain::allocateGradients() {
    size_t param_count = getTotalParamCount();
    float* d_gradients;
    cudaMalloc(&d_gradients, param_count * sizeof(float));
    cudaMemset(d_gradients, 0, param_count * sizeof(float));
    return d_gradients;
}

void V7Brain::zeroGradients(float* gradients) {
    size_t param_count = getTotalParamCount();
    cudaMemset(gradients, 0, param_count * sizeof(float));
}

size_t V7Brain::getTotalParamCount() const {
    if (!cortex_ || !brainstem_ || !thalamus_) return 0;
    
    return cortex_->getParamCount() + 
           brainstem_->getParamCount() + 
           thalamus_->getParamCount();
}

void V7Brain::adjustSpectralDimensions(const float* adjustment_factors) {
    // TODO: Implement dynamic spectral dimension adjustment
    // This would involve adjusting the effective dimensions based on
    // the torsion field and task requirements
}

} // namespace v7
