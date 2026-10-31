/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "assets.hh"
#include <iostream>
#include <random>
using namespace wavelength::source1;
template<typename F> void rejects(F fn) {bool failed=false;try{fn();}catch(const std::exception &){failed=true;}if(!failed)throw std::runtime_error("Malformed input accepted");}
template<typename T> void put(Bytes &b,size_t at,T v){if(b.size()<at+sizeof(T))b.resize(at+sizeof(T));std::memcpy(b.data()+at,&v,sizeof(T));}
int main(int argc,char **argv)
{
  try {
    rejects([](){asset_path("../outside");});rejects([](){asset_path("C:/outside");});
    Bytes b(80+8);std::memcpy(b.data(),"VTF\0",4);put<int32_t>(b,4,7);put<int32_t>(b,8,2);put<uint32_t>(b,12,80);
    put<uint16_t>(b,16,4);put<uint16_t>(b,18,4);put<uint16_t>(b,24,1);put<int32_t>(b,52,13);put<uint8_t>(b,56,1);put<uint16_t>(b,63,1);
    auto texture=read_vtf(b);if(texture.payload.size()!=8 || texture.width!=4)throw std::runtime_error("DXT payload changed");
    b.pop_back();rejects([&](){read_vtf(b);});
    std::string kv="LightmappedGeneric { \"$basetexture\" \"brick/test\" // comment\n \"$alphatest\" 1 }";
    auto parsed=keyvalues(Bytes(kv.begin(),kv.end()));if(parsed.size()!=1 || parsed[0].key!="lightmappedgeneric" || parsed[0].children.size()!=2)throw std::runtime_error("VMT parse failed");
    kv="VertexLitGeneric { \"$envmap\" \"\" }";parsed=keyvalues(Bytes(kv.begin(),kv.end()));if(parsed[0].children[0].value!="")throw std::runtime_error("Empty VMT value rejected");
    std::mt19937 rng(42);
    for(int i=0;i<1000;i++) {
      Bytes malformed(rng()%512);for(auto &v:malformed)v=uint8_t(rng());
      rejects([&](){read_vtf(malformed);});
      Bytes mdl(512),vvd(512),vtx(512);for(auto *data:{&mdl,&vvd,&vtx})for(auto &v:*data)v=uint8_t(rng());
      std::memcpy(mdl.data(),"IDST",4);put<int32_t>(mdl,4,49);put<int32_t>(mdl,8,42);put<int32_t>(mdl,76,512);
      std::memcpy(vvd.data(),"IDSV",4);put<int32_t>(vvd,4,4);put<int32_t>(vvd,8,42);put<int32_t>(vvd,12,1);put<int32_t>(vvd,16,1);put<int32_t>(vvd,48,0);put<int32_t>(vvd,52,64);put<int32_t>(vvd,56,64);
      put<int32_t>(vtx,0,7);put<int32_t>(vtx,16,42);put<int32_t>(vtx,20,1);
      rejects([&](){read_model(mdl,vvd,vtx);});
    }
    if(argc>2) {
      std::string mounts;std::ifstream input(argv[1]);std::getline(input,mounts,'\0');Library library(mounts);
      auto model=load_model(library,argv[2]);size_t triangles=0;for(auto &surface:model.surfaces)triangles+=surface.indices.size()/3;
      std::cout<<"MODEL "<<model.vertices.size()<<" vertices "<<triangles<<" triangles "<<model.materials.size()<<" materials\n";
      for(auto &surface:model.surfaces)if(!surface.indices.empty()) {
        bool loaded=false;
        for(auto &dir:model.directories)try {
          auto mat=load_material(library,dir+model.materials[surface.material]);auto tex=load_texture(library,mat.base);
          std::cout<<"VTF "<<tex.width<<"x"<<tex.height<<" format "<<tex.format<<" original bytes "<<tex.payload.size()<<"\n";loaded=true;break;
        }catch(const std::exception &){}
        if(!loaded)std::cout<<"MATERIAL unavailable "<<model.materials[surface.material]<<"\n";
      }
    }
    std::cout<<"PASS native Source readers: original DXT blocks, VMT tokens, bounds, 2000 malformed-input rejections\n";
  }catch(const std::exception &e){std::cerr<<e.what()<<"\n";return 1;}
}
