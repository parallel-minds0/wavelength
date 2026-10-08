cmake_minimum_required(VERSION 3.16)
project(wavelength_native LANGUAGES CXX)
add_library(wavelength_grid SHARED src/wavelength_grid.cpp src/wavelength_abi.cpp)
target_include_directories(wavelength_grid PUBLIC include)
target_compile_features(wavelength_grid PUBLIC cxx_std_17)
target_compile_definitions(wavelength_grid PRIVATE WAVELENGTH_NATIVE_BUILD)
# This is a standalone native library; it does not hook Blender's renderer.
