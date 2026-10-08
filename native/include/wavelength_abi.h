#pragma once
/* Stable, Blender-independent C ABI for the Wavelength grid prototype. */
#ifdef _WIN32
#  ifdef WAVELENGTH_NATIVE_BUILD
#    define WL_API __declspec(dllexport)
#  else
#    define WL_API __declspec(dllimport)
#  endif
#else
#  define WL_API __attribute__((visibility("default")))
#endif
#ifdef __cplusplus
extern "C" {
#endif
#define WL_NATIVE_ABI_VERSION 1
/* Returns 1 for a highlighted line, 0 otherwise. Inputs are in Blender meters. */
WL_API int wl_grid_is_highlight_line(double coordinate_meters, double origin_meters,
                                     double step_meters, double tolerance_meters, int enabled);
WL_API unsigned int wl_native_abi_version(void);
#ifdef __cplusplus
}
#endif
