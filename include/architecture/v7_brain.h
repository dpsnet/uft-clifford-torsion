/**
 * @file v7_brain.h
 * @brief V7Brain - Unified Brain Architecture with Cortex, Brainstem, and Thalamus
 * 
 * Three-layer architecture:
 * - Cortex: High-level cognitive processing (language)
 * - Brainstem: Basic reflexes and sensory processing
 * - Thalamus: Unified modulation and routing interface
 * 
 * Features:
 * - Bidirectional information flow
 * - Torsion field global modulation
 * - Sensory-motor mapping
 * - Spectral dimension dynamic adjustment
 */

#ifndef V7_BRAIN_H
#define V7_BRAIN_H

#include <cuda_runtime.h>
#include <cublas_v2.h>
#include <cudnn.h>
#include <vector>
#include <memory>

namespace v7 {

// Configuration constants
constexpr int V7_VOCAB_SIZE = 5;      // Language vocabulary size
constexpr int V7_EMBED_DIM = 16;      // Embedding dimension
constexpr int V7_SENSOR_DIM = 4;      // Sensory input dimension
constexpr int V7_MOTOR_DIM = 2;       // Motor output dimension
constexpr int V7_HIDDEN_DIM = 16;     // Hidden layer dimension
constexpr int V7_THALAMUS_DIM = 32;   // Combined input to thalamus

/**
 * @brief Cortex module - High-level cognitive processing
 * 
 * Handles language input and converts to motor commands
 * through learned embeddings and linear transformations.
 */
class Cortex {
public:
    Cortex();
    ~Cortex();

    // Initialize weights on host and device
    void initialize();
    
    // Forward pass: language token -> motor output + hidden state
    void forward(const int* language_tokens,      // [batch_size]
                 float* lang_hidden,               // [batch_size, EMBED_DIM]
                 float* lang_motor,                // [batch_size, MOTOR_DIM]
                 int batch_size,
                 cudaStream_t stream = 0);

    // Getters for weights (for training/loading)
    float* getEmbeddingWeights() { return d_embedding_weights_; }
    float* getLangToMotorWeights() { return d_lang_to_motor_weights_; }
    float* getLangToMotorBias() { return d_lang_to_motor_bias_; }

    size_t getParamCount() const;

private:
    // Host weights
    float* h_embedding_weights_;      // [VOCAB_SIZE, EMBED_DIM]
    float* h_lang_to_motor_weights_;  // [EMBED_DIM, MOTOR_DIM]
    float* h_lang_to_motor_bias_;     // [MOTOR_DIM]

    // Device weights
    float* d_embedding_weights_;
    float* d_lang_to_motor_weights_;
    float* d_lang_to_motor_bias_;

    // cuBLAS handle
    cublasHandle_t cublas_handle_;
    bool initialized_;
};

/**
 * @brief Brainstem module - Basic reflexes and sensory processing
 * 
 * Processes raw sensory input and generates reflexive motor responses.
 * Uses ReLU activation for non-linear sensory processing.
 */
class Brainstem {
public:
    Brainstem();
    ~Brainstem();

    void initialize();
    
    // Forward pass: sensory input -> motor output + hidden state
    void forward(const float* sensory_input,       // [batch_size, SENSOR_DIM]
                 float* sense_hidden,               // [batch_size, HIDDEN_DIM]
                 float* sense_motor,                // [batch_size, MOTOR_DIM]
                 int batch_size,
                 cudaStream_t stream = 0);

    float* getSensorWeights() { return d_sensor_weights_; }
    float* getSensorBias() { return d_sensor_bias_; }
    float* getSensorToMotorWeights() { return d_sensor_to_motor_weights_; }
    float* getSensorToMotorBias() { return d_sensor_to_motor_bias_; }

    size_t getParamCount() const;

private:
    // Host weights
    float* h_sensor_weights_;           // [SENSOR_DIM, HIDDEN_DIM]
    float* h_sensor_bias_;              // [HIDDEN_DIM]
    float* h_sensor_to_motor_weights_;  // [HIDDEN_DIM, MOTOR_DIM]
    float* h_sensor_to_motor_bias_;     // [MOTOR_DIM]

    // Device weights
    float* d_sensor_weights_;
    float* d_sensor_bias_;
    float* d_sensor_to_motor_weights_;
    float* d_sensor_to_motor_bias_;

    cublasHandle_t cublas_handle_;
    bool initialized_;
};

/**
 * @brief Thalamus interface - Unified modulation and routing
 * 
 * Combines cortical and brainstem representations, applies
torsion field modulation, and produces unified output.
 */
class Thalamus {
public:
    Thalamus();
    ~Thalamus();

    void initialize();
    
    // Forward pass: combine cortical and brainstem hidden states
    void forward(const float* lang_hidden,        // [batch_size, EMBED_DIM]
                 const float* sense_hidden,        // [batch_size, HIDDEN_DIM]
                 float* thalamic_output,           // [batch_size, HIDDEN_DIM]
                 int batch_size,
                 cudaStream_t stream = 0);

    // Torsion field modulation
    void applyTorsionModulation(float* thalamic_output,
                                int batch_size,
                                float modulation_scale = 0.2f,
                                cudaStream_t stream = 0);

    // Getters/setters for torsion field (learnable parameter)
    float* getTorsionField() { return d_torsion_field_; }
    void setTorsionField(const float* values);  // [HIDDEN_DIM]

    float* getThalamusWeights() { return d_thalamus_weights_; }
    float* getThalamusBias() { return d_thalamus_bias_; }
    float* getFusionWeights() { return d_fusion_weights_; }
    float* getFusionBias() { return d_fusion_bias_; }

    size_t getParamCount() const;

private:
    // Torsion field (learnable modulation parameter)
    float* h_torsion_field_;      // [HIDDEN_DIM]
    float* d_torsion_field_;

    // Thalamus transformation: 32 -> 16
    float* h_thalamus_weights_;   // [THALAMUS_DIM, HIDDEN_DIM]
    float* h_thalamus_bias_;      // [HIDDEN_DIM]
    float* d_thalamus_weights_;
    float* d_thalamus_bias_;

    // Fusion transformation: 16 -> 2
    float* h_fusion_weights_;     // [HIDDEN_DIM, MOTOR_DIM]
    float* h_fusion_bias_;        // [MOTOR_DIM]
    float* d_fusion_weights_;
    float* d_fusion_bias_;

    cublasHandle_t cublas_handle_;
    bool initialized_;
};

/**
 * @brief V7Brain - Complete unified brain architecture
 * 
 * Integrates Cortex, Brainstem, and Thalamus into a cohesive system
 * with bidirectional information flow and torsion field modulation.
 */
class V7Brain {
public:
    V7Brain();
    ~V7Brain();

    // Initialize all modules
    void initialize();
    
    // Check if CUDA is available
    bool isCudaAvailable() const;

    // Main forward pass
    struct ForwardOutput {
        float* motor;           // [batch_size, MOTOR_DIM] - final motor output
        float* lang_hidden;     // [batch_size, EMBED_DIM] - cortical representation
        float* sense_hidden;    // [batch_size, HIDDEN_DIM] - brainstem representation
        float* thalamic;        // [batch_size, HIDDEN_DIM] - thalamic output
    };

    // Forward with optional inputs (can be null)
    ForwardOutput forward(const float* sensory_input,    // [batch_size, SENSOR_DIM] or nullptr
                          const int* language_tokens,     // [batch_size] or nullptr
                          int batch_size,
                          cudaStream_t stream = 0);

    // Convenience methods for single-modality inference
    ForwardOutput forwardSensory(const float* sensory_input, int batch_size);
    ForwardOutput forwardLanguage(const int* language_tokens, int batch_size);
    ForwardOutput forwardFused(const float* sensory_input,
                                const int* language_tokens,
                                int batch_size);

    // Get individual modules for advanced use
    Cortex* getCortex() { return cortex_.get(); }
    Brainstem* getBrainstem() { return brainstem_.get(); }
    Thalamus* getThalamus() { return thalamus_.get(); }

    // Training support
    float* allocateGradients();
    void zeroGradients(float* gradients);
    size_t getTotalParamCount() const;
    
    // Utility functions
    void setTrainingMode(bool training) { is_training_ = training; }
    bool isTraining() const { return is_training_; }

    // Spectral dimension adjustment (dynamic)
    void adjustSpectralDimensions(const float* adjustment_factors);

private:
    std::unique_ptr<Cortex> cortex_;
    std::unique_ptr<Brainstem> brainstem_;
    std::unique_ptr<Thalamus> thalamus_;

    // Intermediate buffers
    float* d_lang_hidden_;
    float* d_lang_motor_;
    float* d_sense_hidden_;
    float* d_sense_motor_;
    float* d_thalamic_;
    float* d_fusion_out_;
    float* d_motor_output_;

    int max_batch_size_;
    bool initialized_;
    bool is_training_;
};

/**
 * @brief Utility functions for V7Brain
 */
namespace utils {
    // Initialize random weights with Xavier initialization
    void xavierInit(float* weights, int fan_in, int fan_out, unsigned seed = 42);
    
    // Initialize zeros
    void zeroInit(float* data, int count);
    
    // Copy between host and device
    void hostToDevice(float* d_dst, const float* h_src, size_t count);
    void deviceToHost(float* h_dst, const float* d_src, size_t count);
    
    // Tanh activation (in-place)
    void tanhActivation(float* data, int count, cudaStream_t stream = 0);
    
    // ReLU activation (in-place)
    void reluActivation(float* data, int count, cudaStream_t stream = 0);
}

} // namespace v7

#endif // V7_BRAIN_H
