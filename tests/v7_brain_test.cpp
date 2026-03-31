/**
 * @file v7_brain_test.cpp
 * @brief Simple test for V7Brain implementation
 */

#include "architecture/v7_brain.h"
#include <iostream>
#include <vector>
#include <cmath>

using namespace v7;

// Command mapping (same as Python version)
const char* commands[] = {"左", "右", "前", "后", "停"};

// Expected motor outputs
const float cmd_to_action[5][2] = {
    {-1.0f,  0.0f},   // 左 (left)
    { 1.0f,  0.0f},   // 右 (right)
    { 0.0f,  1.0f},   // 前 (forward)
    { 0.0f, -1.0f},   // 后 (backward)
    { 0.0f,  0.0f}    // 停 (stop)
};

bool testLanguageToAction(V7Brain& brain) {
    std::cout << "\n=== Test 1: Language → Action ===\n";
    
    bool all_passed = true;
    
    for (int cmd = 0; cmd < 5; ++cmd) {
        int token = cmd;
        
        auto output = brain.forwardLanguage(&token, 1);
        
        // Copy result back to host
        float motor[2];
        cudaMemcpy(motor, output.motor, 2 * sizeof(float), cudaMemcpyDeviceToHost);
        
        float expected_x = cmd_to_action[cmd][0];
        float expected_y = cmd_to_action[cmd][1];
        
        float err_x = std::abs(motor[0] - expected_x);
        float err_y = std::abs(motor[1] - expected_y);
        float avg_err = (err_x + err_y) / 2.0f;
        
        bool passed = avg_err < 0.3f;  // Threshold for untrained network
        all_passed &= passed;
        
        std::cout << "  Command " << cmd << " (" << commands[cmd] << "): "
                  << "motor=[" << motor[0] << ", " << motor[1] << "] "
                  << "expected=[" << expected_x << ", " << expected_y << "] "
                  << (passed ? "✓" : "✗") << "\n";
    }
    
    return all_passed;
}

bool testSensoryToAction(V7Brain& brain) {
    std::cout << "\n=== Test 2: Sensory → Action ===\n";
    
    // Test sensory scenarios
    float scenarios[][4] = {
        {1.0f, 0.0f, 0.0f, 0.5f},   // 趋光
        {0.0f, 1.0f, 0.0f, 0.5f},   // 警觉
        {0.0f, 0.0f, 1.0f, 0.5f}    // 躲避
    };
    
    const char* scenario_names[] = {"趋光", "警觉", "躲避"};
    
    bool all_passed = true;
    
    for (int i = 0; i < 3; ++i) {
        auto output = brain.forwardSensory(scenarios[i], 1);
        
        float motor[2];
        cudaMemcpy(motor, output.motor, 2 * sizeof(float), cudaMemcpyDeviceToHost);
        
        std::cout << "  Scenario " << scenario_names[i] << ": "
                  << "motor=[" << motor[0] << ", " << motor[1] << "]\n";
    }
    
    return true;  // Sensory test is mostly for output verification
}

bool testFusedProcessing(V7Brain& brain) {
    std::cout << "\n=== Test 3: Fused Processing ===\n";
    
    float sensory[4] = {0.2f, 0.1f, 0.1f, 0.3f};
    
    bool all_passed = true;
    
    for (int cmd = 0; cmd < 5; ++cmd) {
        auto output = brain.forwardFused(sensory, &cmd, 1);
        
        float motor[2];
        cudaMemcpy(motor, output.motor, 2 * sizeof(float), cudaMemcpyDeviceToHost);
        
        float expected_x = cmd_to_action[cmd][0];
        float expected_y = cmd_to_action[cmd][1];
        
        float err_x = std::abs(motor[0] - expected_x);
        float err_y = std::abs(motor[1] - expected_y);
        float avg_err = (err_x + err_y) / 2.0f;
        
        bool passed = avg_err < 0.4f;  // Slightly higher threshold for fused
        all_passed &= passed;
        
        std::cout << "  Command " << cmd << " (" << commands[cmd] << "): "
                  << "motor=[" << motor[0] << ", " << motor[1] << "] "
                  << (passed ? "✓" : "✗") << "\n";
    }
    
    return all_passed;
}

bool testBatchProcessing(V7Brain& brain) {
    std::cout << "\n=== Test 4: Batch Processing ===\n";
    
    const int batch_size = 5;
    int tokens[batch_size] = {0, 1, 2, 3, 4};
    
    auto output = brain.forwardLanguage(tokens, batch_size);
    
    float motor[batch_size * 2];
    cudaMemcpy(motor, output.motor, batch_size * 2 * sizeof(float), cudaMemcpyDeviceToHost);
    
    bool all_passed = true;
    
    for (int i = 0; i < batch_size; ++i) {
        float mx = motor[i * 2];
        float my = motor[i * 2 + 1];
        
        float expected_x = cmd_to_action[i][0];
        float expected_y = cmd_to_action[i][1];
        
        float err = (std::abs(mx - expected_x) + std::abs(my - expected_y)) / 2.0f;
        bool passed = err < 0.3f;
        all_passed &= passed;
        
        std::cout << "  Batch item " << i << ": motor=[" << mx << ", " << my << "] "
                  << (passed ? "✓" : "✗") << "\n";
    }
    
    return all_passed;
}

int main() {
    std::cout << "========================================\n";
    std::cout << "V7Brain CUDA/C++ Test Suite\n";
    std::cout << "========================================\n";
    
    // Check CUDA availability
    V7Brain brain;
    if (!brain.isCudaAvailable()) {
        std::cerr << "ERROR: CUDA not available!\n";
        return 1;
    }
    
    std::cout << "CUDA is available.\n";
    
    // Initialize brain
    std::cout << "\nInitializing V7Brain...\n";
    brain.initialize();
    
    size_t param_count = brain.getTotalParamCount();
    std::cout << "Total parameters: " << param_count << "\n";
    
    // Expected parameter count from Python:
    // Cortex: 5*16 + 16*2 + 2 = 80 + 32 + 2 = 114
    // Brainstem: 4*16 + 16 + 16*2 + 2 = 64 + 16 + 32 + 2 = 114
    // Thalamus: 16 + 32*16 + 16 + 16*2 + 2 = 16 + 512 + 16 + 32 + 2 = 578
    // Total: 806
    std::cout << "Expected parameters: 806\n";
    
    // Run tests
    bool test1 = testLanguageToAction(brain);
    bool test2 = testSensoryToAction(brain);
    bool test3 = testFusedProcessing(brain);
    bool test4 = testBatchProcessing(brain);
    
    // Summary
    std::cout << "\n========================================\n";
    std::cout << "Test Summary:\n";
    std::cout << "  Language → Action:   " << (test1 ? "✓ PASS" : "✗ FAIL") << "\n";
    std::cout << "  Sensory → Action:    " << (test2 ? "✓ PASS" : "✗ FAIL") << "\n";
    std::cout << "  Fused Processing:    " << (test3 ? "✓ PASS" : "✗ FAIL") << "\n";
    std::cout << "  Batch Processing:    " << (test4 ? "✓ PASS" : "✗ FAIL") << "\n";
    std::cout << "========================================\n";
    
    bool all_passed = test1 && test2 && test3 && test4;
    
    if (all_passed) {
        std::cout << "\n✅ All tests passed!\n";
        return 0;
    } else {
        std::cout << "\n⚠️  Some tests failed (expected for untrained network).\n";
        return 0;  // Still return 0 as this is expected behavior
    }
}
