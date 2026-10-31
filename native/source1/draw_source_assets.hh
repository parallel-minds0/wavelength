/* SPDX-License-Identifier: GPL-2.0-or-later */
#pragma once
#include "assets.hh"
#include <atomic>
struct ID;
namespace blender::gpu {class Texture;}
namespace blender::gpu {class Batch;}
namespace blender::draw::source_assets {
struct Material {
  gpu::Texture **texture=nullptr;
  bool alpha_test=false,translucent=false;
};
struct ModelRequest {
  std::atomic<int> state{0}; // 0 queued/loading, 1 ready, -1 failed.
  std::shared_ptr<const wavelength::source1::Model> data;
  std::string error;
};
struct ModelDraw {
  std::vector<gpu::Batch *> batches;
  std::vector<std::string> materials,directories;
  std::string mounts;
  std::array<float,3> center{},half{};
};
const ModelDraw *model_draw(const ID *id);
std::shared_ptr<ModelRequest> model(const std::string &mounts,const std::string &path,int skin,int body,const std::string &revision={});
Material material(const std::string &mounts,const std::string &path,const std::vector<std::string> &directories={},const std::string &revision={});
Material material(const ID *id);
int pending();
int failures();
int revision();
bool scene_enabled(const ID *id);
void clear();
} // namespace blender::draw::source_assets
