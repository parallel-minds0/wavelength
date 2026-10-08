#include "wavelength_abi.h"
#include "wavelength_grid.hpp"
extern "C" WL_API unsigned int wl_native_abi_version(void) { return WL_NATIVE_ABI_VERSION; }
extern "C" WL_API int wl_grid_is_highlight_line(double coordinate_meters, double origin_meters,
                                                 double step_meters, double tolerance_meters,
                                                 int enabled) {
    const wavelength::GridState state{enabled != 0, step_meters, origin_meters, {1.f, 1.f, 0.f, 1.f}};
    return wavelength::is_highlight_line(coordinate_meters, state, tolerance_meters) ? 1 : 0;
}
