"""Source skeletal animation decoder based on Valve's public studio layout.

No Blender dependency. Unsupported runtime blend/IK graphs fail explicitly;
ordinary compressed bone tracks and external animation blocks are sampled.
"""
import math
from .studio_model import Reader

def _quat(reader,p,bits):
    if bits==48:
        x,y,z=reader.get('3H',p);values=((x-32768)/32768,(y-32768)/32768,((z&32767)-16384)/16384);negative=z>>15
    else:
        packed=reader.get('Q',p)[0];values=tuple((((packed>>(21*i))&2097151)-1048576)/1048576.5 for i in range(3));negative=packed>>63
    w=math.sqrt(max(0.,1-sum(v*v for v in values)))
    return (*values,-w if negative else w)

def _channel(reader,p,frame):
    while True:
        valid,total=reader.get('2B',p)
        if not total or not valid or valid>total:raise ValueError('Invalid Source animation run')
        if frame<total:return reader.get('h',p+2*(1+min(frame,valid-1)))[0]
        frame-=total;p+=2*(valid+1)

def _angles(e):
    # Source RadianEuler is Rz(yaw) Ry(pitch) Rx(roll), expressed XYZ here.
    x,y,z=(v*.5 for v in e);cx,cy,cz=math.cos(x),math.cos(y),math.cos(z);sx,sy,sz=math.sin(x),math.sin(y),math.sin(z)
    return (sx*cy*cz-cx*sy*sz,cx*sy*cz+sx*cy*sz,cx*cy*sz-sx*sy*cz,cx*cy*cz+sx*sy*sz)

def read(mdl,peer):
    m=Reader(mdl);bones=[]
    for p in m.array(m.integer(160),m.integer(156),216):
        name=m.string(p+m.integer(p));parent=m.integer(p+4)
        if parent>=len(bones) or parent < -1:raise ValueError('Invalid Source bone hierarchy')
        bones.append(dict(name=name,parent=parent,pos=m.get('3f',p+32),quat=m.get('4f',p+44),
                          rot=m.get('3f',p+60),posscale=m.get('3f',p+72),rotscale=m.get('3f',p+84)))
    if len({b['name'] for b in bones})!=len(bones):raise ValueError('Source bone names are not unique')
    if m.integer(336):raise ValueError('This model includes external sequence models; importing that animation graph is not supported yet')
    animations=[];warnings=[]
    for p in m.array(m.integer(184),m.integer(180),100):
        name=m.string(p+m.integer(p+4));fps=m.get('f',p+8)[0];flags=m.integer(p+12);count=m.integer(p+16)
        if flags&4 or flags&64 or m.integer(p+20) or m.integer(p+60) or m.integer(p+72):
            raise ValueError('Animation '+name+' uses a delta/frame, root-motion, IK or hierarchy track not yet supported for editable import')
        if count<1 or not math.isfinite(fps) or fps<=0:raise ValueError('Invalid Source animation timing')
        block,index=m.get('2i',p+52);sections,sectionframes=m.get('2i',p+80)
        frames=[]
        for frame in range(count):
            at=frame;bid,offset=block,index
            if sectionframes:
                section=frame//sectionframes;at=frame%sectionframes
                if frame==count-1 and count>sectionframes:section=count//sectionframes+1;at=0
                bid,offset=m.get('2i',p+sections+section*8)
            if bid<0:raise ValueError('Missing animation block: '+name)
            r=m;cursor=p+offset if offset else 0
            if bid:
                if bid>=m.integer(352):raise ValueError('Invalid external animation block')
                start,end=m.get('2i',m.integer(356)+bid*8)
                payload=peer(m.string(m.integer(348)))
                r=Reader(payload[start:end]);cursor=offset
            values=[(b['pos'],b['quat']) for b in bones];seen=set()
            while cursor:
                bi,options,nextoff=r.get('BBH',cursor)
                if bi==255:break
                if bi>=len(bones) or bi in seen:raise ValueError('Invalid animation bone chain')
                seen.add(bi);b=bones[bi];q=b['quat'];position=b['pos'];data=cursor+4
                if options&16:raise ValueError('Additive bone animation needs its runtime base pose: '+name)
                if options&2:q=_quat(r,data,48)
                if options&32:q=_quat(r,data,64)
                if options&1:position=r.get('3e',data+(6 if options&2 else 0)+(8 if options&32 else 0))
                if options&8:
                    offsets=r.get('3h',data)
                    q=_angles([b['rot'][i]+(_channel(r,data+off,at)*b['rotscale'][i] if off else 0) for i,off in enumerate(offsets)])
                if options&4:
                    posdata=data+(6 if options&8 else 0);offsets=r.get('3h',posdata)
                    position=tuple(b['pos'][i]+(_channel(r,posdata+off,at)*b['posscale'][i] if off else 0) for i,off in enumerate(offsets))
                if not all(math.isfinite(v) for v in (*position,*q)):raise ValueError('Nonfinite Source animation sample')
                values[bi]=(position,q)
                if not nextoff:break
                cursor+=nextoff
            frames.append(values)
        animations.append(dict(name=name,fps=fps,loop=bool(flags&1),frames=frames))
    clips=[]
    for p in m.array(m.integer(192),m.integer(188),212):
        if m.integer(p+56)!=1:raise ValueError('Blended sequence graphs are not yet supported for editable import')
        index=m.get('h',p+m.integer(p+60))[0]
        if not 0<=index<len(animations):raise ValueError('Invalid sequence animation index')
        clip=dict(animations[index]);clip['name']=m.string(p+m.integer(p+4));clip['loop']=bool(m.integer(p+12)&1)
        activity=m.integer(p+8);clip['activity']=m.string(p+activity) if activity else ''
        if m.integer(p+24):warnings.append('Sequence '+clip['name']+' has game events; event export is not yet supported')
        clips.append(clip)
    return dict(bones=bones,clips=clips or animations,warnings=warnings)
