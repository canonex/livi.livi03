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

import bpy, os, subprocess, colorsys, multiprocessing, sys, math, datetime
from math import pi
from subprocess import PIPE, Popen, STDOUT

nproc = multiprocessing.cpu_count()

class LiVi_c(object):  
    def __init__(self, lexport, prev_op):
        self.acc = lexport.scene.livi_calc_acc
        self.scene = bpy.context.scene
        if str(sys.platform) != 'win32':
            if lexport.scene.livi_export_time_type == "0" or lexport.scene.livi_anim == "1":
                self.simlistn = ("illumout", "irradout", "dfout")
                self.simlist = (" |  rcalc  -e '$1=47.4*$1+120*$2+11.6*$3' ", " |  rcalc  -e '$1=$1' ", " |  rcalc  -e '$1=(47.4*$1+120*$2+11.6*$3)/100' ")
                self.unit = ("Lux", "W/m^2", "DF %", "Glare")
            else:
                self.simlistn = ("cumillumout", "cumirradout", "", "", "daout")
                self.simlist = (" |  rcalc  -e '$1=47.4*$1+120*$2+11.6*$3' ", " |  rcalc  -e '$1=$1' ")
                self.unit = ("Luxhours", "Wh/m^2", "", "", "DA %")
        if str(sys.platform) == 'win32':
            if lexport.scene.livi_export_time_type == "0"  or lexport.scene.livi_anim == "1":
                self.simlistn = ("illumout", "irradout", "dfout")
                self.simlist = (' |  rcalc  -e "$1=47.4*$1+120*$2+11.6*$3" ', ' |  rcalc  -e "$1=$1" ', ' |  rcalc  -e "$1=(47.4*$1+120*$2+11.6*$3)/100" ')
                self.unit = ("Lux", "W/m^2", "DF %", "Glare")
            else:
                self.simlistn = ("cumillumout", "cumirradout", "", "", "daout")
                self.simlist = (' |  rcalc  -e "$1=47.4*$1+120*$2+11.6*$3" ', ' |  rcalc  -e "$1=$1" ')
                self.unit = ("Luxhours", "Wh/m^2", "", "", "DA %")
        try:
            if os.lstat(lexport.filebase+".rtrace").st_size == 0:
                if prev_op.name == "Radiance Preview":
                    self.rad_prev(lexport, prev_op)
                elif lexport.metric == "3":
                    self.rad_glare(lexport, prev_op)
                else:
                    prev_op.report({'ERROR'},"There are no calcsurf materials. Associate a 'calcsurf' material with an object.")
            else:
                if prev_op.name == "Radiance Preview":
                    self.rad_prev(lexport, prev_op)
                elif lexport.metric == "3":
                    self.rad_glare(lexport, prev_op)
                elif lexport.metric == "4":
                    self.dayavail(lexport ,prev_op)
                else:
                    self.rad_calc(lexport, prev_op)
        except:
            pass
        
    def rad_prev(self, lexport, prev_op):
        if os.path.isfile(lexport.filebase+"-0.poly"):
            cams = [obs for obs in (lexport.scene.objects) if obs.type == 'CAMERA']
            if len(cams) != 0:
                cang = cams[0].data.angle*180/pi
                vv = cang * bpy.context.scene.render.resolution_y/bpy.context.scene.render.resolution_x
                spotmatrix = cams[0].matrix_world
                subprocess.call("rvu -n "+str(nproc)+" -vv "+str(vv)+" -vh "+str(cang)+" -vd "+str(-spotmatrix[0][2])+" "+str(-spotmatrix[1][2])+" "+str(-spotmatrix[2][2])+" -vp "+str(cams[0].location[0])+" "+str(cams[0].location[1])+" "+str(cams[0].location[2])+" "+lexport.pparams(lexport.scene.livi_calc_acc)+" "+lexport.filebase+"-"+str(lexport.scene.frame_current)+".oct &", shell = True)
            else:
                prev_op.report({'ERROR'}, "There is no camera in the scene. Radiance preview will not work")
        else:
            prev_op.report({'ERROR'},"Missing export file. Make sure you have exported the scene.")
    
    def rad_calc(self, lexport, calc_op):
        lexport.clearscened()
        res = [[] for frame in range(0, bpy.context.scene.frame_end+1)]
        for frame in range(0, bpy.context.scene.frame_end+1):
            if os.path.isfile(lexport.filebase+"-"+str(frame)+".af"):
                subprocess.call(lexport.rm+" "+lexport.filebase+"-"+str(frame)+".af", shell=True)
            rtcmd = "rtrace -n "+str(nproc)+" -w "+lexport.sparams(self.acc)+" -h -ov -I -af "+lexport.filebase+"-"+str(frame)+".af "+lexport.filebase+"-"+str(frame)+".oct  < "+lexport.filebase+".rtrace "+self.simlist[int(lexport.metric)] #+" | tee "+lexport.newdir+lexport.fold+self.simlistn[int(lexport.metric)]+"-"+str(frame)+".res" 
            rtrun = Popen(rtcmd, shell = True, stdout=PIPE, stderr=STDOUT)
            resfile = open(lexport.newdir+lexport.fold+self.simlistn[int(lexport.metric)]+"-"+str(frame)+".res", 'w')
            for line in rtrun.stdout:
                res[frame].append(float(line.decode()))
                resfile.write(str(line.decode()))
            resfile.close()
        self.resapply(res, lexport)
        calc_op.report({'INFO'}, "Calculation is finished.")
        
    def rad_glare(self, lexport, calc_op):
        scene = bpy.context.scene
        gfiles=[]
        cams = [obs for obs in (scene.objects) if obs.type == 'CAMERA']

        if len(cams) != 0:
            for frame in range(0, scene.frame_end+1):
                spotmatrix = cams[0].matrix_world
                glarecmd = "rpict -vth -vh 180 -vv 180 -x 800 -y 800 -vd "+str(-spotmatrix[0][2])+" "+str(-spotmatrix[1][2])+" "+str(-spotmatrix[2][2])+" -vp "+str(cams[0].location[0])+" "+str(cams[0].location[1])+" "+str(cams[0].location[2])+" "+lexport.sparams(self.acc)+" "+lexport.filename+"-"+str(frame)+".oct | evalglare -c glare"+str(frame)+".hdr"
                glarerun = Popen(glarecmd, shell = True, stdout = PIPE)
                for line in glarerun.stdout:
                    if line.decode().split(",")[0] == 'dgp':
                        glaretext = line.decode().replace(',', ' ').replace("#INF", "").split(' ')
                        glaretf = open(lexport.filebase+".glare", "w")
                        glaretf.write("{0:0>2d}/{1:0>2d} {2:0>2d}:{3:0>2d}\ndgp: {4:.3f}\ndgi: {5:.3f}\nugr: {6:.3f}\nvcp: {7:.3f}\ncgi: {8:.3f}\nLveil: {9:.3f}\n".format(lexport.simtimes[frame].day, lexport.simtimes[frame].month, lexport.simtimes[frame].hour, lexport.simtimes[frame].minute, *[float(x) for x in glaretext[6:12]]))
                        glaretf.close()
                subprocess.call("pcond -u 300 glare"+str(frame)+".hdr > glaretm"+str(frame)+".hdr", shell=True)
                subprocess.call(lexport.cat+" "+lexport.filename+".glare | psign -h 32 -cb 0 0 0 -cf 40 40 40 | pcompos glaretm"+str(frame)+".hdr 0 0 - 800 550 > glare"+str(frame)+".hdr", shell=True)
                subprocess.call(lexport.rm+" glaretm"+str(frame)+".hdr", shell=True)                    
                        
                gfile={"name":"glare"+str(frame)+".hdr"}
                gfiles.append(gfile)

            if "glare0.hdr" in bpy.data.scenes["Scene"].sequence_editor.sequences_all:
                bpy.ops.sequencer.delete()

            bpy.ops.sequencer.image_strip_add( directory = lexport.newdir, \
                    files = gfiles, \
                    frame_start=0, \
                    channel=2, \
                    filemode=9)
        else:
            calc_op.report({'ERROR'}, "There is no camera in the scene. Create one for glare analysis")
        lexport.scene.livi_display_panel = 0
   
    def dayavail(self, lexport, calc_op):
        lexport.clearscened()
        res = [[0] * lexport.reslen for frame in range(0, bpy.context.scene.frame_end+1)]
        wd = (7, 5)[int(lexport.scene.livi_calc_da_weekdays)]
        fwd = datetime.datetime(2010, 1, 1).weekday()
        vecvals = [[x%24, (fwd+x)%7] for x in range(0,8760)]
        if os.path.splitext(os.path.basename(lexport.scene.livi_export_epw_name))[1] in (".hdr", ".HDR"):
            skyrad = open(lexport.filebase+".whitesky", "w")    
            skyrad.write("void glow sky_glow \n0 \n0 \n4 1 1 1 0 \nsky_glow source sky \n0 \n0 \n4 0 0 1 180 \nvoid glow ground_glow \n0 \n0 \n4 1 1 1 0 \nground_glow source ground \n0 \n0 \n4 0 0 -1 180\n\n")
            skyrad.close() 
            mtx = open(lexport.scene.livi_calc_mtx_name, "r")
            hour = 0
            mtxlines = mtx.readlines()
            mtx.close() 
            for fvals in mtxlines[:]:
                if fvals != "\n" and math.isnan(float(fvals.split(" ")[0])) == False:
                    vecvals[hour].append(round(float(fvals.split(" ")[0]) +  float(fvals.split(" ")[1]) + float(fvals.split(" ")[2]), 2))
                    hour += 1
                elif fvals != "\n" and math.isnan(float(fvals.split(" ")[0])) == True:
                    vecvals[hour].append(0)
                    hour += 1 
                else:
                    hour = 0
        else:
            vecvals = lexport.vecvals  

        for frame in range(0, bpy.context.scene.frame_end+1):
            hours = 0
            sensarray = [[] for x in range(0, 146)]
            subprocess.call("oconv -w "+lexport.lights(frame)+" "+lexport.filename+".whitesky "+lexport.mat(frame)+" "+lexport.poly(frame)+" > "+lexport.filename+"-"+str(frame)+"ws.oct", shell = True)
            if not os.path.isdir(lexport.newdir+lexport.fold+"s_data"):
                os.makedirs(lexport.newdir+lexport.fold+"s_data")
            
            subprocess.call(lexport.cat+lexport.filebase+".rtrace | rcontrib -h -I -fo -bn 146 -ab 3 -ad 4096 -lw 0.0003 -n "+lexport.nproc+" -f tregenza.cal -b tbin -o "+lexport.newdir+lexport.fold+"s_data/"+str(frame)+"-sensor%d.dat -m sky_glow "+lexport.filename+"-"+str(frame)+"ws.oct", shell = True)
            
            for i in range(0, 146):
                sensfile = open(lexport.newdir+"/s_data/"+str(frame)+"-sensor"+str(i)+".dat", "r")
                for sens in sensfile.readlines():
                    sensarray[i].append(sens.strip("\n").split("\t"))
                sensfile.close()
            for l, readings in enumerate(vecvals):
                finalillu = []
                for i in range(0, 146):
                    if float(readings[0]) >= lexport.scene.livi_calc_dastart_hour and float(readings[0]) < lexport.scene.livi_calc_daend_hour and float(readings[1]) < wd:
                        for j, sens in enumerate(sensarray[i]):
                            senreading = 179*(0.265*float(sens[0])+0.67*float(sens[1])+0.065*float(sens[2]))
                            if i == 0:
                                finalillu.append(senreading*readings[i+2])
                                if j == 0:
                                    hours += 1
                            else:
                                finalillu[j] += senreading*readings[i+2]
                for k, reading in enumerate(finalillu):
                    if reading > lexport.scene.livi_calc_min_lux:
                        res[frame][k] += 1
                        
            for r in range(0, len(res[frame])):
                if hours != 0:
                    res[frame][r] = res[frame][r]*100/hours

            daresfile = open(lexport.newdir+"/"+self.simlistn[int(lexport.metric)]+"-"+str(frame)+".res", "w")
            daresfile.write("{:.2f}\n".format(*res[frame]))
            daresfile.close()
        calc_op.report({'INFO'}, "Calculation is finished.") 
        self.resapply(res, lexport) 
        
    def resapply(self, res, lexport):
        maxres = []
        minres = []
        avres = []
        
        for frame in range(0, lexport.scene.frame_end+1):
            maxres.append(max(res[frame]))
            minres.append(min(res[frame]))
            avres.append(sum(res[frame])/len(res[frame]))
            
        self.scene['resav'] = avres
        self.scene['resmax'] = maxres
        self.scene['resmin'] = minres

        for frame in range(0, lexport.scene.frame_end+1):
            rgb = []
            lcol_i = []
            mcol_i = 0
            f = 0
            for i in range(0, len(res[frame])):
                h = 0.75*(1-(res[frame][i]-min(lexport.scene['resmin']))/(max(lexport.scene['resmax']) + 0.01 - min(lexport.scene['resmin'])))
                rgb.append(colorsys.hsv_to_rgb(h, 1.0, 1.0))
            cno = 0

            for geo in self.scene.objects:
                bpy.ops.object.select_all(action = 'DESELECT')
                self.scene.objects.active = None
                try:
                    if geo['calc'] == 1:
                        self.scene.objects.active = geo
                        geo.select = True
                        if frame == 0:
                            while len(geo.data.vertex_colors) > 0:
                                bpy.ops.mesh.vertex_color_remove()
                            
                        bpy.ops.mesh.vertex_color_add()
                        geo.data.vertex_colors[frame].name = str(frame)
                        vertexColour = geo.data.vertex_colors[frame]
                 
                        for face in geo.data.polygons:
                            if "calcsurf" in str(geo.data.materials[face.material_index].name):
                                if self.scene['cp'] == 1:
                                    for loop_index in face.loop_indices:
                                        v = geo.data.loops[loop_index].vertex_index
                                        col_i = [vi for vi, vval in enumerate(geo['cverts']) if v == geo['cverts'][vi]][0]
                                        lcol_i.append(col_i)
                                        vertexColour.data[loop_index].color = rgb[col_i+mcol_i]
                                    
                                if self.scene['cp'] == 0:
                                    for loop_index in face.loop_indices:
                                        vertexColour.data[loop_index].color = rgb[f]
                                    f += 1
                           
                        cno = cno + len(geo['cverts'])
                        mcol_i = len(list(set(lcol_i)))   
        
                except Exception as e:
                    print(e)

        lexport.scene.livi_display_panel = 1
        
        for frame in range(0, self.scene.frame_end+1):
            bpy.ops.anim.change_frame(frame = frame)
            for geo in self.scene.objects:
                try:
                    if geo['calc'] == 1:
                        for vc in geo.data.vertex_colors:
                            if frame == int(vc.name):
                                vc.active = 1
                                vc.active_render = 1
                                vc.keyframe_insert("active")
                                vc.keyframe_insert("active_render")
                            else:
                                vc.active = 0
                                vc.active_render = 0
                                vc.keyframe_insert("active")
                                vc.keyframe_insert("active_render")
                except Exception as e:
                    print(e)
           
        
        bpy.ops.wm.save_mainfile(check_existing = False)
