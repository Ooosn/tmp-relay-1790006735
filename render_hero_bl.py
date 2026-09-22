import bpy, sys, os, math
from mathutils import Vector, Matrix
import numpy as np
def args():
    a=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument('--glb',required=True); p.add_argument('--outdir',required=True)
    p.add_argument('--azs',default='40'); p.add_argument('--el',type=float,default=20.0)
    p.add_argument('--res',type=int,default=900); p.add_argument('--engine',default='BLENDER_EEVEE')
    p.add_argument('--up',default='auto'); p.add_argument('--margin',type=float,default=1.28)
    p.add_argument('--lens',type=float,default=62.0); p.add_argument('--floor',type=int,default=1)
    p.add_argument('--vc',type=int,default=1); p.add_argument('--tag',default='')
    return p.parse_args(a)
def si(inp,name,val):
    try: inp[name].default_value=val; return True
    except Exception: return False
def import_mesh(path):
    ext=os.path.splitext(path)[1].lower()
    if ext in ('.glb','.gltf'): bpy.ops.import_scene.gltf(filepath=path)
    else: bpy.ops.wm.obj_import(filepath=path)
    return [o for o in bpy.data.objects if o.type=='MESH']
def world_verts(objs):
    pts=[]
    for o in objs:
        vs=o.data.vertices
        if not vs: continue
        arr=np.empty(len(vs)*3,dtype=np.float64); vs.foreach_get('co',arr); arr=arr.reshape(-1,3)
        m=np.array(o.matrix_world); arr=arr@m[:3,:3].T+m[:3,3]; pts.append(arr)
    return np.concatenate(pts,0) if pts else None
def robust_frame(objs):
    P=world_verts(objs)
    c=np.median(P,axis=0); d=np.linalg.norm(P-c,axis=1); R=float(np.percentile(d,90))
    lo=np.percentile(P,3,axis=0); hi=np.percentile(P,97,axis=0); ext=hi-lo; floor_z=float(np.percentile(P[:,2],2))
    return c,R,ext,floor_z
def place_cam(cam,center,dist,az,el):
    azr=math.radians(az); elr=math.radians(el)
    d=Vector((math.cos(elr)*math.cos(azr),math.cos(elr)*math.sin(azr),math.sin(elr)))
    loc=center+d*dist; fwd=(center-loc).normalized(); up=Vector((0,0,1))
    if abs(fwd.dot(up))>0.999: up=Vector((0,1,0))
    right=fwd.cross(up).normalized(); tup=right.cross(fwd).normalized()
    Rm=Matrix(((right.x,tup.x,-fwd.x),(right.y,tup.y,-fwd.y),(right.z,tup.z,-fwd.z))).to_4x4()
    cam.matrix_world=Matrix.Translation(loc)@Rm
def main():
    a=args(); bpy.ops.wm.read_factory_settings(use_empty=True)
    objs=import_mesh(a.glb)
    if not objs: print('NO_MESH'); sys.exit(1)
    mat=bpy.data.materials.new('obj'); mat.use_nodes=True; nt=mat.node_tree; b=nt.nodes.get('Principled BSDF')
    si(b.inputs,'Roughness',0.34); si(b.inputs,'Metallic',0.0)
    si(b.inputs,'Specular IOR Level',0.55) or si(b.inputs,'Specular',0.55)
    si(b.inputs,'Coat Weight',0.10); si(b.inputs,'Coat Roughness',0.10)
    have_vc=False; cname='Color'
    for o in objs:
        ca=getattr(o.data,'color_attributes',None)
        if ca and len(ca)>0: have_vc=True; cname=ca[0].name; break
    if a.vc and have_vc:
        vcn=nt.nodes.new('ShaderNodeVertexColor'); vcn.layer_name=cname
        nt.links.new(vcn.outputs['Color'],b.inputs['Base Color'])
    for o in objs: o.data.materials.clear(); o.data.materials.append(mat)
    c,R,ext,fz=robust_frame(objs)
    up_axis=int(np.argmax(ext)) if a.up=='auto' else {'x':0,'y':1,'z':2}[a.up]
    if up_axis!=2:
        Rn=Matrix.Rotation(math.radians(90),4,'Y') if up_axis==0 else Matrix.Rotation(math.radians(-90),4,'X')
        for o in objs: o.matrix_world=Rn@o.matrix_world
        c,R,ext,fz=robust_frame(objs)
    center=Vector(c); R=max(float(R),1e-3)
    if a.floor:
        bpy.ops.mesh.primitive_plane_add(size=float(max(ext))*20.0,location=(center.x,center.y,fz))
        fl=bpy.context.active_object; fm=bpy.data.materials.new('floor'); fm.use_nodes=True; fb=fm.node_tree.nodes.get('Principled BSDF')
        si(fb.inputs,'Base Color',(0.95,0.95,0.96,1.0)); si(fb.inputs,'Roughness',0.75); si(fb.inputs,'Specular IOR Level',0.4) or si(fb.inputs,'Specular',0.4)
        fl.data.materials.append(fm)
    cd=bpy.data.cameras.new('cam'); cd.lens=a.lens; cam=bpy.data.objects.new('cam',cd)
    bpy.context.scene.collection.objects.link(cam); bpy.context.scene.camera=cam
    dist=max(R*a.margin/math.tan(cd.angle/2.0),1e-3)
    w=bpy.data.worlds.new('w'); bpy.context.scene.world=w; w.use_nodes=True
    bg=w.node_tree.nodes.get('Background'); bg.inputs[0].default_value=(0.96,0.96,0.97,1.0); bg.inputs[1].default_value=0.28
    def sun(nm,en,ang=0.30):
        L=bpy.data.lights.new(nm,'SUN'); L.energy=en; L.angle=ang; ob=bpy.data.objects.new(nm,L); bpy.context.scene.collection.objects.link(ob); return ob
    key=sun('key',2.7,0.22); fill=sun('fill',0.85,0.55); rim=sun('rim',1.5,0.2)
    al=bpy.data.lights.new('top','AREA'); al.energy=R*R*260.0; al.size=R*3.0; al.shape='DISK'
    alo=bpy.data.objects.new('top',al); bpy.context.scene.collection.objects.link(alo)
    alo.location=(center.x,center.y,center.z+R*2.6); alo.rotation_euler=(0,0,0)
    sc=bpy.context.scene; sc.render.engine=a.engine; sc.render.resolution_x=a.res; sc.render.resolution_y=a.res
    sc.render.film_transparent=(a.floor==0)
    sc.render.image_settings.file_format='PNG'; sc.render.image_settings.color_mode='RGBA'
    try: sc.view_settings.view_transform='AgX'
    except Exception:
        try: sc.view_settings.view_transform='Filmic'
        except Exception: pass
    sc.view_settings.look='None'
    try: sc.view_settings.exposure=-0.75
    except Exception: pass
    if a.engine=='BLENDER_EEVEE':
        ev=sc.eevee
        for attr,val in (('use_gtao',True),('gtao_distance',R*0.5),('use_shadows',True),('use_soft_shadows',True),('taa_render_samples',128),('use_raytracing',True),('use_bloom',False)):
            try: setattr(ev,attr,val)
            except Exception: pass
        try: ev.ray_tracing_options.use_denoise=True
        except Exception: pass
    os.makedirs(a.outdir,exist_ok=True)
    for az in [float(x) for x in a.azs.split(',')]:
        place_cam(cam,center,dist,az,a.el)
        key.rotation_euler=(math.radians(46),0.0,math.radians(az+38))
        fill.rotation_euler=(math.radians(64),0.0,math.radians(az-92))
        rim.rotation_euler=(math.radians(112),0.0,math.radians(az+165))
        nm=a.tag if a.tag else 'az%03d'%int(round(az))
        sc.render.filepath=os.path.join(a.outdir,nm+'.png'); bpy.ops.render.render(write_still=True)
        print('RENDERED',sc.render.filepath,'vc=',have_vc)
main()
