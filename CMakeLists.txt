# =============================================================================
# Phase-Aware Loss Module - CMake Configuration
# =============================================================================
# CUDA/C++ implementation of PhaseAwareLoss from Python
# =============================================================================

cmake_minimum_required(VERSION 3.18 FATAL_ERROR)
project(PhaseAwareLoss VERSION 1.0.0 LANGUAGES CXX CUDA)

# =============================================================================
# C++ and CUDA Standards
# =============================================================================
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CUDA_STANDARD 17)
set(CMAKE_CUDA_STANDARD_REQUIRED ON)

# =============================================================================
# Find Packages
# =============================================================================
find_package(Torch REQUIRED)
find_package(CUDA REQUIRED)

# =============================================================================
# CUDA Architecture Settings
# =============================================================================
if(NOT DEFINED CMAKE_CUDA_ARCHITECTURES)
    # Support common architectures (adjust based on your target GPUs)
    set(CMAKE_CUDA_ARCHITECTURES 70 75 80 86 89 90)
endif()

# =============================================================================
# CUDA Compilation Flags
# =============================================================================
set(CUDA_NVCC_FLAGS ${CUDA_NVCC_FLAGS}
    -O3
    --use_fast_math
    -lineinfo
    -Xcompiler -fPIC
)

# Debug build flags
if(CMAKE_BUILD_TYPE STREQUAL "Debug")
    list(APPEND CUDA_NVCC_FLAGS -g -G)
endif()

# =============================================================================
# Include Directories
# =============================================================================
include_directories(
    ${CMAKE_CURRENT_SOURCE_DIR}/include
    ${TORCH_INCLUDE_DIRS}
    ${CUDA_INCLUDE_DIRS}
)

# =============================================================================
# Source Files
# =============================================================================
# Core C++ implementation
set(CORE_SOURCES
    src/core/phase_aware_loss.cpp
)

# CUDA kernel sources
set(CUDA_SOURCES
    kernels/phase_loss_kernels.cu
)

# =============================================================================
# CUDA Object Library
# =============================================================================
# Compile CUDA kernels separately to enable parallel compilation
add_library(phase_loss_kernels OBJECT ${CUDA_SOURCES})
set_target_properties(phase_loss_kernels PROPERTIES
    POSITION_INDEPENDENT_CODE ON
    CUDA_SEPARABLE_COMPILATION ON
    CUDA_RESOLVE_DEVICE_SYMBOLS ON
)

target_include_directories(phase_loss_kernels PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/include
    ${TORCH_INCLUDE_DIRS}
    ${CUDA_INCLUDE_DIRS}
)

# =============================================================================
# Main Library
# =============================================================================
# Create shared library for Phase-Aware Loss module
add_library(phase_aware_loss SHARED 
    ${CORE_SOURCES}
    $<TARGET_OBJECTS:phase_loss_kernels>
)

target_link_libraries(phase_aware_loss
    ${TORCH_LIBRARIES}
    ${CUDA_LIBRARIES}
    cudart
)

set_target_properties(phase_aware_loss PROPERTIES
    POSITION_INDEPENDENT_CODE ON
    CUDA_SEPARABLE_COMPILATION ON
    LIBRARY_OUTPUT_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/lib
    RUNTIME_OUTPUT_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/bin
)

# =============================================================================
# Static Library (optional, for linking into other projects)
# =============================================================================
add_library(phase_aware_loss_static STATIC 
    ${CORE_SOURCES}
    $<TARGET_OBJECTS:phase_loss_kernels>
)

target_link_libraries(phase_aware_loss_static
    ${TORCH_LIBRARIES}
    ${CUDA_LIBRARIES}
    cudart
)

set_target_properties(phase_aware_loss_static PROPERTIES
    POSITION_INDEPENDENT_CODE ON
    CUDA_SEPARABLE_COMPILATION ON
    ARCHIVE_OUTPUT_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/lib
)

# =============================================================================
# Python Extension (PyTorch C++ Extension)
# =============================================================================
# Uncomment if you want to build as a Python extension module
# find_package(pybind11 REQUIRED)
# pybind11_add_module(phase_aware_loss_py 
#     src/core/phase_aware_loss.cpp
#     src/bindings/python_bindings.cpp
#     $<TARGET_OBJECTS:phase_loss_kernels>
# )
# target_link_libraries(phase_aware_loss_py PRIVATE 
#     ${TORCH_LIBRARIES}
#     ${CUDA_LIBRARIES}
# )

# =============================================================================
# Tests
# =============================================================================
option(BUILD_TESTS "Build test executables" ON)

if(BUILD_TESTS)
    enable_testing()
    
    # Test executable for phase-aware loss
    add_executable(test_phase_aware_loss
        tests/test_phase_aware_loss.cpp
    )
    
    target_link_libraries(test_phase_aware_loss
        phase_aware_loss_static
        ${TORCH_LIBRARIES}
        ${CUDA_LIBRARIES}
    )
    
    set_target_properties(test_phase_aware_loss PROPERTIES
        RUNTIME_OUTPUT_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/bin
    )
    
    # Add test
    add_test(NAME PhaseAwareLossTest 
             COMMAND test_phase_aware_loss
             WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR})
endif()

# =============================================================================
# Benchmark
# =============================================================================
option(BUILD_BENCHMARK "Build benchmark executable" ON)

if(BUILD_BENCHMARK)
    add_executable(benchmark_phase_loss
        benchmarks/benchmark_phase_loss.cpp
    )
    
    target_link_libraries(benchmark_phase_loss
        phase_aware_loss_static
        ${TORCH_LIBRARIES}
        ${CUDA_LIBRARIES}
    )
    
    set_target_properties(benchmark_phase_loss PROPERTIES
        RUNTIME_OUTPUT_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/bin
    )
endif()

# =============================================================================
# Installation
# =============================================================================
install(TARGETS phase_aware_loss phase_aware_loss_static
    LIBRARY DESTINATION lib
    ARCHIVE DESTINATION lib
    RUNTIME DESTINATION bin
)

install(DIRECTORY include/
    DESTINATION include
    FILES_MATCHING PATTERN "*.h" PATTERN "*.hpp"
)

# =============================================================================
# Print Configuration Summary
# =============================================================================
message(STATUS "")
message(STATUS "Phase-Aware Loss Module Configuration:")
message(STATUS "  Version:        ${PROJECT_VERSION}")
message(STATUS "  C++ Standard:   ${CMAKE_CXX_STANDARD}")
message(STATUS "  CUDA Standard:  ${CMAKE_CUDA_STANDARD}")
message(STATUS "  CUDA Architectures: ${CMAKE_CUDA_ARCHITECTURES}")
message(STATUS "  Torch Version:  ${Torch_VERSION}")
message(STATUS "  Build Type:     ${CMAKE_BUILD_TYPE}")
message(STATUS "  Build Tests:    ${BUILD_TESTS}")
message(STATUS "  Build Benchmark: ${BUILD_BENCHMARK}")
message(STATUS "")
