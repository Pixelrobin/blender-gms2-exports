bl_info = {

	'name'        : 'Export GameMaker Studio 2 Vertex Buffer (.vb)',
	'author'      : 'Michael Savchuk',
	'version'     : ( 1, 0, 0 ),
	'blender'     : ( 2, 7, 8 ),
	'location'    : 'File > Export',
	'description' : 'Export 3D Vertex Buffers for GameMaker Studio 2',
	'warning'     : '',
	'wiki_url'    : '',
	'tracker_url' : 'https://twitter.com/thepixelrobin',
	'category'    : 'Import-Export'

}

'''
MIT License

Copyright (c) 2016 Michael Savchuk

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

As an overriding clause, you may not sell this software, modified or not. You must keep it open source.

Usage Notes:
    Build your 3D model, select it, then go to File > Export > GameMaker Studio 2 Vertex Buffer.
    Set options as desired, export, load it as a buffer in gamemaker, and convert to a vertex buffer (GM SCRIPT COMING SOON).
    This creates a raw binary file that gamemaker can load natively.
    Using Edge Split and marking sharp edges is recommended, as is setting up a proper UV map. You can use vertex colors too.
	This script isn't done, but it's in a stable state at the moment. I have more ideas of things I could add.

Contact me:
	twitter: https://twitter.com/thepixelrobin (@thepixelrobin)

Conceptually Based on Martin Crownover's work:
    url: http://martincrownover.com
    e-mail: martin {at} martincrownover {dot} com
	(This addon was based on his in terms of general concept, but I rewrote it from scratch)
    
Additional credits:
	Lots of this was done with the help of Michael McFabulous: https://twitter.com/MaddeMichael
		(Especially with his guide: https://forum.yoyogames.com/index.php?threads/guide-getting-started-with-3d-in-gms2-project-download.12145/)

    Original script that Martin wrote was edited off Jeff LaMarche's: http://iphonedevelopment.blogspot.com
		(I also used some of Jeff's newer scripts as a reference when making this one)

    BenRK helped Martin fix up his original script, and in turn indirectly helped with this one

Formatting notes:
	Yes, I like to pad and align a lot of things, I come from javascript users, ok?
	I commented a bunch of this for people who don't know python or the blender api, I didn't when I started this.
'''

# There's more import stuff after the function
import bpy
import struct
import math

def write_vb( ctx, fp, p ):

	# Note: Instead of manually selecting the object, can't I just access it with ctx?

	o  = ctx.active_object      # Selected object
	s  = bpy.context.scene      # Current scene
	fn = False                  # Do we need to flip normals?
	om = ctx.active_object.mode # Store the current object mode for later
	
	# First we make sure that the object is the only thing selected
	bpy.ops.object.mode_set( mode = 'OBJECT' )
	bpy.ops.object.select_all( action = 'DESELECT' )
	o.select         = True
	s.objects.active = o
	
	# Then, we copy the object and it's data
	ocd     = o.data.copy()              # Object copy data
	oc      = o.copy()                   # Object copy
	oc.data = ocd                        # Set the object copy data to the copied data
	bpy.context.scene.objects.link( oc ) # Link the object copy to the current scene
	
	# Next, we select the object copy
	bpy.ops.object.select_all( action = 'DESELECT' )
	oc.select        = True
	s.objects.active = oc
	
	# Lastly, we apply all the properties and transformations and stuff (Kinda in order of export property appearance)
	
	# Apply modifiers if needed
	if p.apply_modifiers: bpy.ops.object.convert( target = 'MESH' )
	
	# Triangulate if needed
	if p.triangulate:
		bpy.ops.object.mode_set( mode = 'EDIT' )     # Change to edit mode
		bpy.ops.mesh.select_all( action = 'SELECT' ) # Select all vertices
		bpy.ops.mesh.quads_convert_to_tris(          # Triangulate the object

			quad_method = 'BEAUTY',
			ngon_method = 'BEAUTY'

		)
		s.update()                                   # Update the current scene (idk why)
		bpy.ops.object.mode_set( mode = 'OBJECT' )   # Reset to object mode
	
	# Flip coordinates if needed
	for a in range( 0, 2 ):
		if p.flip_axis[ a ]:
			bpy.context.object.scale[ a ] *= -1 # Negate Y object scale       
			fn = True                           # We'll need to flip normals later
	
	# Do all the orientation stuff
	if p.change_orientation == 'ZUP':       # Z up, need to flip on z axis
		bpy.context.object.scale[ 2 ] *= -1 # Negate Z object scale
	elif p.change_orientation == 'YUP':     # Y up, need to rotate X by 90d
		bpy.context.object.rotation_euler[ 0 ] += math.radians( 90 )
		fn = True
	
	# Apply additional scaling to the object
	bpy.context.object.scale[ 0 ] *= p.scale
	bpy.context.object.scale[ 1 ] *= p.scale
	bpy.context.object.scale[ 2 ] *= p.scale
	
	# Apply object transforms
	bpy.ops.object.transform_apply(
		
		location = True,
		rotation = True,
		scale    = True
	
	)

	# Flip normals if needed
	if fn:
		bpy.ops.object.mode_set( mode = 'EDIT' )   # We need to do it in edit mode
		bpy.ops.mesh.flip_normals()                # Flippity-flop
		bpy.ops.object.mode_set( mode = 'OBJECT' ) # Reset to object mode, you know the drill (activate drill sounds) (sorry, it's late')
	
	# And now it's time to write to the file!
	# Required GameMaker Vertex Format Order:
	# {
	#     vertex_format_add_normal();      // 3 32bit floats, 4 bytes for each
	#     vertex_format_add_texcoord();    // 2 32bit floats, 4 bytes for each
	#     vertex_format_add_position_3d(); // 3 32bit floats, 4 bytes for each
	#     vertex_format_add_color();       // 4 Unsigned ints, 1 byte for each
	# }
	# I use this order to make normals and uv optional, eventually

	f   = open( fp, 'wb' )  # Open file for writing binary
	m   = oc.data           # Get the actual mesh
	vrt = m.vertices        # Mesh vertices

	# Check to see if vertex colors or uv colors exist
	cc  = len( m.vertex_colors ) > 0
	cuv = len( m.uv_layers     ) > 0

	# Use vertex colors if they exist, otherwise use defaults (DefaultVertexColors class, defined below this function)
	if cc: cl = m.vertex_colors.active.data
	else:  cl = [ DefaultVertexColors() ]

	# Use uv coordinates if they exist, otherwise use defaults (DefaultUVCoordinates class, defined below this function)
	if cuv: uvc = m.uv_layers.active.data
	else:   uvc = [ DefaultUVCoordinates() ]

	# Convert bools to ints for exporting
	cc  = int( cc )
	cuv = int( cuv )

	# Ok, ok, NOW we export the stuff
	# If you don't know what is happening here, here's some docs: https://www.blender.org/api/blender_python_api_2_78_0/bpy.types.Mesh.html
	# This also uses the struct library, here some docs: https://docs.python.org/3/library/struct.html
	# The '<' character is used to signify little endian mode, I'm not sure what that is or if it's needed
	for g in m.polygons:
		s = g.loop_start
		i = 0

		for v in g.vertices:
			c  = cl [ ( s + i ) * cc  ].color
			uv = uvc[ ( s + i ) * cuv ].uv
			
			# It's all just a bunch of binary to me
			f.write( struct.pack( '<3f', vrt[ v ].normal[ 0 ], vrt[ v ].normal[ 1 ], vrt[ v ].normal[ 2 ] ) ) # Vertex normal
			if p.flip_uvs: f.write( struct.pack( '<2f', uv[ 0 ], 1.0 - uv[ 1 ] ) )                            # Vertex uv flipped
			else: f.write( struct.pack( '<2f', uv[ 0 ], uv[ 1 ] ) )                                           # Vertex uv
			f.write( struct.pack( '<3f', vrt[ v ].co[ 0 ], vrt[ v ].co[ 1 ], vrt[ v ].co[ 2 ] ) )             # Vertex position
			f.write( struct.pack( '<4B',                                                                      # Vertex color 

				math.floor( 255 * c[ 0 ] ), # Red
				math.floor( 255 * c[ 1 ] ), # Green
				math.floor( 255 * c[ 2 ] ), # Blue
				255                         # Alpha, right now, this just defaults to full
			
			) )

			if    i == 2: break
			else: i += 1
	
	# Delete defaults if applicable
	if cc  == 0: del cl [ 0 ]
	if cuv == 0: del uvc[ 0 ]

	# close the file
	f.close()
	
	# Delete the object copy
	bpy.ops.object.delete() 
	
	# Reselect the original object
	o.select = True
	bpy.context.scene.objects.active = o

	# Reset to default edit mode
	bpy.ops.object.mode_set( mode = om )

	# Tell blender we done
	return { 'FINISHED' } 

# Default vertex colors if missing
class DefaultVertexColors():
	color = [ 1.0, 1.0, 1.0 ]

# Default uv coordinates if missing
class DefaultUVCoordinates():
	uv = [ 0.0, 0.0 ]

# ExportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty, BoolProperty, BoolVectorProperty, EnumProperty, FloatProperty
from bpy.types import Operator

# This is the thingy class that makes it all work the above function was just to seperate code
class ExportVertexBuffer(Operator, ExportHelper):
	'''Export a vertex buffer for use with Gamemaker Studio 2'''
	bl_idname = "export_object.vb"                       # important since its how bpy.ops.import_test.some_data is constructed
	bl_label = "Export Gamemaker Studio 2 Vertex Buffer"
	bl_options = { 'PRESET' }                            # This makes it so you can set operator presets when exporting

	# ExportHelper mixin class uses this
	filename_ext = ".vb" # No, not Visual Basic but Vertex Buffer
	
	# Umm, this exists. It was in the blender template. Idk why. Dont' touch it I guess?
	filter_glob = StringProperty(

		default = "*.txt",
		options = { 'HIDDEN' },
		maxlen  = 255,  # Max internal buffer length, longer would be clamped.
	
	)

	# List of operator properties, the attributes will be assigned
	# to the class instance from the operator settings before calling.
	# ^ Fancy language from the template, these are all the settings
	# You need to import all the different properties in the 2nd import line above the ExportSomeData class
	# A list of all the property types: https://www.blender.org/api/blender_python_api_2_78_0/bpy.props.html
	apply_modifiers = BoolProperty(
		
		name        = 'Apply modifiers',
		description = 'Apply object modifiers before exporting',
		default     = True
		
	)
	
	flip_uvs = BoolProperty(
	
		name        = 'Flip UVs vertically',
		description = 'Flip UV coordinates on the y axis',
		default     = True
	
	)

	flip_axis = BoolVectorProperty(
		
		name = 'Flip on',
		description = 'Flips coordinates of mesh in desired directions\nPlease note that setting the mesh to Z up flips the z coordinates',
		default = ( False, False, False ),
		subtype = 'XYZ'
	
	)
	
	triangulate = BoolProperty(
	
		name        = 'Triangulate Mesh',
		description = 'Convert all faces in the mesh to triangles\nBeauty mode will be used for both quads and polygons',
		default     = True
	
	)

	change_orientation = EnumProperty(
	
		name        = 'Reorientate',
		description = "Make your mesh point the right way according to your camera's up vector",
		items       = ( ( 'NON',   'None',   'No additional changes'                                                   ),
		                ( 'ZUP',   'Z up',   'Use if your camera up vector is (0, 0, 1)\nFlips coordinates on Z axis'  ),
		                ( 'YUP',   'Y up',   'Use if your camera up vector is (0, 1, 0)\nRotate 90 degrees on X'       ) ),
		default     = 'ZUP'
		
	)
	
	scale = FloatProperty(
		
		name        = 'Scale',
		description = 'Adjust the scale before exporting',
		default     = 1.0,
		
	)

	# This is what happens when you press the button to export
	def execute(self, context):
		# We just moved the function to the start for readability or something
		return write_vb( context, self.filepath, self.properties )
	
	# This hunk of code just makes it so you can only export meshes
	@classmethod
	def poll(cls, context):
		return context.active_object.type in ['MESH', 'CURVE', 'SURFACE', 'FONT']

# Only needed if you want to add into a dynamic menu
# ^v Template code, no idea what is going on :\ I think this adds it to the file > export menu?
def menu_func_export( self, context ): self.layout.operator( ExportSomeData.bl_idname, text = 'Export GameMaker Studio 2 Vertex Buffer' )

# So this adds the class to blender officially, so blender gets to know it a bit :)
def register():
	bpy.utils.register_class( ExportVertexBuffer )           # Add the command
	bpy.types.INFO_MT_file_export.append( menu_func_export ) # Add to menu.... I think?

# And this is when you need to have this break up with blender and never talk to it again
def unregister():
	bpy.utils.unregister_class(ExportSomeData)
	bpy.types.INFO_MT_file_export.remove(menu_func_export)

# This umm, runs the script once it's imported, I think
if __name__ == "__main__":
	register()
	# uncomment next line to export as soon as script loads, useful for dev, not useful for actual usage
	# bpy.ops.export_object.vb('INVOKE_DEFAULT')