/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "draw_source_assets.hh"
#include "BKE_idprop.hh"
#include "DNA_ID.h"
#include "GPU_texture.hh"
#include "GPU_batch.hh"
#include "GPU_batch_utils.hh"
#include "GPU_index_buffer.hh"
#include "GPU_vertex_buffer.hh"
#include <condition_variable>
#include <deque>
#include <functional>
#include <thread>

namespace blender::draw::source_assets {
namespace src=wavelength::source1;
namespace {
struct MaterialRequest {
  std::atomic<int> state{0};std::shared_ptr<const src::Texture> data;src::Material properties;std::string error;
};
struct Cache {
  std::mutex mutex;std::condition_variable wake;bool stop=false;
  std::deque<std::function<void()>> jobs;
  std::map<std::string,std::shared_ptr<ModelRequest>> models;
  std::map<std::string,std::shared_ptr<MaterialRequest>> materials;
  std::map<std::string,std::shared_ptr<src::Library>> libraries; // Worker thread only.
  std::map<std::string,std::shared_ptr<const src::Texture>> texture_data; // Worker thread only.
  std::map<std::string,Material> gpu_materials; // Draw thread only.
  std::map<const src::Texture *,gpu::Texture *> gpu_textures;
  std::map<const src::Model *,std::unique_ptr<ModelDraw>> gpu_models;
  std::atomic<int> loading{0},errors{0},completed{0};
  size_t resident_bytes=0;
  std::thread worker;
  Cache():worker([this](){run();}){}
  ~Cache()
  {
    {std::lock_guard<std::mutex> lock(mutex);stop=true;jobs.clear();}wake.notify_one();worker.join();
    for(auto &entry:gpu_textures)GPU_texture_free(entry.second);
    for(auto &entry:gpu_models)for(auto *batch:entry.second->batches)if(batch)GPU_batch_discard(batch);
  }
  void run()
  {
    while(true) {
      std::function<void()> job;
      {std::unique_lock<std::mutex> lock(mutex);wake.wait(lock,[this](){return stop || !jobs.empty();});if(stop)return;job=std::move(jobs.front());jobs.pop_front();}
      job();completed++;loading--;
    }
  }
  src::Library &library(const std::string &mounts)
  {
    auto &entry=libraries[mounts];if(!entry)entry=std::make_shared<src::Library>(mounts);return *entry;
  }
  void reserve(size_t bytes)
  {
    /* Predictable bounded cache; an explicit Reload releases the generation.
     * Failed/missing assets stay negative-cached instead of retrying per frame. */
    constexpr size_t budget=512ull*1024*1024;
    if(bytes>budget-resident_bytes)throw std::runtime_error("Native Source asset cache budget exceeded; reload or reduce loaded assets");resident_bytes+=bytes;
  }
  template<typename Request> void enqueue(std::shared_ptr<Request> request,std::function<void()> job)
  {
    loading++;
    jobs.emplace_back([this,request,job=std::move(job)](){
      try{job();request->state.store(1,std::memory_order_release);}
      catch(const std::exception &e){request->error=e.what();std::fprintf(stderr,"wavelength native Source: %s\n",request->error.c_str());errors++;request->state.store(-1,std::memory_order_release);}
    });wake.notify_one();
  }
};
std::unique_ptr<Cache> cache;
Cache &get(){if(!cache)cache=std::make_unique<Cache>();return *cache;}
std::string property(const ID *id,const char *name)
{
  auto *p=id && id->properties?IDP_GetPropertyFromGroup(id->properties,name):nullptr;
  return p && p->type==IDP_STRING?IDP_string_get(p):"";
}
gpu::Texture *upload(const src::Texture &texture)
{
  using gpu::TextureFormat;
  auto format=TextureFormat::SRGB_DXT1;
  if(texture.format==14)format=TextureFormat::SRGB_DXT3;
  else if(texture.format==15)format=TextureFormat::SRGB_DXT5;
  if(texture.format==13 || texture.format==14 || texture.format==15 || texture.format==20)
    return GPU_texture_create_compressed_2d("Source VTF",texture.width,texture.height,1,format,GPU_TEXTURE_USAGE_SHADER_READ,texture.payload.data());
  /* Original uncompressed VTFs need channel swizzles, never Blender Images. */
  std::vector<uint8_t> rgba(size_t(texture.width)*texture.height*4,255);
  size_t stride=texture.format==2 || texture.format==3?3:(texture.format==5 || texture.format==8?1:4);
  for(size_t i=0;i<rgba.size()/4;i++) {
    auto *p=texture.payload.data()+i*stride;auto *out=rgba.data()+i*4;
    if(texture.format==5){out[0]=out[1]=out[2]=p[0];}
    else if(texture.format==8){out[0]=out[1]=out[2]=255;out[3]=p[0];}
    else if(texture.format==1){out[0]=p[3];out[1]=p[2];out[2]=p[1];out[3]=p[0];}
    else if(texture.format==12){out[0]=p[1];out[1]=p[2];out[2]=p[3];out[3]=p[0];}
    else {bool bgr=texture.format==3 || texture.format==11 || texture.format==16;out[0]=p[bgr?2:0];out[1]=p[1];out[2]=p[bgr?0:2];if(stride==4 && texture.format!=16)out[3]=p[3];}
  }
  auto *result=GPU_texture_create_2d("Source VTF",texture.width,texture.height,1,TextureFormat::SRGBA_8_8_8_8,GPU_TEXTURE_USAGE_SHADER_READ,nullptr);
  if(result)GPU_texture_update(result,GPU_DATA_UBYTE,rgba.data());return result;
}
} // namespace

std::shared_ptr<ModelRequest> model(const std::string &mounts,const std::string &path,int skin,int body,const std::string &revision)
{
  auto &c=get();auto key=mounts+"\nMODEL "+path+" "+std::to_string(skin)+" "+std::to_string(body)+"\n"+revision;
  std::lock_guard<std::mutex> lock(c.mutex);auto found=c.models.find(key);if(found!=c.models.end())return found->second;
  auto request=std::make_shared<ModelRequest>();
  if(c.models.size()+c.materials.size()>=4096){request->error="Native Source request limit";request->state=-1;return request;}
  c.models[key]=request;
  c.enqueue<ModelRequest>(request,[&c,request,mounts,path,skin,body](){
    auto data=std::make_shared<src::Model>(src::load_model(c.library(mounts),path,skin,body));
    size_t bytes=data->vertices.size()*sizeof(src::Vertex);for(auto &s:data->surfaces)bytes+=s.indices.size()*sizeof(uint32_t);c.reserve(bytes);request->data=std::move(data);
  });return request;
}
Material material(const std::string &mounts,const std::string &path,const std::vector<std::string> &directories,const std::string &revision)
{
  auto &c=get();auto key=mounts+"\nMATERIAL "+path+"\n"+revision;for(auto &dir:directories)key+="\n"+dir;
  auto gpu=c.gpu_materials.find(key);if(gpu!=c.gpu_materials.end())return gpu->second;
  std::shared_ptr<MaterialRequest> request;
  {
    std::lock_guard<std::mutex> lock(c.mutex);auto found=c.materials.find(key);
    if(found!=c.materials.end())request=found->second;
    else {
      if(c.models.size()+c.materials.size()>=4096)return {};
      request=std::make_shared<MaterialRequest>();c.materials[key]=request;
      c.enqueue<MaterialRequest>(request,[&c,request,mounts,path,directories](){
        auto &library=c.library(mounts);auto dirs=directories;dirs.push_back("");std::string error;
        bool resolved=false;
        for(auto &dir:dirs)try {
          auto candidate=dir;std::replace(candidate.begin(),candidate.end(),'\\','/');
          while(!candidate.empty() && candidate.back()=='/')candidate.pop_back();
          while(!candidate.empty() && candidate.front()=='/')candidate.erase(candidate.begin());
          if(!candidate.empty())candidate+='/';
          request->properties=src::load_material(library,candidate+path);resolved=true;break;
        }catch(const std::exception &e){error=e.what();}
        if(!resolved)throw std::runtime_error(error);
        auto texture_path=src::asset_path(request->properties.base);if(texture_path.rfind("materials/",0)!=0)texture_path="materials/"+texture_path;if(texture_path.size()<4 || texture_path.substr(texture_path.size()-4)!=".vtf")texture_path+=".vtf";
        auto texture_key=mounts+"\n"+library.fingerprint(texture_path);
        auto &texture=c.texture_data[texture_key];
        if(!texture){auto data=std::make_shared<src::Texture>(src::load_texture(library,request->properties.base));c.reserve(data->payload.size());texture=std::move(data);}
        request->data=texture;
      });return {};
    }
  }
  if(request->state.load(std::memory_order_acquire)!=1)return {};
  auto &texture=c.gpu_textures[request->data.get()];if(!texture)texture=upload(*request->data);
  Material result{&texture,request->properties.alpha_test,request->properties.translucent};c.gpu_materials[key]=result;return result;
}
Material material(const ID *id)
{
  auto mounts=property(id,"wl_source_mounts"),path=property(id,"wl_source_native_material");
  if(mounts.empty() || path.empty())return {};return material(mounts,path,{},property(id,"wl_source_revision"));
}
const ModelDraw *model_draw(const ID *id)
{
  auto mounts=property(id,"wl_source_mounts"),path=property(id,"wl_source_native_model");
  if(mounts.empty() || path.empty())return nullptr;
  auto integer=[&](const char *name){auto *p=IDP_GetPropertyFromGroup(id->properties,name);return p && p->type==IDP_INT?IDP_int_get(p):0;};
  auto request=model(mounts,path,integer("wl_source_skin"),integer("wl_source_body"),property(id,"wl_source_revision"));
  if(request->state.load(std::memory_order_acquire)!=1)return nullptr;
  auto &c=get();auto found=c.gpu_models.find(request->data.get());if(found!=c.gpu_models.end())return found->second.get();
  const auto &data=*request->data;auto draw=std::make_unique<ModelDraw>();draw->materials=data.materials;draw->directories=data.directories;draw->mounts=mounts;
  std::array<float,3> low=data.vertices[0].position,high=low;
  struct Vertex {float pos[3],nor[3],ac[4],au[2];};std::vector<Vertex> vertices;vertices.reserve(data.vertices.size());
  for(auto &v:data.vertices) {
    Vertex out{};for(int i=0;i<3;i++){out.pos[i]=v.position[i];out.nor[i]=v.normal[i];low[i]=std::min(low[i],v.position[i]);high[i]=std::max(high[i],v.position[i]);}
    for(int i=0;i<4;i++)out.ac[i]=1;out.au[0]=v.uv[0];out.au[1]=1.0f-v.uv[1];vertices.push_back(out);
  }
  for(int i=0;i<3;i++){draw->center[i]=(low[i]+high[i])*.5f;draw->half[i]=std::max((high[i]-low[i])*.5f,.001f);}
  GPUVertFormat format{};GPU_vertformat_attr_add_legacy(&format,"pos",GPU_COMP_F32,3,GPU_FETCH_FLOAT);GPU_vertformat_attr_add_legacy(&format,"nor",GPU_COMP_F32,3,GPU_FETCH_FLOAT);GPU_vertformat_attr_add_legacy(&format,"ac",GPU_COMP_F32,4,GPU_FETCH_FLOAT);GPU_vertformat_attr_add_legacy(&format,"au",GPU_COMP_F32,2,GPU_FETCH_FLOAT);
  auto *vbo=GPU_vertbuf_create_with_format(format);GPU_vertbuf_data_alloc(*vbo,vertices.size());vbo->data<Vertex>().copy_from(Span<Vertex>(vertices.data(),vertices.size()));
  bool first=true;
  for(auto &surface:data.surfaces) {
    if(surface.indices.empty()){draw->batches.push_back(nullptr);continue;}
    GPUIndexBufBuilder builder;GPU_indexbuf_init(&builder,GPU_PRIM_TRIS,surface.indices.size()/3,vertices.size());
    for(size_t i=0;i<surface.indices.size();i+=3)GPU_indexbuf_add_tri_verts(&builder,surface.indices[i],surface.indices[i+1],surface.indices[i+2]);
    auto *ibo=GPU_indexbuf_build(&builder);auto *batch=GPU_batch_create_ex(GPU_PRIM_TRIS,vbo,ibo,first?GPU_BATCH_OWNS_VBO|GPU_BATCH_OWNS_INDEX:GPU_BATCH_OWNS_INDEX);first=false;draw->batches.push_back(batch);
  }
  auto *result=draw.get();c.gpu_models[data.vertices.empty()?nullptr:request->data.get()]=std::move(draw);return result;
}
int pending(){return cache?cache->loading.load():0;}
int failures(){return cache?cache->errors.load():0;}
int revision(){return cache?cache->completed.load():0;}
bool scene_enabled(const ID *id)
{
  auto *p=id && id->properties?IDP_GetPropertyFromGroup(id->properties,"wl_native_source_scene"):nullptr;
  return p && ELEM(p->type,IDP_BOOLEAN,IDP_INT) && p->data.val!=0;
}
void clear(){cache.reset();}
} // namespace blender::draw::source_assets

