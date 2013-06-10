# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

import bpy, os, math, subprocess, datetime, multiprocessing, sys
import time as ti
from math import sin, cos, acos, asin, pi
from mathutils import Vector
from subprocess import PIPE, Popen

try:
    import numpy as numpy
    np = 1
except:
    np = 0
nproc = multiprocessing.cpu_count()

class LiVi_bc(object):
    def __init__(self, filepath, scene):
        if str(sys.platform) != 'win32':
            self.nproc = str(multiprocessing.cpu_count())
            self.rm = "rm "
            self.cat = "cat "
            self.fold = "/"
        elif str(sys.platform) == 'win32':
            self.nproc = "1"
            self.rm = "del "
            self.cat = "type "
            self.fold = "\\"
        self.filepath = filepath
        self.filename = os.path.splitext(os.path.basename(self.filepath))[0]
        self.filedir = os.path.dirname(self.filepath)
        if not os.path.isdir(self.filedir+self.fold+self.filename):
            os.makedirs(self.filedir+self.fold+self.filename)        
        self.newdir = self.filedir+self.fold+self.filename
        self.filebase = self.newdir+self.fold+self.filename
        self.scene = scene
        self.scene['newdir'] = self.newdir
        
class LiVi_e(LiVi_bc):
    def __init__(self, filepath, scene, sd, tz, export_op):
        LiVi_bc.__init__(self, filepath, scene)
        self.simtimes = []
        self.TZ = tz
        self.StartD = sd
        self.scene.livi_display_legend = -1
        self.clearscenee()
        self.clearscened()
        self.sky_type = int(scene.livi_export_sky_type)
        self.time_type = int(scene.livi_export_time_type)
        self.merr = 0
        self.rtrace = self.filebase+".rtrace"
        for a in bpy.app.handlers.frame_change_pre:
            bpy.app.handlers.frame_change_pre.remove(a)
  
        if scene.livi_anim == "0":
            scene.frame_start = 0
            scene.frame_end = 0 
            if scene.livi_export_time_type == "0":
                self.starttime = datetime.datetime(2010, int(scene.livi_export_start_month), int(scene.livi_export_start_day), int(scene.livi_export_start_hour), 0)
            self.fe = 0
            self.frameend = 0

        elif scene.livi_anim == "1":
            self.scene.livi_export_time_type = "0"
            self.sky_type = int(scene.livi_export_sky_type_period)
            self.starttime = datetime.datetime(2010, int(scene.livi_export_start_month), int(scene.livi_export_start_day), int(scene.livi_export_start_hour), 0)
            self.endtime = datetime.datetime(2010, int(scene.livi_export_end_month), int(scene.livi_export_end_day), int(scene.livi_export_end_hour), 0)
            self.hours = (self.endtime-self.starttime).seconds/3600
            scene.frame_start = 0
            scene.frame_end = int(self.hours/scene.livi_export_interval)
            self.fe = int(self.hours/scene.livi_export_interval)
            self.frameend = int(self.hours/scene.livi_export_interval)
        
        elif scene.livi_anim in ("2", "3", "4"):
            self.fe = scene.frame_end
            self.frameend = 0
            if scene.livi_export_time_type == "0":
                self.starttime = datetime.datetime(2010, int(scene.livi_export_start_month), int(scene.livi_export_start_day), int(scene.livi_export_start_hour), 0)
        
        if self.sky_type < 4 and self.scene.livi_export_time_type == "0":    
            self.skytypeparams = ("+s", "+i", "-c", "-b 22.86 -c")[self.sky_type]
            self.radskyhdrexport()
            if self.sky_type < 2 or self.scene.livi_anim == "1":
                self.sunexport()
            
        elif self.sky_type == 4:
            self.skyhdrexport(self.scene.livi_export_hdr_name)
        
        elif self.sky_type == 5:
            for frame in range(0, self.fe + 1):
                rad_sky = open(self.sky(frame), "w")
                rad_sky.close()
            
        elif self.scene.livi_export_time_type == "1" and self.scene.livi_anim != "1":
            self.clearscenee()            
            self.ddsskyexport()
        
        for frame in range(0, self.fe + 1):
            if scene.livi_anim == "4":
                self.radlights(frame)
            else:
                if frame == 0:
                    self.radlights(frame)
            
            if scene.livi_anim == "3":
                self.radmat(frame, export_op)
            else:
                if frame == 0:
                    self.radmat(frame, export_op)
        
        self.rtexport(export_op)
        
        if self.export != 0:    
            for frame in range(0, self.fe + 1):  
                self.merr = 0
                if scene.livi_anim == "2":
                    self.obexport(frame, [geo for geo in self.scene.objects if geo.type == 'MESH' and 'lightarray' not in geo.name and geo.hide == False and geo.layers[0] == True], 0, export_op) 
                if scene.livi_anim == "3":
                    self.obmexport(frame, [geo for geo in self.scene.objects if geo.type == 'MESH' and 'lightarray' not in geo.name and geo.hide == False and geo.layers[0] == True], 0, export_op) 
                else:
                    if frame == 0:
                        self.obexport(frame, [geo for geo in self.scene.objects if geo.type == 'MESH' and 'lightarray' not in geo.name and geo.hide == False and geo.layers[0] == True], 0, export_op)
            
                self.fexport(frame, export_op)
        
    def poly(self, fr):
        if self.scene.livi_anim == "2" or (self.scene.livi_anim == "3" and self.merr == 0):
            return(self.filebase+"-"+str(fr)+".poly")   
        else:
            return(self.filebase+"-0.poly")
     
    def obj(self, name, fr):
        if self.scene.livi_anim == "2":
            return(self.filebase+"-{}-{}.obj".format(name, fr))
        else:
            return(self.filebase+"-{}-0.obj".format(name))
    
    def mesh(self, name, fr):
        if self.scene.livi_anim in ("2", "3"):
            return(self.filebase+"-{}-{}.mesh".format(name, fr))
        else:
            return(self.filebase+"-{}-0.mesh".format(name))
    
    def mat(self, fr):
        if self.scene.livi_anim == "3":
            return(self.filebase+"-"+str(fr)+".mat")
        else:
            return(self.filebase+"-0.mat")
    
    def lights(self, fr):
        if self.scene.livi_anim == "4":
            return(self.filebase+"-"+str(fr)+".lights")
        else:
            return(self.filebase+"-0.lights")
    
    def sky(self, fr):
        if self.scene.livi_anim == "1":
            return(self.filebase+"-"+str(fr)+".sky")
        else:
            return(self.filebase+"-0.sky")
    
    def clearscenee(self):
        for sunob in [ob for ob in self.scene.objects if ob.type == 'LAMP' and ob.data.type == 'SUN']:
            self.scene.objects.unlink(sunob)
        
        for ob in [ob for ob in self.scene.objects if ob.type == 'MESH']:
            self.scene.objects.active = ob
            for vcol in ob.data.vertex_colors:
                bpy.ops.mesh.vertex_color_remove()
    
    def clearscened(self):    
        for ob in [ob for ob in self.scene.objects if ob.type == 'MESH']:
            try:
                if ob['res'] == 1:
                   self.scene.objects.unlink(ob)
            except Exception as e:
                if str(e) != '\'bpy_struct[key]: key "res" not found\'':
                    print(e, '\'bpy_struct[key]: key "res" not found\'')
       
        for mesh in bpy.data.meshes:
            if mesh.users == 0:
                bpy.data.meshes.remove(mesh)
        
        for lamp in bpy.data.lamps:
            if lamp.users == 0:
                bpy.data.lamps.remove(lamp)
        
        for oldgeo in bpy.data.objects:
            if oldgeo.users == 0:
                bpy.data.objects.remove(oldgeo)
                
        for sk in bpy.data.shape_keys:
            if sk.users == 0:
                for keys in sk.keys():
                    keys.animation_data_clear()
                    
    def sparams(self, acc):
        if acc == "3":
            return(self.scene.livi_calc_custom_acc)
        else:
            if acc == "0":
                num = ("2", "256", "128", "128", "0.3", "1", "1", "1", "0", "1", "0.05")
            elif acc == "1":
                num = ("2", "1024", "512", "512", "0.15", "1", "1", "2", "1", "1", "0.01")
            elif acc == "2":
                num = ("3", "4096", "1024", "1024", "0.08", "1", "1", "3", "5", "1", "0.0003")
            return(" -ab %s -ad %s -ar %s -as %s -av 0 0 0 -aa %s -dj %s -ds %s -dr %s -ss %s -st %s -lw %s " %(num))
        
    def pparams(self, acc):
        if acc == "3":
            return(self.scene.livi_calc_custom_acc)
        else:
            if acc == "0":
                num = ("2", "256", "32", "32", "0.3", "0", "0.5", "1", "0", "0.85", "0.05")
            elif acc == "1":
                num = ("3", "1024", "64", "256", "0.15", "0.7", "0.15", "2", "1", "0.5", "0.01")
            elif acc == "2":
                num = ("4", "4096", "0", "1024", "0.05", "1", "0.02", "3", "5", "0.15", "0.0003")
            return(" -ab %s -ad %s -ar %s -as %s -av 0 0 0 -aa %s -dj %s -ds %s -dr %s -ss %s -st %s -lw %s " %(num))
    
    def radskyhdrexport(self):
        for frame in range(0, self.frameend + 1):
            simtime = self.starttime + frame*datetime.timedelta(seconds = 3600*self.scene.livi_export_interval)
            self.simtimes.append(simtime)
            subprocess.call("gensky "+str(self.simtimes[frame].month)+" "+str(self.simtimes[frame].day)+" "+str(self.simtimes[frame].hour)+":"+str(self.simtimes[frame].minute)+str(self.TZ)+" -a "+str(self.scene.livi_export_latitude)+" -o "+str(self.scene.livi_export_longitude)+" "+self.skytypeparams+" > "+self.sky(frame), shell=True)
            self.skyexport(open(self.sky(frame), "a"))           
            subprocess.call("oconv "+self.sky(frame)+" > "+self.filebase+"-"+str(frame)+"sky.oct", shell=True)
            subprocess.call("cnt 250 500 | rcalc -f %s/io_livi/lib/latlong.cal -e 'XD=500;YD=250;inXD=0.002;inYD=0.004' | rtrace -af pan.af -n %s -x 500 -y 250 -fac %s-%ssky.oct > %s/%sp.hdr" %(self.scene.livipath, nproc, self.filebase, frame, self.newdir, frame), shell=True)
            subprocess.call("rpict -vta -vp 0 0 0 -vd 1 0 0 -vu 0 0 1 -vh 360 -vv 360 -x 1000 -y 1000 {}-{}sky.oct > {}/{}.hdr".format(self.filebase, frame, self.newdir, frame), shell=True)
                
    def sunexport(self):
        for frame in range(0, self.frameend + 1):
            simtime = self.starttime + frame*datetime.timedelta(seconds = 3600*self.scene.livi_export_interval)
            deg2rad = 2*math.pi/360
            if self.scene.livi_export_summer_enable:
                DS = 1 
            else:
                DS = 0
            ([solalt, solazi]) = solarPosition(simtime.timetuple()[7], simtime.hour - DS + (simtime.minute)*0.016666, self.scene.livi_export_latitude, self.scene.livi_export_longitude) 
            if self.sky_type < 2:
                if frame == 0:
                    bpy.ops.object.lamp_add(type='SUN')
                    sun = bpy.context.object
                    sun.data.shadow_method = 'RAY_SHADOW'
                    sun.data.shadow_ray_samples = 8
                    sun.data.sky.use_sky = 1
                    if self.sky_type == 0:
                        sun.data.shadow_soft_size = 0.1
                        sun.data.energy = 5
                    elif self.sky_type == 1:
                        sun.data.shadow_soft_size = 3
                        sun.data.energy = 3
                    sun.location = (0,0,10)
                sun.rotation_euler = (90-solalt)*deg2rad, 0, solazi*deg2rad
                sun.keyframe_insert(data_path = 'location', frame = frame)
                sun.keyframe_insert(data_path = 'rotation_euler', frame = frame)
                sun.data.cycles.use_multiple_importance_sampling = True
                sun.data.shadow_soft_size = 0.01
            
            bpy.ops.object.select_all()
            
    def skyhdrexport(self, hdr_skies):
        render = self.scene.render
        w = bpy.data.worlds['World']
        if self.sky_type > 1 or self.scene.livi_export_time_type == "1":
            imgPath = hdr_skies
            img = bpy.data.images.load(imgPath)
            if self.scene.world.texture_slots[0] == None or self.scene.world.texture_slots[0] == "":
                
                imtex = bpy.data.textures.new('Radsky', type = 'IMAGE')
                imtex.image = img
                
                slot = w.texture_slots.add()
                slot.texture = imtex
                slot.use_map_horizon = True
                slot.use_map_blend = False
                slot.texture_coords = 'EQUIRECT'
                bpy.data.textures['Radsky'].image_user.use_auto_refresh = True
                
                self.scene.world.light_settings.use_environment_light = True
                self.scene.world.light_settings.use_indirect_light = False
                self.scene.world.light_settings.use_ambient_occlusion = True
                self.scene.world.light_settings.environment_energy = 1
                self.scene.world.light_settings.environment_color = 'SKY_TEXTURE'
                self.scene.world.light_settings.gather_method = 'APPROXIMATE'
                self.scene.world.light_settings.passes = 1
                self.scene.world.use_sky_real = True
                self.scene.world.use_sky_paper = False
                self.scene.world.use_sky_blend = False
                
                self.scene.world.horizon_color = (0, 0, 0)
                self.scene.world.zenith_color = (0, 0, 0)
                
                render.use_raytrace = True
                render.use_textures = True
                render.use_shadows = True
                render.use_envmaps = True
                bpy.ops.images.reload
            else:
                bpy.data.worlds['World'].texture_slots[0].texture.image.filepath = hdr_skies
                bpy.data.worlds['World'].texture_slots[0].texture.image.reload()
            
            if self.scene.livi_anim != '1':
                bpy.data.worlds['World'].texture_slots[0].texture.image.source = 'FILE'
            else:
                bpy.data.worlds['World'].texture_slots[0].texture.image.source = 'SEQUENCE'
            
            if self.scene.livi_export_time_type == "0":
                self.scene.world.ambient_color = (0.04, 0.04, 0.04)
            else:
                self.scene.world.ambient_color = (0.000001, 0.000001, 0.000001)
            bpy.data.worlds['World'].texture_slots[0].texture.factor_red = (0.05, 0.000001)[int(self.scene.livi_export_time_type)]
            bpy.data.worlds['World'].texture_slots[0].texture.factor_green = (0.05, 0.000001)[int(self.scene.livi_export_time_type)]
            bpy.data.worlds['World'].texture_slots[0].texture.factor_blue = (0.05, 0.000001)[int(self.scene.livi_export_time_type)]
            
            if self.sky_type == 4:
                self.hdrsky(open(self.sky(0), "w"), self.scene.livi_export_hdr_name)
            elif self.time_type == 1:
                self.hdrsky(open(self.sky(0), "w"), hdr_skies)
            
            if self.scene.render.engine == "CYCLES" and bpy.data.worlds['World'].use_nodes == False:
                bpy.data.worlds['World'].use_nodes = True
                nt = bpy.data.worlds['World'].node_tree
                try:
                    if nt.nodes['Environment Texture']:
                        pass
                except:
                    nt.nodes.new("TEX_ENVIRONMENT")
                    nt.nodes['Environment Texture'].image = bpy.data.images[os.path.basename(hdr_skies)]
                    nt.nodes['Environment Texture'].image.name = "World"
                    nt.nodes['Environment Texture'].image.source = 'FILE'
                    if self.scene.livi_export_time_type == "1":
                        nt.nodes['Environment Texture'].projection = 'MIRROR_BALL'
                    else:
                        nt.nodes['Environment Texture'].projection = 'EQUIRECTANGULAR'
            bpy.app.handlers.frame_change_pre.append(cyfc1) 
        else:
            self.scene.world.use_sky_real = False
            self.scene.world.use_sky_paper = False
            self.scene.world.use_sky_blend = False
            self.scene.world.light_settings.use_environment_light = True
            self.scene.world.light_settings.use_indirect_light = False
            self.scene.world.light_settings.use_ambient_occlusion = False
            self.scene.world.light_settings.environment_energy = 1
            self.scene.world.light_settings.environment_color = 'SKY_COLOR'
            self.scene.world.light_settings.gather_method = 'APPROXIMATE'
            self.scene.world.light_settings.passes = 1
            self.scene.render.alpha_mode = "SKY"
            render.use_raytrace = True
            render.use_textures = True
            render.use_shadows = True
            render.use_envmaps = False
            try:
                w.texture_slots[0].use_map_horizon = False
            except:
                pass

            for sun in [s for s in bpy.data.objects if s.type == "LAMP" and s.data.type == "SUN"]:
                sun.data.shadow_method = "RAY_SHADOW"
                sun.data.shadow_soft_size = 0.01
                sun.data.cycles.cast_shadow = True
                sun.data.cycles.use_multiple_importance_sampling = True
                sun.data.sky.use_sky = True
                sun.hide = False   
                sun.data.sky.use_atmosphere = False
                sun.data.energy = 1
                
    def skyexport(self, rad_sky):
        rad_sky.write("\nskyfunc glow skyglow\n0\n0\n")
        if self.sky_type < 3:
            rad_sky.write("4 .8 .8 1 0\n\n")
        else:
            rad_sky.write("4 1 1 1 0\n\n")    
        rad_sky.write("skyglow source sky\n0\n0\n4 0 0 1  180\n\n")
        rad_sky.write("skyfunc glow groundglow\n0\n0\n4 .8 1.1 .8  0\n\n")
        rad_sky.write("groundglow source ground\n0\n0\n4 0 0 -1  180\n\n")
        rad_sky.close()
        
    def ddsskyexport(self):
        os.chdir(self.newdir)
        pcombfiles = "ps0.hdr ps1.hdr ps2.hdr ps3.hdr ps4.hdr ps5.hdr ps6.hdr ps7.hdr ps8.hdr ps9.hdr ps10.hdr ps11.hdr ps12.hdr ps13.hdr ps14.hdr ps15.hdr ps16.hdr ps17.hdr ps18.hdr ps19.hdr ps20.hdr ps21.hdr ps22.hdr ps23.hdr ps24.hdr ps25.hdr ps26.hdr ps27.hdr ps28.hdr ps29.hdr ps30.hdr ps31.hdr ps32.hdr ps33.hdr ps34.hdr ps35.hdr ps36.hdr ps37.hdr ps38.hdr ps39.hdr ps40.hdr ps41.hdr ps42.hdr ps43.hdr ps44.hdr ps45.hdr ps46.hdr ps47.hdr ps48.hdr ps49.hdr ps50.hdr ps51.hdr ps52.hdr ps53.hdr ps54.hdr ps55.hdr ps56.hdr ps57.hdr ps58.hdr ps59.hdr ps60.hdr ps61.hdr ps62.hdr ps63.hdr ps64.hdr ps65.hdr ps66.hdr ps67.hdr ps68.hdr ps69.hdr ps70.hdr ps71.hdr ps72.hdr ps73.hdr ps74.hdr ps75.hdr ps76.hdr ps77.hdr ps78.hdr ps79.hdr ps80.hdr ps81.hdr ps82.hdr ps83.hdr ps84.hdr ps85.hdr ps86.hdr ps87.hdr ps88.hdr ps89.hdr ps90.hdr ps91.hdr ps92.hdr ps93.hdr ps94.hdr ps95.hdr ps96.hdr ps97.hdr ps98.hdr ps99.hdr ps100.hdr ps101.hdr ps102.hdr ps103.hdr ps104.hdr ps105.hdr ps106.hdr ps107.hdr ps108.hdr ps109.hdr ps110.hdr ps111.hdr ps112.hdr ps113.hdr ps114.hdr ps115.hdr ps116.hdr ps117.hdr ps118.hdr ps119.hdr ps120.hdr ps121.hdr ps122.hdr ps123.hdr ps124.hdr ps125.hdr ps126.hdr ps127.hdr ps128.hdr ps129.hdr ps130.hdr ps131.hdr ps132.hdr ps133.hdr ps134.hdr ps135.hdr ps136.hdr ps137.hdr ps138.hdr ps139.hdr ps140.hdr ps141.hdr ps142.hdr ps143.hdr ps144.hdr ps145.hdr"
        if os.path.splitext(os.path.basename(self.scene.livi_export_epw_name))[1] in (".epw", ".EPW"):
            epw = open(self.scene.livi_export_epw_name, "r")
            epwlines = epw.readlines()
            epwyear = epwlines[8].split(",")[0]
            if not os.path.isfile(self.newdir+"/"+os.path.splitext(os.path.basename(self.scene.livi_export_epw_name))[0]+".wea"):
                wea = open(self.newdir+"/"+os.path.splitext(os.path.basename(self.scene.livi_export_epw_name))[0]+".wea", "w")
                wea.write("place {0[1]}\nlatitude {0[6]}\nlongitude {0[7]}\ntime_zone {0[8]}\nsite_elevation {0[9]}weather_data_file_units 1\n".format(epwlines[0].split(",")))
                for epwline in epwlines[8:]:
                    wea.write("%s %s %s %s %s \n" % tuple(col for c, col in enumerate(epwline.split(",")) if c in (1, 2, 3, 14, 15)))
                wea.close()
            if not os.path.isfile(self.newdir+"/"+os.path.splitext(os.path.basename(self.scene.livi_export_epw_name))[0]+".mtx"):
                subprocess.call("gendaymtx -r -90 -m 1 {} > {}".format(self.newdir+"/"+os.path.splitext(os.path.basename(self.scene.livi_export_epw_name))[0]+".wea", self.newdir+"/"+os.path.splitext(os.path.basename(self.scene.livi_export_epw_name))[0]+".mtx"), shell=True) 
            mtx = open(self.newdir+"/"+os.path.splitext(os.path.basename(self.scene.livi_export_epw_name))[0]+".mtx", "r") 
            patch = 0
            vals = [0]
            fwd = datetime.datetime(int(epwyear), 1, 1).weekday()
            self.vecvals = [[x%24, (fwd+x)%7] for x in range(0,8760)]
    
            hour = 0
            for fvals in mtx.readlines():
                if fvals != "\n" and math.isnan(float(fvals.split(" ")[0])) == False:
                    vals[patch] = vals[patch] + round(float(fvals.split(" ")[0]) +  float(fvals.split(" ")[1]) + float(fvals.split(" ")[2]), 2)
                    self.vecvals[hour].append(round(float(fvals.split(" ")[0]) +  float(fvals.split(" ")[1]) + float(fvals.split(" ")[2]), 2))
                    hour += 1
                elif fvals != "\n" and math.isnan(float(fvals.split(" ")[0])) == True:
                    self.vecvals[hour].append(0)
                    hour += 1 
                else:
                    patch += 1
                    hour = 0
                    vals.append(0)
            
            mtx.close()       
            skyrad = open(self.filename+".whitesky", "w")    
            skyrad.write("void glow sky_glow \n0 \n0 \n4 1 1 1 0 \nsky_glow source sky \n0 \n0 \n4 0 0 1 180 \nvoid glow ground_glow \n0 \n0 \n4 1 1 1 0 \nground_glow source ground \n0 \n0 \n4 0 0 -1 180\n\n")
            skyrad.close()
            subprocess.call("oconv "+self.filename+".whitesky > "+self.filename+"-whitesky.oct", shell=True)
            subprocess.call("vwrays -ff -x 600 -y 600 -vta -vp 0 0 0 -vd 1 0 0 -vu 0 0 1 -vh 360 -vv 360 -vo 0 -va 0 -vs 0 -vl 0 | rcontrib -bn 146 -fo -ab 0 -ad 512 -n "+self.nproc+" -ffc -x 600 -y 600 -ld- -V+ -f tregenza.cal -b tbin -o p%d.hdr -m sky_glow "+self.filename+"-whitesky.oct", shell = True)
            
            for j in range(0, 146):
                subprocess.call("pcomb -s "+str(vals[j])+" p"+str(j)+".hdr > ps"+str(j)+".hdr", shell = True)
                subprocess.call(self.rm+"  p"+str(j)+".hdr", shell = True) 
            subprocess.call("pcomb -h  "+pcombfiles+" > "+self.newdir+"/"+os.path.splitext(os.path.basename(self.scene.livi_export_epw_name))[0]+".hdr", shell = True)    
            subprocess.call(self.rm+" ps*.hdr" , shell = True)            
            self.skyhdrexport(self.newdir+"/"+os.path.splitext(os.path.basename(self.scene.livi_export_epw_name))[0]+".hdr")
        elif os.path.splitext(os.path.basename(self.scene.livi_export_epw_name))[-1] in (".hdr", ".HDR"):
            self.skyhdrexport(self.scene.livi_export_epw_name)
        
    
    def hdrsky(self, rad_sky, skyfile):
        rad_sky.write("# Sky material\nvoid colorpict hdr_env\n7 red green blue "+skyfile+" angmap.cal sb_u sb_v\n0\n0\n\nhdr_env glow env_glow\n0\n0\n4 1 1 1 0\n\nenv_glow bubble sky\n0\n0\n4 0 0 0 500\n\n")
        rad_sky.close()
        
    def radmat(self, frame, export_op):
        self.scene.frame_set(frame)
        rad_mat = open(self.mat(frame), "w")
        for meshmat in bpy.data.materials:
            diff = [meshmat.diffuse_color[0]*meshmat.diffuse_intensity, meshmat.diffuse_color[1]*meshmat.diffuse_intensity, meshmat.diffuse_color[2]*meshmat.diffuse_intensity]
            if "calcsurf" in meshmat.name:
                meshmat.use_vertex_color_paint = 1
            if meshmat.use_shadeless == 1:
                rad_mat.write("# Antimatter material\nvoid antimatter " + meshmat.name.replace(" ", "_") +"\n1 void\n0\n0\n\n")
                
            elif meshmat.emit > 0:
                rad_mat.write("# Light material\nvoid light " + meshmat.name.replace(" ", "_") +"\n0\n0\n3 {:.2f} {:.2f} {:.2f}\n".format(meshmat.emit * diff[0], meshmat.emit * diff[1], meshmat.emit * diff[2]))
                for o in [o for o in bpy.data.objects if o.type == 'MESH']:
                    if meshmat in [om for om in o.data.materials]:
                        o['merr'] = 1
                        export_op.report({'INFO'}, o.name+" has a emission material. Basic export routine used with no modifiers.")
                        
            elif meshmat.use_transparency == False and meshmat.raytrace_mirror.use == True and meshmat.raytrace_mirror.reflect_factor >= 0.99:
                rad_mat.write("# Mirror material\nvoid mirror " + meshmat.name.replace(" ", "_") +"\n0\n0\n3 {0[0]} {0[1]} {0[2]}\n\n".format(meshmat.mirror_color))
                for o in [o for o in bpy.data.objects if o.type == 'MESH']:
                    if meshmat in [om for om in o.data.materials]:
                        o['merr'] = 1
                        export_op.report({'INFO'}, o.name+" has a mirror material. Basic export routine used with no modifiers.")
            
            elif meshmat.use_transparency == True and meshmat.transparency_method == 'RAYTRACE' and meshmat.alpha < 1.0 and meshmat.translucency == 0:
                if "{:.2f}".format(meshmat.raytrace_transparency.ior) == "1.52":
                    rad_mat.write("# Glass material\nvoid glass " + meshmat.name.replace(" ", "_") +"\n0\n0\n3 {:.3f} {:.3f} {:.3f}\n\n".format((1.0 - meshmat.alpha)*diff[0], (1.0 - meshmat.alpha)*diff[1], (1.0 - meshmat.alpha)*diff[2]))
                else:
                    rad_mat.write("# Glass material\nvoid glass " + meshmat.name.replace(" ", "_") +"\n0\n0\n4 {0:.3f} {1:.3f} {2:.3f} {3}\n\n".format((1.0 - meshmat.alpha)*diff[0], (1.0 - meshmat.alpha)*diff[1], (1.0 - meshmat.alpha)*diff[2], meshmat.raytrace_transparency.ior))
                 
            elif meshmat.use_transparency == True and meshmat.transparency_method == 'RAYTRACE' and meshmat.alpha < 1.0 and meshmat.translucency > 0.001:
                rad_mat.write("# Translucent material\nvoid trans " + meshmat.name.replace(" ", "_")+"\n0\n0\n7 {0[0]:.3f} {0[1]:.3f} {0[2]:.3f} {1} {2} {3} {4}\n\n".format(diff, meshmat.specular_intensity, 1.0 - meshmat.specular_hardness/511.0, 1.0 - meshmat.alpha, 1.0 - meshmat.translucency))
            
            elif meshmat.use_transparency == False and meshmat.raytrace_mirror.use == True and meshmat.raytrace_mirror.reflect_factor < 0.99:
                rad_mat.write("# Metal material\nvoid metal " + meshmat.name.replace(" ", "_") +"\n0\n0\n5 {0[0]:.3f} {0[1]:.3f} {0[2]:.3f} {1} {2}\n\n".format(diff, meshmat.specular_intensity, 1.0-meshmat.specular_hardness/511.0))
            else:
                rad_mat.write("# Plastic material\nvoid plastic " + meshmat.name.replace(" ", "_") +"\n0\n0\n5 {0[0]:.2f} {0[1]:.2f} {0[2]:.2f} {1:.2f} {2:.2f}\n\n".format(diff, meshmat.specular_intensity, 1.0-meshmat.specular_hardness/511.0))
        rad_mat.close()

    def obexport(self,frame, obs, obno, export_op):
        self.scene.frame_current = frame
        rad_poly = open(self.poly(frame), 'w')
        bpy.ops.object.select_all(action='DESELECT')
        for o in obs:
            try:
                o['merr']
            except:
                o['merr'] = 0
                
            o.select = True
            bpy.ops.export_scene.obj(filepath=self.obj(o.name, frame), check_existing=True, filter_glob="*.obj;*.mtl", use_selection=True, use_animation=False, use_mesh_modifiers=True, use_edges=False, use_normals=o.data.polygons[0].use_smooth, use_uvs=True, use_materials=True, use_triangles=True, use_nurbs=True, use_vertex_groups=True, use_blen_objects=True, group_by_object=False, group_by_material=False, keep_vertex_order=False, global_scale=1.0, axis_forward='Y', axis_up='Z', path_mode='AUTO')
            o.select = False
            objcmd = "obj2mesh -w -a "+self.mat(frame)+" "+self.obj(o.name, frame)+" "+self.mesh(o.name, frame)
            objrun = Popen(objcmd, shell = True, stderr = PIPE)
            for line in objrun.stderr:
                if 'fatal' in str(line):
                    o['merr'] = 1

            if o['merr'] == 0:
                rad_poly.write("void mesh id \n1 "+self.mesh(o.name, frame)+"\n0\n0\n\n")
    
            else:
                export_op.report({'INFO'}, o.name+" could not be converted into a Radiance mesh and simpler export routine has been used. No un-applied object modifiers will be exported.")
                o['merr'] = 0
                geomatrix = o.matrix_world
                for face in o.data.polygons:
                    try:
                        vertices = face.vertices[:]
                        rad_poly.write("# Polygon \n"+o.data.materials[face.material_index].name.replace(" ", "_") + " polygon " + "poly_"+o.data.name.replace(" ", "_")+"_"+str(face.index) + "\n0\n0\n"+str(3*len(face.vertices))+"\n")
                        try:
                            if o.data.shape_keys.key_blocks[0] and o.data.shape_keys.key_blocks[1]:
                                for vertindex in vertices:
                                    sk0 = o.data.shape_keys.key_blocks[0]
                                    sk0co = geomatrix*sk0.data[vertindex].co
                                    sk1 = o.data.shape_keys.key_blocks[1]
                                    sk1co = geomatrix*sk1.data[vertindex].co
                                    rad_poly.write(" " +str(sk0co[0]+(sk1co[0]-sk0co[0])*sk1.value) +  " " + str(sk0co[1]+(sk1co[1]-sk0co[1])*sk1.value) +" "+ str(sk0co[2]+(sk1co[2]-sk0co[2])*sk1.value) + "\n")
                        except:
                            for vertindex in vertices:
                                rad_poly.write(" " +str((geomatrix*o.data.vertices[vertindex].co)[0]) +  " " + str((geomatrix*o.data.vertices[vertindex].co)[1]) +" "+ str((geomatrix*o.data.vertices[vertindex].co)[2]) + "\n")
                        rad_poly.write("\n")
                    except:
                        export_op.report({'ERROR'},"Make sure your object "+o.name+" has an associated material")
            
        rad_poly.close()

    def obmexport(self, frame, obs, ob, export_op):
        self.scene.frame_current = frame
        rad_poly = open(self.poly(frame), 'w')
        for o in obs:
            if frame == 0:
                try:
                    o['merr']
                except:
                    o['merr'] = 0
                o.select = True
                bpy.ops.export_scene.obj(filepath=self.obj(o.name, frame), check_existing=True, filter_glob="*.obj;*.mtl", use_selection=True, use_animation=False, use_mesh_modifiers=True, use_edges=False, use_normals=o.data.polygons[0].use_smooth, use_uvs=True, use_materials=True, use_triangles=True, use_nurbs=True, use_vertex_groups=True, use_blen_objects=True, group_by_object=False, group_by_material=False, keep_vertex_order=False, global_scale=1.0, axis_forward='Y', axis_up='Z', path_mode='AUTO')
                o.select = False
#                bpy.ops.export_scene.obj(filepath=self.obj(obs.name, frame), check_existing=True, filter_glob="*.obj;*.mtl", use_selection=True, use_animation=False, use_apply_modifiers=True, use_edges=False, use_normals=True, use_uvs=True, use_materials=True, use_triangles=True, use_nurbs=True, use_vertex_groups=False, use_blen_objects=True, group_by_object=False, group_by_material=False, keep_vertex_order=False, global_scale=1.0, axis_forward='Y', axis_up='Z', path_mode='AUTO')
            objcmd = "obj2mesh -w -a "+self.mat(frame)+" "+self.obj(o.name, 0)+" "+self.mesh(o.name, frame)
            objrun = Popen(objcmd, shell = True, stderr = PIPE)
        
            for line in objrun.stderr:
                if 'fatal' in str(line):
                    o['merr'] = 1
       
            if o['merr'] == 0 and ob == 0:
                rad_poly.write("void mesh id \n1 "+self.mesh(o.name, frame)+"\n0\n0\n")
        
            elif o['merr'] == 1:        
                if frame == 0:
                    for geo in obs:
                        geomatrix = geo.matrix_world
                        for face in geo.data.polygons:
                            try:
                                vertices = face.vertices[:]
                                rad_poly.write("# Polygon \n"+geo.data.materials[face.material_index].name.replace(" ", "_") + " polygon " + "poly_"+geo.data.name.replace(" ", "_")+"_"+str(face.index) + "\n0\n0\n"+str(3*len(face.vertices))+"\n")
                                try:
                                    if geo.data.shape_keys.key_blocks[0] and geo.data.shape_keys.key_blocks[1]:
                                        for vertindex in vertices:
                                            sk0 = geo.data.shape_keys.key_blocks[0]
                                            sk0co = geomatrix*sk0.data[vertindex].co
                                            sk1 = geo.data.shape_keys.key_blocks[1]
                                            sk1co = geomatrix*sk1.data[vertindex].co
                                            rad_poly.write(" " +str(sk0co[0]+(sk1co[0]-sk0co[0])*sk1.value) +  " " + str(sk0co[1]+(sk1co[1]-sk0co[1])*sk1.value) +" "+ str(sk0co[2]+(sk1co[2]-sk0co[2])*sk1.value) + "\n")
                                except:
                                    for vertindex in vertices:
                                        rad_poly.write(" " +str((geomatrix*geo.data.vertices[vertindex].co)[0]) +  " " + str((geomatrix*geo.data.vertices[vertindex].co)[1]) +" "+ str((geomatrix*geo.data.vertices[vertindex].co)[2]) + "\n")
                                rad_poly.write("\n")
                            except:
                                export_op.report({'ERROR'},"Make sure your object "+geo.name+" has an associated material")
                            
        rad_poly.close()
        
    def radlights(self, frame):
        os.chdir(self.newdir)
        self.scene.frame_set(frame)
        rad_lights = open(self.lights(frame), "w")
        for geo in bpy.context.scene.objects:
            if geo.ies_name != "":
                iesname = os.path.splitext(os.path.basename(geo.ies_name))[0]
                subprocess.call("ies2rad -t default -m {} -l / -p {} -d{} -o {}-{} {}".format(geo.ies_strength, self.newdir, geo.ies_unit, iesname, frame, geo.ies_name), shell=True)
                if geo.type == 'LAMP':
                    if geo.parent:
                        geo = geo.parent                    
                    rad_lights.write("!xform -rx {0} -ry {1} -rz {2} -t {3[0]} {3[1]} {3[2]} {4}.rad\n\n".format((180/pi)*geo.rotation_euler[0], (180/pi)*geo.rotation_euler[1], (180/pi)*geo.rotation_euler[2], geo.location, self.newdir+"/"+iesname+"-"+str(frame)))    
                if 'lightarray' in geo.name:
                    spotmatrix = geo.matrix_world
                    rotation = geo.rotation_euler                    
                    for face in geo.data.polygons:
                        fx = sum([(spotmatrix*v.co)[0] for v in geo.data.vertices if v.index in face.vertices])/len(face.vertices)
                        fy = sum([(spotmatrix*v.co)[1] for v in geo.data.vertices if v.index in face.vertices])/len(face.vertices)
                        fz = sum([(spotmatrix*v.co)[2] for v in geo.data.vertices if v.index in face.vertices])/len(face.vertices)
                        rad_lights.write("!xform -rx {:.3f} -ry {:.3f} -rz {:.3f} -t {:.3f} {:.3f} {:.3f} {}\n".format((180/pi)*rotation[0], (180/pi)*rotation[1], (180/pi)*rotation[2], fx, fy, fz, self.newdir+"/"+iesname+"-"+str(frame)+".rad"))
        rad_lights.close()
        
    def rtexport(self, export_op):
    # Function for the exporting of Blender geometry and materials to Radiance files
        rtrace = open(self.rtrace, "w")       
        calcsurfverts = []
        calcsurffaces = []
        if 0 not in [len(geo.data.materials) for geo in bpy.data.objects if geo.type == 'MESH' and 'lightarray' not in geo.name and geo.hide == False and geo.layers[0] == True ]:
            for o, geo in enumerate(self.scene.objects):
                
                csf = []
                cverts = []
                cvox = []
                cvoy = []
                cvoz = []
                
                self.scene.objects.active = geo
                if geo.type == 'MESH' and 'lightarray' not in geo.name and geo.hide == False and geo.layers[0] == True:
                    bpy.ops.object.mode_set(mode = 'EDIT')
                    bpy.ops.mesh.select_all(action='SELECT')
                    bpy.ops.object.mode_set(mode = 'OBJECT')
                    mesh = geo.to_mesh(self.scene, True, 'PREVIEW', calc_tessface=False)
                    mesh.transform(geo.matrix_world)

                    if len([mat.name for mat in geo.material_slots if 'calcsurf' in mat.name]) != 0:

                        for face in mesh.polygons:
                            if "calcsurf" in str(mesh.materials[face.material_index].name):
                                vsum = Vector((0, 0, 0))
                                self.scene.objects.active = geo
                                geo.select = True
                                bpy.ops.object.mode_set(mode = 'OBJECT')                        
                                for vc in geo.data.vertex_colors:
                                    bpy.ops.mesh.vertex_color_remove()
#                                fnormx, fnormy, fnormz = face.normal[:]
                                if self.scene['cp'] == 0:                            
                                    for v in face.vertices:
                                        vsum = mesh.vertices[v].co + vsum
                                    fc = vsum/len(face.vertices)
                                    rtrace.write('{0[0]} {0[1]} {0[2]} {1[0]} {1[1]} {1[2]} \n'.format(fc, face.normal[:]))
                                                        
                                calcsurffaces.append((o, face))
                                csf.append(face.index)
                                geo['calc'] = 1
                                
                                for vert in face.vertices:
                                    if (mesh.vertices[vert]) not in calcsurfverts:
                                        vcentx, vcenty, vcentz = mesh.vertices[vert].co[:]
                                        vnormx, vnormy, vnormz = (mesh.vertices[vert].normal*geo.matrix_world.inverted())[:]
                                        
                                        if self.scene['cp'] == 1:
                                            rtrace.write('{0[0]} {0[1]} {0[2]} {1[0]} {1[1]} {1[2]} \n'.format(mesh.vertices[vert].co[:], (mesh.vertices[vert].normal*geo.matrix_world.inverted())[:]))
                                            
                                        calcsurfverts.append(mesh.vertices[vert])
                                        cvox.append(vcentx - geo.location[0]) 
                                        cvoy.append(vcenty - geo.location[1]) 
                                        cvoz.append(vcentz - geo.location[2])
                                        cverts.append(vert)
                                        
                                geo['cverts'] = cverts
                                geo['cvox'] = cvox
                                geo['cvoy'] = cvoy
                                geo['cvoz'] = cvoz
                        if geo['calc'] == 1:              
                            geo['cfaces'] = csf
                        
                        if self.scene.livi_export_calc_points == "1":
                            self.reslen = len(calcsurfverts)
                        else:
                            self.reslen = len(calcsurffaces)
                    else:
                        geo['calc'] = 0
                        for mat in geo.material_slots:
                            mat.material.use_transparent_shadows = True

            rtrace.close()    
            bpy.data.meshes.remove(mesh)
            self.export = 1
        else:
            self.export = 0
            for geo in self.scene.objects:
                if geo.type == 'MESH' and geo.name != 'lightarray' and geo.hide == False and geo.layers[0] == True:
                    if not geo.data.materials:
                        export_op.report({'ERROR'},"Make sure your object "+geo.name+" has an associated material") 
    
    def fexport(self, frame, export_op):
        try:
            subprocess.call("oconv -w "+self.lights(frame)+" "+self.sky(frame)+" "+self.mat(frame)+" "+self.poly(frame)+" > "+self.filebase+"-"+str(frame)+".oct", shell=True)
            self.export = 1
        except:
            export_op.report({'ERROR'},"There is a problem with geometry export. If created in another package simplify the geometry, and turn off smooth shading")
            self.export = 0
        self.scene.livi_display_panel = 0   

        export_op.report({'INFO'},"Export is finished")
        self.scene.frame_set(0)                      


#Compute solar position (altitude and azimuth in degrees) based on day of year (doy; integer), local solar time (lst; decimal hours), latitude (lat; decimal degrees), and longitude (lon; decimal degrees).
def solarPosition(doy, lst, lat, lon):
    #Set the local standard time meridian (lsm) (integer degrees of arc)
    lsm = int(lon/15)*15
    #Approximation for equation of time (et) (minutes) comes from the Wikipedia article on Equation of Time
    b = 2*math.pi*(doy-81)/364
    et = 9.87 * math.sin(2*b) - 7.53 * math.cos(b) - 1.5 * math.sin(b)
    #The following formulas adapted from the 2005 ASHRAE Fundamentals, pp. 31.13-31.16
    #Conversion multipliers
    degToRad = 2*math.pi/360
    radToDeg = 1/degToRad
    #Apparent solar time (ast)
    ast = lst + et/60 + (lsm-lon)/15
    #Solar declination (delta) (radians)
    delta = degToRad*23.45 * math.sin(2*math.pi*(284+doy)/365)
    #Hour angle (h) (radians)
    h = degToRad*15 * (ast-12)
     #Local latitude (l) (radians)
    l = degToRad*lat
    #Solar altitude (beta) (radians)
    beta = asin(cos(l) * cos(delta) * cos(h) + sin(l) * sin(delta))
    #Solar azimuth phi (radians)
    phi = acos((sin(beta) * sin(l) - sin(delta))/(cos(beta) * cos(l)))                                                                         
    #Convert altitude and azimuth from radians to degrees, since the Spatial Analyst's Hillshade function inputs solar angles in degrees
    altitude = radToDeg*beta
    if ast<=12:
        azimuth = radToDeg*phi
    else:
        azimuth = 360 - radToDeg*phi
    return([altitude, azimuth])         
    
def negneg(x):
    if float(x) < 0:
        x = 0
    return float(x)
    
def cyfc1(self):
    if bpy.data.scenes[0].render.engine == "CYCLES":
        for materials in bpy.data.materials:
            if materials.use_nodes == 1:
                try:
                    if 'calcsurf' in materials.name:
                        nt = materials.node_tree
                        nt.nodes["Attribute"].attribute_name = str(bpy.context.scene.frame_current)
                except Exception as e:
                    print(e, 'Something wrong with changing the material attribute name')  
        if hasattr(bpy.data.worlds, 'World'):
            if bpy.data.worlds["World"].use_nodes == False:
                bpy.data.worlds["World"].use_nodes = True
        nt = bpy.data.worlds[0].node_tree
        if hasattr(nt.nodes, 'Environment Texture'):    
            nt.nodes['Environment Texture'].image.filepath = bpy.context.scene['newdir']+"/%sp.hdr" %(bpy.context.scene.frame_current)
            nt.nodes['Environment Texture'].image.reload()  
        if hasattr(bpy.data.worlds[0].node_tree.nodes, 'Background'):
            try:
                bpy.data.worlds[0].node_tree.nodes["Background"].inputs[1].keyframe
            except:
                bpy.data.worlds[0].node_tree.nodes["Background"].inputs[1].keyframe_insert('default_value')
        bpy.data.worlds[0].use_nodes = 0
        ti.sleep(0.1)
        bpy.data.worlds[0].use_nodes = 1
    
