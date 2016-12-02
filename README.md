# blender-gms2-vertex-buffer-export
Blender addon that exports to vertex buffers, made for GameMaker Studio 2

Required GameMaker Vertex Format Order:
```
{
  vertex_format_add_normal();
  vertex_format_add_texcoord();
  vertex_format_add_position_3d();
  vertex_format_add_color();
}
```
I use this order to make normals and uv optional, eventually
Perhaps support for custom attributes will come in the future?
