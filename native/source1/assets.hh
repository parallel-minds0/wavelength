/* SPDX-License-Identifier: GPL-2.0-or-later */
#pragma once
#include <algorithm>
#include <array>
#include <cmath>
#include <cctype>
#include <cstdio>
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <map>
#include <memory>
#include <mutex>
#include <stdexcept>
#include <string>
#include <vector>
#include <unordered_map>

namespace wavelength::source1 {
using Bytes = std::vector<uint8_t>;
constexpr size_t byte_limit = 128 * 1024 * 1024;
constexpr size_t element_limit = 2000000;

/* All disk offsets are checked before dereferencing. No packed structure casts,
 * platform alignment assumptions, or executable material proxies are used. */
struct Reader {
  const Bytes &bytes;
  void bounds(size_t at, size_t length) const
  {
    if (at > bytes.size() || length > bytes.size() - at) throw std::runtime_error("Truncated Source asset");
  }
  template<typename T> T get(size_t at) const
  {
    bounds(at, sizeof(T)); T value; std::memcpy(&value, bytes.data() + at, sizeof(T)); return value;
  }
  int i(size_t at) const { return get<int32_t>(at); }
  size_t table(size_t at, int count, size_t stride) const
  {
    if (count < 0 || size_t(count) > element_limit) throw std::runtime_error("Source table exceeds limit");
    bounds(at, size_t(count) * stride); return at;
  }
  size_t relative(size_t base, int offset) const
  {
    if (offset < 0 || size_t(offset) > bytes.size() || base > bytes.size() - size_t(offset)) throw std::runtime_error("Invalid Source offset");
    return base + size_t(offset);
  }
  std::string string(size_t at) const
  {
    bounds(at, 1); size_t end=at;
    while (end < bytes.size() && end-at < 4096 && bytes[end]) end++;
    if (end == bytes.size() || end-at == 4096) throw std::runtime_error("Unterminated Source string");
    return std::string(reinterpret_cast<const char *>(bytes.data()+at), end-at);
  }
};

inline std::string asset_path(std::string path)
{
  std::replace(path.begin(), path.end(), '\\', '/');
  std::transform(path.begin(), path.end(), path.begin(), [](unsigned char c){return char(std::tolower(c));});
  if (path.empty() || path[0]=='/' || path.find(':')!=std::string::npos) throw std::runtime_error("Invalid Source asset path");
  for (size_t start=0; start<path.size();) {
    size_t end=path.find('/',start); if(end==std::string::npos)end=path.size();
    auto part=path.substr(start,end-start);
    if(part==".." || part==".")throw std::runtime_error("Invalid Source asset path");
    start=end+1;
  }
  return path;
}

inline Bytes file_range(const std::filesystem::path &path, size_t at, size_t size)
{
  if(size>byte_limit)throw std::runtime_error("Source asset exceeds byte limit");
  std::ifstream stream(path,std::ios::binary);
  if(!stream)throw std::runtime_error("Source file not found: "+path.string());
  stream.seekg(0,std::ios::end);auto total=stream.tellg();
  if(total<0 || at>size_t(total) || size>size_t(total)-at)throw std::runtime_error("Truncated Source file");
  stream.seekg(at);Bytes result(size);
  if(size && !stream.read(reinterpret_cast<char *>(result.data()),size))throw std::runtime_error("Cannot read Source asset");
  return result;
}
inline Bytes file(const std::filesystem::path &path)
{
  return file_range(path,0,std::filesystem::file_size(path));
}
inline uint32_t crc32(const Bytes &bytes)
{
  static const auto table=[](){std::array<uint32_t,256> result{};for(uint32_t n=0;n<256;n++){uint32_t c=n;for(int i=0;i<8;i++)c=(c>>1)^(0xedb88320u&uint32_t(-int(c&1)));result[n]=c;}return result;}();
  uint32_t crc=~0u;
  for(uint8_t v:bytes)crc=table[(crc^v)&255]^(crc>>8);
  return ~crc;
}

struct Archive {
  struct Entry { uint32_t crc, offset, length; uint16_t index; Bytes preload; };
  std::filesystem::path path;
  size_t base=0;
  std::unordered_map<std::string,Entry> entries;
  explicit Archive(std::filesystem::path source):path(std::move(source))
  {
    auto header=file_range(path,0,12);Reader h{header};
  int version=h.i(4);if(h.get<uint32_t>(0)!=0x55aa1234 || (version!=1 && version!=2))throw std::runtime_error("Unsupported VPK");
    size_t start=version==1?12:28;auto tree=file_range(path,start,h.get<uint32_t>(8));base=start+tree.size();Reader r{tree};size_t at=0;
    auto next=[&](){auto s=r.string(at);at+=s.size()+1;return s;};
    for(std::string ext=next();!ext.empty();ext=next())
      for(std::string dir=next();!dir.empty();dir=next())
        for(std::string name=next();!name.empty();name=next()) {
          r.bounds(at,18);Entry e{r.get<uint32_t>(at),r.get<uint32_t>(at+8),r.get<uint32_t>(at+12),r.get<uint16_t>(at+6),{}};
          size_t preload=r.get<uint16_t>(at+4);
          if(r.get<uint16_t>(at+16)!=65535 || size_t(e.length)+preload>byte_limit)throw std::runtime_error("Invalid VPK entry");
          at+=18;r.bounds(at,preload);e.preload.assign(tree.begin()+at,tree.begin()+at+preload);at+=preload;
          if(entries.size()>=element_limit)throw std::runtime_error("VPK entry limit");
          entries.emplace(asset_path((dir==" "?"":dir+"/")+name+(ext==" "?"":"."+ext)),std::move(e));
        }
  }
  Bytes read(const Entry &e) const
  {
    auto archive=path;size_t offset=e.offset;
    if(e.index==0x7fff)offset+=base;
    else {
      auto stem=path.stem().string();if(stem.size()<4 || stem.substr(stem.size()-4)!="_dir")throw std::runtime_error("Invalid split VPK name");
      char suffix[16];std::snprintf(suffix,sizeof(suffix),"_%03u.vpk",unsigned(e.index));
      archive=path.parent_path()/(stem.substr(0,stem.size()-4)+suffix);
    }
    auto result=e.preload;auto data=file_range(archive,offset,e.length);result.insert(result.end(),data.begin(),data.end());
    if(crc32(result)!=e.crc)throw std::runtime_error("VPK CRC mismatch");return result;
  }
};

/* Mount order is the profile's resolved gameinfo order, never a second guessed
 * search path. Archives are indexed once per asset-library generation. */
class Library {
  struct Mount {std::filesystem::path path;std::unique_ptr<Archive> archive;};
  std::vector<Mount> mounts_;
public:
  explicit Library(const std::string &mounts)
  {
    size_t at=0;
    while(at<mounts.size()) {
      auto end=mounts.find('\n',at);if(end==std::string::npos)end=mounts.size();
      auto path=std::filesystem::u8path(mounts.substr(at,end-at));at=end+1;
      if(path.empty() || path.string()[0]=='#')continue;
      Mount mount{path,nullptr};if(path.extension()==".vpk")mount.archive=std::make_unique<Archive>(path);
      mounts_.push_back(std::move(mount));
    }
  }
  Bytes read(const std::string &raw) const
  {
    auto name=asset_path(raw);
    for(const auto &mount:mounts_) {
      if(mount.archive) {auto i=mount.archive->entries.find(name);if(i!=mount.archive->entries.end())return mount.archive->read(i->second);}
      else {
        auto path=mount.path/std::filesystem::u8path(name);
        if(std::filesystem::is_regular_file(path)) {
          auto root=std::filesystem::weakly_canonical(mount.path);auto real=std::filesystem::weakly_canonical(path);
          auto relative=real.lexically_relative(root);
          if(relative.empty() || *relative.begin()=="..")throw std::runtime_error("Source loose asset escapes mount");
          return file(path);
        }
      }
    }
    throw std::runtime_error("Source asset not found: "+name);
  }
  std::string fingerprint(const std::string &raw) const
  {
    auto name=asset_path(raw);
    for(const auto &mount:mounts_) {
      if(mount.archive) {auto i=mount.archive->entries.find(name);if(i!=mount.archive->entries.end())return mount.path.string()+":"+std::to_string(i->second.crc);}
      else {auto path=mount.path/std::filesystem::u8path(name);if(std::filesystem::is_regular_file(path))return path.string()+":"+std::to_string(std::filesystem::last_write_time(path).time_since_epoch().count())+":"+std::to_string(std::filesystem::file_size(path));}
    }
    return name+":missing";
  }
};

struct Texture {
  int width=0,height=0,format=0;
  Bytes payload; // Original DXT blocks, or original uncompressed VTF texels.
};
inline size_t image_bytes(int width,int height,int format)
{
  if(width<1 || height<1 || width>32768 || height>32768)throw std::runtime_error("Invalid VTF dimensions");
  size_t result=0;
  if(format==13 || format==20)result=size_t((width+3)/4)*((height+3)/4)*8;
  else if(format==14 || format==15)result=size_t((width+3)/4)*((height+3)/4)*16;
  else if(format==0 || format==1 || format==11 || format==12 || format==16)result=size_t(width)*height*4;
  else if(format==2 || format==3)result=size_t(width)*height*3;
  else if(format==5 || format==8)result=size_t(width)*height;
  else throw std::runtime_error("Unsupported native VTF pixel format: "+std::to_string(format));
  if(result>byte_limit)throw std::runtime_error("VTF image exceeds limit");return result;
}
inline Texture read_vtf(const Bytes &bytes)
{
  Reader r{bytes};r.bounds(0,64);
  if(std::memcmp(bytes.data(),"VTF\0",4) || r.i(4)!=7 || r.i(8)>5 || r.i(8)<0)throw std::runtime_error("Unsupported VTF version");
  Texture result;result.width=r.get<uint16_t>(16);result.height=r.get<uint16_t>(18);result.format=r.i(52);
  int mipmaps=r.get<uint8_t>(56),frames=r.get<uint16_t>(24),depth=r.i(8)>=2?r.get<uint16_t>(63):1;
  if(mipmaps<1 || mipmaps>16 || frames<1 || depth!=1)throw std::runtime_error("Unsupported VTF image layout");
  size_t at=r.get<uint32_t>(12);r.bounds(0,at);
  if(r.i(8)>=3) {
    r.bounds(0,80);int count=r.i(68);r.table(80,count,8);bool found=false;
    for(int i=0;i<count;i++) {size_t p=80+i*8;
      if(r.get<uint8_t>(p)==0x30 && r.get<uint8_t>(p+1)==0 && r.get<uint8_t>(p+2)==0) {
        if(r.get<uint8_t>(p+3)&2)throw std::runtime_error("Inline VTF image resource unsupported");at=r.get<uint32_t>(p+4);found=true;
      }
    }
    if(!found)throw std::runtime_error("VTF high-resolution resource missing");
  }
  else if(r.get<uint8_t>(61) && r.get<uint8_t>(62))at+=image_bytes(r.get<uint8_t>(61),r.get<uint8_t>(62),r.i(57));
  int faces=(r.get<uint32_t>(20)&0x4000)?(r.i(8)<5 && r.get<uint16_t>(26)!=65535?7:6):1;
  for(int level=mipmaps-1;level>0;level--) {
    size_t size=image_bytes(std::max(1,result.width>>level),std::max(1,result.height>>level),result.format);
    if(size>byte_limit/size_t(frames*faces))throw std::runtime_error("VTF mip chain exceeds limit");
    at+=size*frames*faces;r.bounds(at,0);
  }
  auto size=image_bytes(result.width,result.height,result.format);r.bounds(at,size);
  result.payload.assign(bytes.begin()+at,bytes.begin()+at+size);return result;
}

struct Vertex {std::array<float,3> position,normal;std::array<float,2> uv;};
struct Surface {int material=0;std::vector<uint32_t> indices;};
struct Model {std::vector<Vertex> vertices;std::vector<Surface> surfaces;std::vector<std::string> materials,directories;};
inline Model read_model(const Bytes &mdl,const Bytes &vvd,const Bytes &vtx,int skin=0,int body=0)
{
  Reader m{mdl},d{vvd},t{vtx};m.bounds(0,240);d.bounds(0,64);t.bounds(0,36);
  if(std::memcmp(mdl.data(),"IDST",4) || m.i(4)<44 || m.i(4)>49 || m.i(76)!=int(mdl.size()) ||
     std::memcmp(vvd.data(),"IDSV",4) || d.i(4)!=4 || t.i(0)!=7 || m.i(8)!=d.i(8) || m.i(8)!=t.i(16))throw std::runtime_error("Invalid or mismatched MDL/VVD/VTX");
  if(skin<0 || body<0 || d.i(12)<1 || d.i(12)>8 || t.i(20)<1)throw std::runtime_error("Invalid Source model variant");
  Model result;int count=d.i(16),start=d.i(56),fixcount=d.i(48),fixstart=d.i(52);d.table(start,count,48);d.table(fixstart,fixcount,12);
  std::vector<int> ids;
  for(int f=0;f<fixcount;f++) {
    size_t p=fixstart+f*12;int first=d.i(p+4),n=d.i(p+8);if(d.i(p)<0 || first<0 || n<0 || size_t(n)+ids.size()>element_limit)throw std::runtime_error("Invalid VVD fixup");
    d.table(size_t(start)+size_t(first)*48,n,48);for(int i=0;i<n;i++)ids.push_back(first+i);
  }
  if(!fixcount)for(int i=0;i<count;i++)ids.push_back(i);
  if(ids.size()!=size_t(count))throw std::runtime_error("VVD fixup count mismatch");
  result.vertices.reserve(ids.size());
  for(int i:ids) {
    size_t p=size_t(start)+size_t(i)*48+16;Vertex v;
    for(int k=0;k<3;k++){v.position[k]=d.get<float>(p+k*4);v.normal[k]=d.get<float>(p+12+k*4);if(!std::isfinite(v.position[k]) || !std::isfinite(v.normal[k]))throw std::runtime_error("Non-finite Source vertex");}
    for(int k=0;k<2;k++){v.uv[k]=d.get<float>(p+24+k*4);if(!std::isfinite(v.uv[k]))throw std::runtime_error("Non-finite Source UV");}
    result.vertices.push_back(v);
  }
  int numtex=m.i(204),texstart=m.i(208),numdirs=m.i(212),dirstart=m.i(216),numrefs=m.i(220),numskins=m.i(224),skinstart=m.i(228),numbodies=m.i(232),bodystart=m.i(236);
  m.table(texstart,numtex,64);m.table(dirstart,numdirs,4);m.table(bodystart,numbodies,16);
  if(numrefs<0 || numskins<0 || int64_t(numrefs)*numskins>int64_t(element_limit) || skin>=std::max(1,numskins))throw std::runtime_error("Invalid Source skin");
  m.table(skinstart,numrefs*numskins,2);
  for(int i=0;i<numtex;i++){size_t p=texstart+i*64;result.materials.push_back(m.string(m.relative(p,m.i(p))));result.surfaces.push_back({i,{}});}
  for(int i=0;i<numdirs;i++)result.directories.push_back(m.string(m.i(dirstart+i*4)));
  if(t.i(28)!=numbodies)throw std::runtime_error("Model body tables disagree");t.table(t.i(32),numbodies,8);
  size_t triangles=0;
  for(int bi=0;bi<numbodies;bi++) {
    size_t bp=bodystart+bi*16,vp=t.i(32)+bi*8;int models=m.i(bp+4),base=m.i(bp+8);
    if(models<1 || base<1 || t.i(vp)!=models)throw std::runtime_error("Invalid model bodypart");
    m.table(m.relative(bp,m.i(bp+12)),models,148);t.table(t.relative(vp,t.i(vp+4)),models,8);
    int mi=(body/base)%models;size_t mp=m.relative(bp,m.i(bp+12))+mi*148,vm=t.relative(vp,t.i(vp+4))+mi*8;
    int meshes=m.i(mp+72),nverts=m.i(mp+80),vertexoff=m.i(mp+84);
    if(vertexoff<0 || vertexoff%48 || nverts<0 || size_t(vertexoff/48)+nverts>result.vertices.size() || t.i(vm)<1)throw std::runtime_error("Invalid model vertex range");
    size_t modelbase=vertexoff/48,lp=t.relative(vm,t.i(vm+4));t.bounds(lp,12);
    if(t.i(lp)!=meshes)throw std::runtime_error("Model mesh tables disagree");
    m.table(m.relative(mp,m.i(mp+76)),meshes,116);t.table(t.relative(lp,t.i(lp+4)),meshes,9);
    for(int meshindex=0;meshindex<meshes;meshindex++) {
      size_t mesh=m.relative(mp,m.i(mp+76))+meshindex*116,vmsh=t.relative(lp,t.i(lp+4))+meshindex*9;
      int mat=m.i(mesh),meshverts=m.i(mesh+8),meshbase=m.i(mesh+12);
      if(mat<0 || mat>=(numrefs && numskins?numrefs:numtex) || meshverts<0 || meshbase<0 || int64_t(meshbase)+meshverts>nverts)throw std::runtime_error("Invalid Source mesh");
      int slot=numrefs && numskins?m.get<uint16_t>(skinstart+(skin*numrefs+mat)*2):mat;
      if(slot<0 || slot>=numtex)throw std::runtime_error("Invalid Source material index");
      int groups=t.i(vmsh);size_t firstgroup=t.relative(vmsh,t.i(vmsh+4));t.table(firstgroup,groups,25);
      for(int gi=0;gi<groups;gi++) {
        size_t gp=firstgroup+gi*25;int nv=t.i(gp),ni=t.i(gp+8),ns=t.i(gp+16);
        size_t vo=t.relative(gp,t.i(gp+4)),io=t.relative(gp,t.i(gp+12)),so=t.relative(gp,t.i(gp+20));t.table(vo,nv,9);t.table(io,ni,2);t.table(so,ns,27);
        std::vector<uint32_t> remap;remap.reserve(nv);
        for(int i=0;i<nv;i++){int original=t.get<uint16_t>(vo+i*9+4);if(original>=meshverts)throw std::runtime_error("Invalid VTX vertex");remap.push_back(uint32_t(modelbase+meshbase+original));}
        auto index=[&](int i){int v=t.get<uint16_t>(io+size_t(i)*2);if(v>=nv)throw std::runtime_error("Invalid VTX index");return remap[v];};
        auto emit=[&](uint32_t a,uint32_t b,uint32_t c){if(a==b || b==c || a==c)return;if(++triangles>element_limit)throw std::runtime_error("Source triangle limit");auto &out=result.surfaces[slot].indices;out.insert(out.end(),{a,c,b});};
        for(int si=0;si<ns;si++) {
          size_t sp=so+si*27;int n=t.i(sp),first=t.i(sp+4);uint8_t flags=t.get<uint8_t>(sp+18);
          if(first<0 || n<0 || int64_t(first)+n>ni)throw std::runtime_error("Invalid VTX strip");
          if(flags&1){if(n%3)throw std::runtime_error("Incomplete VTX triangles");for(int i=0;i<n;i+=3)emit(index(first+i),index(first+i+1),index(first+i+2));}
          else if(flags&2){for(int i=0;i<n-2;i++)if(i%2)emit(index(first+i+1),index(first+i),index(first+i+2));else emit(index(first+i),index(first+i+1),index(first+i+2));}
          else throw std::runtime_error("Unsupported VTX topology");
        }
      }
    }
  }
  if(!triangles)throw std::runtime_error("Source model has no triangles");return result;
}
inline Model load_model(const Library &library,const std::string &raw,int skin=0,int body=0)
{
  auto path=asset_path(raw);if(path.size()<4 || path.substr(path.size()-4)!=".mdl")throw std::runtime_error("Expected Source MDL");
  auto stem=path.substr(0,path.size()-4);auto mdl=library.read(path),vvd=library.read(stem+".vvd");Bytes vtx;
  for(auto suffix:{".dx90.vtx",".dx80.vtx",".sw.vtx",".vtx"})try{vtx=library.read(stem+suffix);break;}catch(const std::exception &){}
  if(vtx.empty())throw std::runtime_error("Source VTX companion missing");
  try{return read_model(mdl,vvd,vtx,skin,body);}catch(const std::exception &){if(!skin && !body)throw;return read_model(mdl,vvd,vtx,0,0);}
}

struct Material {
  std::string shader,base,second;
  bool alpha_test=false,translucent=false,nocull=false;
};
struct KV {
  std::string key,value;std::vector<KV> children;
};
inline std::vector<KV> keyvalues(const Bytes &bytes)
{
  size_t at=0,tokens=0;bool eof=false;
  auto token=[&]()->std::string {
    while(at<bytes.size()) {
      if(std::isspace(bytes[at])){at++;continue;}
      if(bytes[at]=='/' && at+1<bytes.size() && bytes[at+1]=='/') {while(at<bytes.size() && bytes[at]!='\n')at++;continue;}
      break;
    }
    if(++tokens>element_limit)throw std::runtime_error("VMT token limit");
    if(at==bytes.size()){eof=true;return {};}
    if(bytes[at]=='{' || bytes[at]=='}')return std::string(1,char(bytes[at++]));
    std::string out;
    if(bytes[at]=='"') {
      at++;while(at<bytes.size() && bytes[at]!='"') {
        if(bytes[at]=='\\' && at+1<bytes.size() && bytes[at+1]=='"')at++;
        out+=char(bytes[at++]);
      }
      if(at==bytes.size())throw std::runtime_error("Unterminated VMT token");at++;
    }
    else while(at<bytes.size() && !std::isspace(bytes[at]) && bytes[at]!='{' && bytes[at]!='}')out+=char(bytes[at++]);
    return out;
  };
  auto parse=[&](auto &self,int depth,bool nested)->std::vector<KV> {
    if(depth>32)throw std::runtime_error("VMT nesting limit");std::vector<KV> result;
    while(true) {
      auto key=token();if(eof){if(nested)throw std::runtime_error("Unclosed VMT block");break;}
      if(key=="}"){if(!nested)throw std::runtime_error("Unexpected VMT brace");break;}
      auto value=token();std::transform(key.begin(),key.end(),key.begin(),[](unsigned char c){return char(std::tolower(c));});
      KV item{key,value,{}};if(value=="{")item.children=self(self,depth+1,true);else if(value=="}" || eof)throw std::runtime_error("Invalid VMT pair");
      result.push_back(std::move(item));
    }
    return result;
  };
  return parse(parse,0,false);
}
inline std::map<std::string,std::string> material_properties(const Library &library,std::string name,std::vector<std::string> seen={})
{
  name=asset_path(name);if(name.rfind("materials/",0)!=0)name="materials/"+name;
  if(name.size()<4 || name.substr(name.size()-4)!=".vmt")name+=".vmt";
  if(seen.size()>=16 || std::find(seen.begin(),seen.end(),name)!=seen.end())throw std::runtime_error("VMT include cycle");seen.push_back(name);
  auto document=keyvalues(library.read(name));if(document.empty() || document[0].value!="{")throw std::runtime_error("Invalid VMT shader");
  auto &root=document[0];std::map<std::string,std::string> result;
  if(root.key=="patch") {
    std::string include;for(auto &p:root.children)if(p.key=="include")include=p.value;
    if(include.empty())throw std::runtime_error("VMT patch missing include");result=material_properties(library,include,seen);
    for(auto &p:root.children)if(p.key=="insert" || p.key=="replace")for(auto &v:p.children) {
      if(p.key=="replace" || !result.count(v.key))result[v.key]=v.value;
    }
  }
  else {result["_shader"]=root.key;for(auto &p:root.children)if(p.children.empty())result[p.key]=p.value;}
  return result;
}
inline Material load_material(const Library &library,const std::string &name)
{
  auto props=material_properties(library,name);Material result;
  result.shader=props["_shader"];result.base=props["$basetexture"];if(result.base.empty())result.base=props["%tooltexture"];
  if(result.base.empty() && (result.shader=="eyes" || result.shader=="eyerefract"))result.base=props["$iris"];
  result.second=props["$basetexture2"];result.alpha_test=props["$alphatest"]=="1";result.translucent=props["$translucent"]=="1";result.nocull=props["$nocull"]=="1";
  if(result.base.empty())throw std::runtime_error("VMT has no base/tool texture");return result;
}
inline Texture load_texture(const Library &library,std::string name)
{
  name=asset_path(name);if(name.rfind("materials/",0)!=0)name="materials/"+name;
  if(name.size()<4 || name.substr(name.size()-4)!=".vtf")name+=".vtf";
  return read_vtf(library.read(name));
}
} // namespace wavelength::source1
