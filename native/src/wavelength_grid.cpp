#include "wavelength_grid.hpp"
#include <cmath>
namespace wavelength {
bool is_highlight_line(double x, const GridState& s, double tolerance) noexcept {
  if (!s.enabled || !std::isfinite(x) || !std::isfinite(s.origin_meters) ||
      !std::isfinite(s.step_meters) || s.step_meters <= 0 ||
      !std::isfinite(tolerance) || tolerance < 0) return false;
  const double k = (x - s.origin_meters) / s.step_meters;
  if (!std::isfinite(k)) return false;
  return std::abs(k - std::round(k)) * s.step_meters <= tolerance;
}
}
