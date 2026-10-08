#pragma once
#include <cstdint>
namespace wavelength {
struct GridState { bool enabled; double step_meters; double origin_meters; float rgba[4]; };
// Pure mathematical predicate. Renderer integration is NOT implemented.
bool is_highlight_line(double coordinate_meters, const GridState& state, double tolerance_meters) noexcept;
}
