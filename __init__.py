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

bl_info = {
    "name": "Lighting Visualiser (LiVi)",
    "author": "Ryan Southall",
    "version": (0, 3, 0),
    "blender": (2, 6, 7),
    "api":"",
    "location": "3D View > Properties Panel",
    "description": "Radiance exporter and results visualiser",
    "warning": "This is a beta script. Some functionality is buggy",
    "wiki_url": "",
    "tracker_url": "",
    "category": "Import-Export"}

if "bpy" in locals():
    import imp
    imp.reload(livi_ui)
else:
    from io_livi import livi_ui

import bpy, os, sys, platform
from bpy.props import BoolProperty, IntProperty, FloatProperty, EnumProperty, StringProperty
#from . import livi_ui


if str(sys.platform) == 'darwin':
    if platform.architecture() == "64bit":
        os.environ["PATH"] = os.environ["PATH"] + ":/usr/local/radiance/bin:"+sys.path[0]+"/io_livi/osx/64" 
    else:
         os.environ["PATH"] = os.environ["PATH"] + ":/usr/local/radiance/bin:"+sys.path[0]+"/io_livi/osx"
    os.environ["RAYPATH"] = "/usr/local/radiance/lib:"+sys.path[0]+"/io_livi/lib"

elif str(sys.platform) == 'win32':
    if os.path.isdir(r"C:\Program Files (x86)\Radiance"):
        os.environ["PATH"] = os.environ["PATH"] + r";C:\Program Files (x86)\Radiance\bin;"+sys.path[0]+"\io_livi\windows" 
        os.environ["RAYPATH"] = r"C:\Program Files (x86)\Radiance\lib;"+sys.path[0]+"\io_livi\lib"
    elif os.path.isdir(r"C:\Program Files\Radiance"):
        os.environ["PATH"] = os.environ["PATH"] + r";C:\Program Files\Radiance\bin;"+sys.path[0]+"\io_livi\windows" 
        os.environ["RAYPATH"] = "C:\Program Files\Radiance\lib;"+sys.path[0]+"\io_livi\lib"
    else:
        print("Cannot find a valid Radiance directory. Please check that you have Radiance installed in either C:\Program Files(x86) (64bit windows) \
or C:\Program Files (32bit windows)")
              
elif str(sys.platform) == 'linux':
    os.environ["PATH"] = os.environ["PATH"] + ":/usr/local/radiance/bin:"+sys.path[0]+"/io_livi/linux"
    os.environ["RAYPATH"] = "/usr/local/radiance/lib:"+sys.path[0]+"/io_livi/lib"

def register():
    bpy.utils.register_module(__name__)
    
    bpy.types.Object.ies_name = StringProperty(name="Path", description="IES File", maxlen=1024, default="")
    bpy.types.Object.ies_strength = FloatProperty(name="Lamp strength:", description="Strength of IES lamp", min = 0, max = 1, default = 1)
    bpy.types.Object.ies_unit = EnumProperty(
            items=[("m", "Meters", ""),
                   ("c", "Centimeters", ""),
                    ("f", "Feet", ""),
                    ("i", "Inches", ""),
                    ],
            name="IES dimension",
            description="Specify the IES file measurement unit",
            default="m")
    

    # LiVi Export panel properties    
    Scene = bpy.types.Scene
    
    Scene.epwdat_name = StringProperty(name="Path", description="EPW processed data file", maxlen=1024, default="")

    Scene.livipath = StringProperty(name="LiVi Path", description="Path to files included with LiVi ", maxlen=1024, default=sys.path[0])        

    Scene.livi_anim = EnumProperty(
            items=[("0", "None", "export for a static scene"),
                   ("1", "Time", "export for a period of time"),
                    ("2", "Geometry", "export for Dynamic Daylight Simulation"),
                    ("3", "Material", "export for Dynamic Daylight Simulation"),
                    ("4", "Lights", "export for Dynamic Daylight Simulation"),
                   ],
            name="",
            description="Specify the animation type",
            default="0")
    
    Scene.livi_export_time_type = EnumProperty(
            items=[("0", "Moment", "export for a moment time"),
                   ("1", "DDS", "analysis over a year"),
                    ],
            name="",
            description="Specify the time type",
            default="0")      
    
    Scene.livi_export_time_type = EnumProperty(
            items=[("0", "Moment", "export for a moment time"),                 
                    ("1", "DDS", "analysis over a year"),
                    ],
            name="",
            description="Specify the time type",
            default="0") 
        
    Scene.livi_export_calc_points = EnumProperty(
            items=[("0", "Faces", "export faces for calculation points"),
                   ("1", "Vertices", "export vertices for calculation points"),
                   ],
            name="",
            description="Specify the type of geometry to act as calculation points",
            default="1")
            
    Scene.livi_export_geo_export = EnumProperty(
            items=[("0", "Static", "Static geometry export"),
                   ("1", "Dynamic", "Dynamic geometry export"),
                   ],
            name="",
            description="Specify the type of geometry to act as calculation points",
            default="0")
    
    Scene.livi_export_sky_type = EnumProperty(
            items=[
                   ("0", "Sunny", "CIE Sunny Sky description"),
                   ("1", "Partly Coudy", "CIE Sunny Sky description"),
                   ("2", "Coudy", "CIE Partly Cloudy Sky description"),
                   ("3", "DF Sky", "Daylight Factor Sky description"),
                   ("4", "HDR Sky", "HDR file sky"),
                   ("5", "None", "No Sky"),],
            name="",
            description="Specify the type of sky for the simulation",
            default="0")
    Scene.livi_export_sky_type_period = EnumProperty(
            items=[("0", "Sunny", "CIE Sunny Sky description"),
                   ("1", "Partly Coudy", "CIE Sunny Sky description"),
                   ("2", "Coudy", "CIE Partly Cloudy Sky description"),],
            name="",
            description="Specify the type of sky for the simulation",
            default="0")
    
    Scene.livi_export_standard_meridian = EnumProperty(
            items=[("0", "YST", ""),
                   ("1", "PST", ""),
                   ("2", "MST", ""),
                   ("3", "CST", ""),
                   ("4", "EST", ""),
                   ("GMT", "GMT", ""),
                   ("6", "CET", ""),
                   ("7", "EET", ""),
                   ("8", "AST", ""),
                   ("9", "GST", ""),
                   ("10", "IST", ""),
                   ("11", "JST", ""),
                   ("12", "NZST", ""),                   ],
            name="Meridian",
            description="Specify the local meridian",
            default="GMT")
    
    Scene.livi_export_summer_meridian = EnumProperty(
            items=[("0", "YDT", ""),
                   ("1", "PDT", ""),
                   ("2", "MDT", ""),
                   ("3", "CDT", ""),
                   ("4", "EDT", ""),
                   ("BST", "BST", ""),
                   ("6", "CEST", ""),
                   ("7", "EEST", ""),
                   ("8", "ADT", ""),
                   ("9", "GDT", ""),
                   ("10", "IDT", ""),
                   ("11", "JDT", ""),
                   ("12", "NZDT", ""),                   ],
            name="Meridian",
            description="Specify the local Summertime meridian",
            default="BST")
    Scene.livi_export_latitude = FloatProperty(
            name="Latitude", description="Site Latitude",
            min=-90, max=90, default=52)
    Scene.livi_export_longitude = FloatProperty(
            name="Longitude", description="Site Longitude",
            min=-15, max=15, default=0)        
    Scene.livi_export_start_month = IntProperty(
            name="Month", description="Month of the year",
            min=1, max=12, default=1)
    Scene.livi_export_start_day = IntProperty(
            name="Day", description="Day of the year",
            min=1, max=31, default=1)
    Scene.livi_export_start_day30 = IntProperty(
            name="Day", description="Day of the year",
            min=1, max=30, default=1)
    Scene.livi_export_start_day28 = IntProperty(
            name="Day", description="Day of the year",
            min=1, max=28, default=1)
    Scene.livi_export_start_hour = IntProperty(
            name="Hour", description="Hour of the day",
            min=1, max=24, default=12)
    Scene.livi_export_end_month = IntProperty(
            name="Month", description="Month of the year",
            min=1, max=12, default=1)
    Scene.livi_export_end_day = IntProperty(
            name="Day", description="Day of the year",
            min=1, max=31, default=1)
    Scene.livi_export_end_day30 = IntProperty(
            name="Day", description="Day of the year",
            min=1, max=30, default=1)
    Scene.livi_export_end_day28 = IntProperty(
            name="Day", description="Day of the year",
            min=1, max=28, default=1)
    Scene.livi_export_end_hour = IntProperty(
            name="Hour", description="Hour of the day",
            min=1, max=24, default=12)
    Scene.livi_export_interval = FloatProperty(
            name="", description="Interval time",
            min=0.1, max=730, default=1)
    Scene.livi_export_summer_enable = BoolProperty(
            name="Daylight saving", description="Enable daylight saving clock",
            default=True)
    Scene.livi_export_epw_name = StringProperty(
            name="", description="Name of the EnergyPlus weather file", default="")
    Scene.livi_export_hdr_name = StringProperty(
            name="", description="Name of the HDR angmap file", default="")
            
# LiVi Calculation panel ui elements

    Scene.livi_metric = EnumProperty(
            items=[("0", "Illuminance", "Lux calculation"),
                   ("1", "Irradiance", "W/m**2 calculation"),
			  ("3", "Glare", "Glare calculation"),
                   ],
            name="",
            description="specify the lighting metric required",
            default="0")
    Scene.livi_metricdf = EnumProperty(
            items=[("0", "Illuminance", "Lux calculation"),
                   ("1", "Irradiance", "W/m**2 calculation"),
                   ("2", "DF", "Daylight Factor calculation"),
                   ("3", "Glare", "Glare calculation"),
                   ],
            name="",
            description="specify the lighting metric required",
            default="0")
    Scene.livi_metricdds = EnumProperty(
            items=[("0", "Cumulative light exposure", "Cumulative luxhours"),
                   ("1", "Cumulative radiation calculation", "kWh/m**2"),
                   ("4", "Daylight availability", "Daylight availability"),
			  ],
            name="",
            description="specify the lighting metric required",
            default="0")	
    Scene.livi_calc_acc = EnumProperty(
            items=[("0", "Low", "Quick but innacurate simulation"),
                   ("1", "Medium", "Medium accuracy and speed"),
                   ("2", "High", "Slow but accurate simulation"),
                   ("3", "Custom", "Specify command line arguments for Radiance below")
                   ],
            name="",
            description="Specify the speed and accuracy of the simulation",
            default="0")
    Scene.livi_calc_dastart_hour = IntProperty(
            name="Hour", description="Starting hour for occupancy",
            min=1, max=24, default=8)  
    Scene.livi_calc_daend_hour = IntProperty(
            name="Hour", description="Ending hour for occupancy",
            min=1, max=24, default=19)
    Scene.livi_calc_min_lux = IntProperty(
            name="Lux", description="Minimum Lux level required",
            min=1, max=2000, default=200)
    Scene.livi_calc_da_weekdays = BoolProperty(
            name="Weekdays only", description="Calculate Daylight availability for weekdays only",
            default=True)
    Scene.livi_calc_custom_acc = StringProperty(
            name="", description="Custom Radiance simulation parameters", default="")   
    Scene.livi_calc_mtx_name = StringProperty(
            name="", description="Name of the generated matrix file", default="")
            
    # LiVi Display panel properties
    Scene.livi_display_legend = IntProperty(
            name="Legend Display", description="Shows a colour coded legend for the results in the 3D view",
            default=0)
    Scene.livi_display_panel = IntProperty(
            name="Display Panel", description="Shows the Disply Panel",
            default=0)
    Scene.livi_disp_3d = BoolProperty(
            name="3D Display", description="Enable 3D results analysis",
            default=0)
    Scene.livi_render_view = BoolProperty(
            name="OpenGL Display", description="Enable OpenGL 3D results view",
            default=True)            
    Scene.livi_disp_3dlevel = FloatProperty(
            name="3D level", description="Level of 3D effect",
            min=0.1, max=5000, default=2)
          
    Scene.livi_display_respoints = bpy.props.BoolProperty(
            name="Display",
            description="Display results on vertices/faces",
            default=False)

    Scene.livi_display_sel_only = bpy.props.BoolProperty(
            name="Selected only",
            description="Only display results on selected vertices/faces",
            default=True)
    
    Scene.livi_display_rp_fs = bpy.props.IntProperty(
            name="Font size",
            description="Font size for point display",
            default=13)
    
def unregister():
#    import bpy
    bpy.utils.unregister_module(__name__)


