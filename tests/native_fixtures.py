"""Synthetic ELF shader containers; never execute these fixtures."""
import struct
from installer.wavelength_installer import experimental as e

def binary(vertex='original', fragment='original', shared=False, capacity=1800):
    header=bytearray(128);header[:6]=b'\x7fELF\x02\x01';struct.pack_into('<H',header,18,62)
    struct.pack_into('<Q',header,32,64);struct.pack_into('<Q',header,40,80)
    for offset,value in ((54,8),(56,1),(58,8),(60,1)):struct.pack_into('<H',header,offset,value)
    v=e.VERTEX+({'original':b'','current':e.V_BLOCK,'legacy':e.V_LEGACY,'unknown':b'float wl_mystery = 2;'}[vertex])
    f={'original':e.FRAGMENT,'current':e.F_CURRENT,'legacy':e.F_LEGACY,'unknown':b'out_color = wl_mystery;'}[fragment]
    strings=[b'VERTEX_SHADER_CREATE_INFO(overlay_grid_next)\n'+v+b' '*capacity,
             b'FRAGMENT_SHADER_CREATE_INFO(overlay_grid_next)\n'+f+b' '*capacity]
    return bytes(header)+(b'\n' if shared else b'\0').join(strings)+b'\0'
