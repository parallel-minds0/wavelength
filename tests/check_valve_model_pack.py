"""Validate actual packed bytes through Valve BSPZIP, not just Python's ZIP reader."""
import sys,subprocess,os,io,zipfile,struct
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'addon'))
from wavelength.source import model_formats
original=Path(r'C:\Users\user\Projects\focus\wavelength\maps\HL2\wavelength_source_hl2_windows.bsp')
folder=root/'build/door-pack-compatibility';folder.mkdir(exist_ok=True)
repaired=folder/original.name;repaired.write_bytes(model_formats.pack_bsp(original.read_bytes(),{}))
environment=dict(os.environ,VPROJECT=r'C:\Program Files (x86)\Steam\steamapps\common\Half-Life 2\hl2_complete')
extracted=folder/'extracted'
result=subprocess.run([r'C:\Program Files (x86)\Steam\steamapps\common\Half-Life 2\bin\bspzip.exe','-extractfiles',str(repaired),str(extracted)],env=environment,capture_output=True,timeout=30)
assert result.returncode==0,result.stdout+result.stderr
data=repaired.read_bytes();offset,size=struct.unpack_from('<ii',data,648)
with zipfile.ZipFile(io.BytesIO(data[offset:offset+size])) as archive:
    for info in archive.infolist():
        assert info.compress_type==zipfile.ZIP_STORED
        payload=archive.read(info)
        assert (extracted/info.filename).read_bytes()==payload,info.filename
        if info.filename.endswith('.mdl'):assert payload.startswith(b'IDST')
print('PASS Valve BSPZIP extraction matches every packaged model, collision, material and texture byte; Source-compatible stored entries')
