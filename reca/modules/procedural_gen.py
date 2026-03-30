# SPDX-License-Identifier: GPL-3.0-or-later
"""RECA Procedural Generator — algorithmic geometry creation."""

import bpy
import math
import random
from bpy.types import Operator, PropertyGroup
from bpy.props import (
    EnumProperty,
    FloatProperty,
    IntProperty,
    BoolProperty,
    FloatVectorProperty,
    PointerProperty,
)
from mathutils import Vector, Matrix


# ─────────────────────────────────────────────
#  Properties
# ─────────────────────────────────────────────

class RECA_PG_procedural_gen(PropertyGroup):
    gen_type: EnumProperty(
        name="Generator",
        items=[
            ('BUILDING', "Building", "Procedural buildings / architecture"),
            ('TERRAIN', "Terrain", "Height-map terrain"),
            ('TREE', "Tree", "Parametric tree"),
            ('ROCKS', "Rocks", "Scatter random rocks"),
            ('CITY', "City Block", "Grid of buildings"),
            ('ARRAY_PATTERN', "Array Pattern", "Geometric patterns"),
            ('SCATTER', "Object Scatter", "Scatter selected on surface"),
            ('PIPE', "Pipe Network", "Random pipe/tube network"),
        ],
        default='BUILDING',
    )

    seed: IntProperty(name="Seed", default=42, min=0)
    count: IntProperty(name="Count", default=10, min=1, max=1000)

    # Building
    bld_width: FloatProperty(name="Width", default=4.0, min=0.5, max=50.0)
    bld_depth: FloatProperty(name="Depth", default=4.0, min=0.5, max=50.0)
    bld_floors: IntProperty(name="Floors", default=5, min=1, max=100)
    bld_floor_height: FloatProperty(name="Floor Height", default=3.0, min=1.0, max=10.0)
    bld_windows: BoolProperty(name="Add Windows", default=True)
    bld_window_rows: IntProperty(name="Window Columns", default=4, min=1, max=20)

    # Terrain
    terr_size: FloatProperty(name="Size", default=20.0, min=1.0, max=500.0)
    terr_subdivisions: IntProperty(name="Subdivisions", default=64, min=4, max=512)
    terr_height: FloatProperty(name="Height Scale", default=3.0, min=0.1, max=50.0)
    terr_noise_scale: FloatProperty(name="Noise Scale", default=5.0, min=0.1, max=50.0)
    terr_octaves: IntProperty(name="Octaves", default=4, min=1, max=10)

    # Tree
    tree_trunk_height: FloatProperty(name="Trunk Height", default=4.0, min=0.5, max=20.0)
    tree_trunk_radius: FloatProperty(name="Trunk Radius", default=0.3, min=0.05, max=5.0)
    tree_branches: IntProperty(name="Branch Levels", default=3, min=1, max=6)
    tree_leaf_size: FloatProperty(name="Leaf Size", default=2.0, min=0.1, max=10.0)
    tree_leaf_density: IntProperty(name="Leaf Density", default=5, min=1, max=20)

    # Rocks
    rock_size_min: FloatProperty(name="Min Size", default=0.3, min=0.01, max=10.0)
    rock_size_max: FloatProperty(name="Max Size", default=1.5, min=0.01, max=10.0)
    rock_spread: FloatProperty(name="Spread", default=10.0, min=0.1, max=100.0)
    rock_roughness: FloatProperty(name="Roughness", default=0.7, min=0.0, max=2.0)

    # City
    city_grid_x: IntProperty(name="Grid X", default=5, min=1, max=20)
    city_grid_y: IntProperty(name="Grid Y", default=5, min=1, max=20)
    city_spacing: FloatProperty(name="Spacing", default=6.0, min=2.0, max=50.0)
    city_height_min: IntProperty(name="Min Floors", default=2, min=1, max=10)
    city_height_max: IntProperty(name="Max Floors", default=15, min=2, max=100)

    # Array pattern
    pattern_type: EnumProperty(
        name="Pattern",
        items=[
            ('GRID', "Grid", ""),
            ('RADIAL', "Radial", ""),
            ('SPIRAL', "Spiral", ""),
            ('FIBONACCI', "Fibonacci", ""),
        ],
        default='GRID',
    )
    pattern_rows: IntProperty(name="Rows", default=5, min=1, max=50)
    pattern_cols: IntProperty(name="Columns", default=5, min=1, max=50)
    pattern_spacing: FloatProperty(name="Spacing", default=2.0, min=0.1, max=20.0)
    pattern_radius: FloatProperty(name="Radius", default=5.0, min=0.1, max=50.0)
    pattern_scale_variation: FloatProperty(name="Scale Variation", default=0.0, min=0.0, max=1.0)

    # Scatter
    scatter_count: IntProperty(name="Count", default=50, min=1, max=5000)
    scatter_scale_min: FloatProperty(name="Scale Min", default=0.5, min=0.01, max=10.0)
    scatter_scale_max: FloatProperty(name="Scale Max", default=1.5, min=0.01, max=10.0)
    scatter_random_rotation: BoolProperty(name="Random Rotation", default=True)
    scatter_align_normal: BoolProperty(name="Align to Normal", default=True)

    # Pipe
    pipe_segments: IntProperty(name="Segments", default=8, min=3, max=30)
    pipe_radius: FloatProperty(name="Pipe Radius", default=0.15, min=0.01, max=2.0)
    pipe_length: FloatProperty(name="Segment Length", default=2.0, min=0.5, max=10.0)
    pipe_branches: IntProperty(name="Branches", default=4, min=1, max=20)


# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────

def _noise_2d(x, y, seed=0, octaves=4, scale=5.0):
    """Simple value noise approximation using sin-based hash."""
    val = 0.0
    amp = 1.0
    freq = scale
    for _ in range(octaves):
        n = math.sin(x * freq * 12.9898 + y * freq * 78.233 + seed) * 43758.5453
        n = n - math.floor(n)
        val += n * amp
        amp *= 0.5
        freq *= 2.0
    return val


def _new_collection(name):
    from ..utils import ensure_collection
    return ensure_collection(name)


# ─────────────────────────────────────────────
#  Generators
# ─────────────────────────────────────────────

class RECA_OT_proc_generate(Operator):
    """Generate procedural geometry"""
    bl_idname = "reca.proc_generate"
    bl_label = "Generate"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        pg = context.scene.reca_procedural_gen
        random.seed(pg.seed)
        gen = pg.gen_type

        col = _new_collection(f"RECA_{gen}")

        if gen == 'BUILDING':
            self._building(context, pg, col)
        elif gen == 'TERRAIN':
            self._terrain(context, pg, col)
        elif gen == 'TREE':
            self._tree(context, pg, col)
        elif gen == 'ROCKS':
            self._rocks(context, pg, col)
        elif gen == 'CITY':
            self._city(context, pg, col)
        elif gen == 'ARRAY_PATTERN':
            self._array_pattern(context, pg, col)
        elif gen == 'SCATTER':
            self._scatter(context, pg, col)
        elif gen == 'PIPE':
            self._pipe_network(context, pg, col)

        self.report({'INFO'}, f"Generated: {gen}")
        return {'FINISHED'}

    def _link_to_col(self, obj, col):
        col.objects.link(obj)
        if obj.name in bpy.context.scene.collection.objects:
            bpy.context.scene.collection.objects.unlink(obj)

    # ── Building ──
    def _building(self, context, pg, col):
        width = pg.bld_width
        depth = pg.bld_depth
        total_h = pg.bld_floors * pg.bld_floor_height

        # Main body
        bpy.ops.mesh.primitive_cube_add(
            size=1,
            location=(0, 0, total_h / 2),
            scale=(width, depth, total_h),
        )
        body = context.active_object
        body.name = "RECA_Building"
        self._link_to_col(body, col)

        # Floors lines
        for f in range(1, pg.bld_floors):
            z = f * pg.bld_floor_height
            bpy.ops.mesh.primitive_cube_add(
                size=1,
                location=(0, 0, z),
                scale=(width + 0.1, depth + 0.1, 0.05),
            )
            line = context.active_object
            line.name = f"RECA_Floor_Line_{f}"
            self._link_to_col(line, col)

        # Windows
        if pg.bld_windows:
            win_w = width / (pg.bld_window_rows + 1) * 0.6
            win_h = pg.bld_floor_height * 0.5
            for f in range(pg.bld_floors):
                z = f * pg.bld_floor_height + pg.bld_floor_height * 0.55
                for w in range(pg.bld_window_rows):
                    x = -width / 2 + (w + 1) * (width / (pg.bld_window_rows + 1))
                    bpy.ops.mesh.primitive_cube_add(
                        size=1,
                        location=(x, -depth / 2 - 0.02, z),
                        scale=(win_w, 0.05, win_h),
                    )
                    win = context.active_object
                    win.name = f"RECA_Window_{f}_{w}"
                    # Glass material
                    mat = bpy.data.materials.new(f"RECA_Glass_{f}_{w}")
                    mat.use_nodes = True
                    bsdf = mat.node_tree.nodes.get("Principled BSDF")
                    if bsdf:
                        bsdf.inputs["Base Color"].default_value = (0.6, 0.8, 1.0, 1.0)
                        bsdf.inputs["Roughness"].default_value = 0.05
                        bsdf.inputs["Transmission Weight"].default_value = 0.8
                    win.data.materials.append(mat)
                    self._link_to_col(win, col)

    # ── Terrain ──
    def _terrain(self, context, pg, col):
        bpy.ops.mesh.primitive_grid_add(
            x_subdivisions=pg.terr_subdivisions,
            y_subdivisions=pg.terr_subdivisions,
            size=pg.terr_size,
            location=(0, 0, 0),
        )
        terrain = context.active_object
        terrain.name = "RECA_Terrain"

        mesh = terrain.data
        for vert in mesh.vertices:
            h = _noise_2d(vert.co.x, vert.co.y,
                          seed=pg.seed,
                          octaves=pg.terr_octaves,
                          scale=pg.terr_noise_scale)
            vert.co.z = h * pg.terr_height

        mesh.update()
        # Add material
        mat = bpy.data.materials.new("RECA_Terrain_Mat")
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs["Base Color"].default_value = (0.2, 0.4, 0.15, 1.0)
            bsdf.inputs["Roughness"].default_value = 0.9
        terrain.data.materials.append(mat)
        self._link_to_col(terrain, col)

    # ── Tree ──
    def _tree(self, context, pg, col):
        # Trunk
        bpy.ops.mesh.primitive_cylinder_add(
            radius=pg.tree_trunk_radius,
            depth=pg.tree_trunk_height,
            location=(0, 0, pg.tree_trunk_height / 2),
        )
        trunk = context.active_object
        trunk.name = "RECA_Trunk"
        mat_trunk = bpy.data.materials.new("RECA_Bark")
        mat_trunk.use_nodes = True
        bsdf = mat_trunk.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs["Base Color"].default_value = (0.25, 0.15, 0.07, 1.0)
            bsdf.inputs["Roughness"].default_value = 0.95
        trunk.data.materials.append(mat_trunk)
        self._link_to_col(trunk, col)

        # Leaf clusters
        mat_leaf = bpy.data.materials.new("RECA_Leaves")
        mat_leaf.use_nodes = True
        bsdf = mat_leaf.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs["Base Color"].default_value = (0.15, 0.45, 0.1, 1.0)
            bsdf.inputs["Roughness"].default_value = 0.7

        top_z = pg.tree_trunk_height
        for level in range(pg.tree_branches):
            z = top_z + level * pg.tree_leaf_size * 0.6
            cluster_count = pg.tree_leaf_density - level
            radius = pg.tree_leaf_size * (1.0 - level * 0.2)
            for i in range(max(1, cluster_count)):
                angle = random.uniform(0, 2 * math.pi)
                dist = random.uniform(0, radius * 0.5)
                x = math.cos(angle) * dist
                y = math.sin(angle) * dist
                sz = radius * random.uniform(0.6, 1.0)
                bpy.ops.mesh.primitive_ico_sphere_add(
                    radius=sz,
                    subdivisions=2,
                    location=(x, y, z),
                )
                leaf = context.active_object
                leaf.name = f"RECA_Leaf_{level}_{i}"
                leaf.data.materials.append(mat_leaf)
                self._link_to_col(leaf, col)

    # ── Rocks ──
    def _rocks(self, context, pg, col):
        mat = bpy.data.materials.new("RECA_Rock")
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs["Base Color"].default_value = (0.35, 0.33, 0.3, 1.0)
            bsdf.inputs["Roughness"].default_value = 0.85

        for i in range(pg.count):
            size = random.uniform(pg.rock_size_min, pg.rock_size_max)
            x = random.uniform(-pg.rock_spread / 2, pg.rock_spread / 2)
            y = random.uniform(-pg.rock_spread / 2, pg.rock_spread / 2)

            bpy.ops.mesh.primitive_ico_sphere_add(
                radius=size,
                subdivisions=2,
                location=(x, y, size * 0.3),
            )
            rock = context.active_object
            rock.name = f"RECA_Rock_{i:03d}"
            # Deform to look rocky
            rock.scale = (
                random.uniform(0.6, 1.4),
                random.uniform(0.6, 1.4),
                random.uniform(0.4, 1.0),
            )
            rock.rotation_euler = (
                random.uniform(0, 0.5),
                random.uniform(0, 0.5),
                random.uniform(0, math.pi * 2),
            )
            # Displace vertices for roughness
            mesh = rock.data
            for v in mesh.vertices:
                offset = random.uniform(-pg.rock_roughness, pg.rock_roughness) * 0.15
                v.co += v.normal * offset
            mesh.update()
            rock.data.materials.append(mat)
            self._link_to_col(rock, col)

    # ── City ──
    def _city(self, context, pg, col):
        for gx in range(pg.city_grid_x):
            for gy in range(pg.city_grid_y):
                floors = random.randint(pg.city_height_min, pg.city_height_max)
                h = floors * 3.0
                w = pg.city_spacing * random.uniform(0.4, 0.8)
                d = pg.city_spacing * random.uniform(0.4, 0.8)
                x = gx * pg.city_spacing
                y = gy * pg.city_spacing
                bpy.ops.mesh.primitive_cube_add(
                    size=1,
                    location=(x, y, h / 2),
                    scale=(w, d, h),
                )
                bldg = context.active_object
                bldg.name = f"RECA_CityBldg_{gx}_{gy}"
                # Random color material
                mat = bpy.data.materials.new(f"RECA_CityMat_{gx}_{gy}")
                mat.use_nodes = True
                bsdf = mat.node_tree.nodes.get("Principled BSDF")
                if bsdf:
                    grey = random.uniform(0.3, 0.7)
                    bsdf.inputs["Base Color"].default_value = (grey, grey, grey * 0.95, 1.0)
                    bsdf.inputs["Roughness"].default_value = random.uniform(0.4, 0.9)
                bldg.data.materials.append(mat)
                self._link_to_col(bldg, col)

    # ── Array Pattern ──
    def _array_pattern(self, context, pg, col):
        positions = []
        pt = pg.pattern_type

        if pt == 'GRID':
            for r in range(pg.pattern_rows):
                for c in range(pg.pattern_cols):
                    positions.append((
                        (c - pg.pattern_cols / 2) * pg.pattern_spacing,
                        (r - pg.pattern_rows / 2) * pg.pattern_spacing,
                        0,
                    ))
        elif pt == 'RADIAL':
            for i in range(pg.count):
                angle = (2 * math.pi / pg.count) * i
                x = math.cos(angle) * pg.pattern_radius
                y = math.sin(angle) * pg.pattern_radius
                positions.append((x, y, 0))
        elif pt == 'SPIRAL':
            for i in range(pg.count):
                angle = i * 0.5
                r = pg.pattern_spacing * 0.3 * angle
                x = math.cos(angle) * r
                y = math.sin(angle) * r
                positions.append((x, y, 0))
        elif pt == 'FIBONACCI':
            golden = (1 + math.sqrt(5)) / 2
            for i in range(pg.count):
                angle = 2 * math.pi * i / (golden ** 2)
                r = pg.pattern_spacing * 0.3 * math.sqrt(i)
                x = math.cos(angle) * r
                y = math.sin(angle) * r
                positions.append((x, y, 0))

        for i, pos in enumerate(positions):
            bpy.ops.mesh.primitive_cube_add(size=0.5, location=pos)
            obj = context.active_object
            obj.name = f"RECA_Pattern_{i:03d}"
            if pg.pattern_scale_variation > 0:
                sv = 1.0 + random.uniform(-pg.pattern_scale_variation, pg.pattern_scale_variation)
                obj.scale = (sv, sv, sv)
            self._link_to_col(obj, col)

    # ── Scatter ──
    def _scatter(self, context, pg, col):
        source = context.active_object
        if source is None:
            self.report({'ERROR'}, "Select an object to scatter on")
            return

        mesh = source.data
        if not hasattr(mesh, 'polygons') or len(mesh.polygons) == 0:
            self.report({'ERROR'}, "Active object has no faces")
            return

        for i in range(pg.scatter_count):
            face = random.choice(mesh.polygons)
            verts = [mesh.vertices[v].co for v in face.vertices]
            # Random barycentric
            weights = [random.random() for _ in verts]
            total = sum(weights)
            weights = [w / total for w in weights]
            pos = Vector((0, 0, 0))
            for w, v in zip(weights, verts):
                pos += w * v
            pos = source.matrix_world @ pos

            bpy.ops.mesh.primitive_cube_add(size=0.3, location=pos)
            obj = context.active_object
            obj.name = f"RECA_Scatter_{i:03d}"
            s = random.uniform(pg.scatter_scale_min, pg.scatter_scale_max)
            obj.scale = (s, s, s)
            if pg.scatter_random_rotation:
                obj.rotation_euler = (
                    random.uniform(0, math.pi * 2),
                    random.uniform(0, math.pi * 2),
                    random.uniform(0, math.pi * 2),
                )
            if pg.scatter_align_normal:
                obj.rotation_euler.x = face.normal.x
                obj.rotation_euler.y = face.normal.y
            self._link_to_col(obj, col)

    # ── Pipe Network ──
    def _pipe_network(self, context, pg, col):
        mat = bpy.data.materials.new("RECA_Pipe_Mat")
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs["Base Color"].default_value = (0.5, 0.5, 0.55, 1.0)
            bsdf.inputs["Metallic"].default_value = 0.9
            bsdf.inputs["Roughness"].default_value = 0.3

        directions = [
            Vector((1, 0, 0)), Vector((-1, 0, 0)),
            Vector((0, 1, 0)), Vector((0, -1, 0)),
            Vector((0, 0, 1)), Vector((0, 0, -1)),
        ]

        for b in range(pg.pipe_branches):
            pos = Vector((0, 0, 0))
            for s in range(pg.pipe_segments):
                d = random.choice(directions)
                end = pos + d * pg.pipe_length
                mid = (pos + end) / 2

                bpy.ops.mesh.primitive_cylinder_add(
                    radius=pg.pipe_radius,
                    depth=pg.pipe_length,
                    location=mid,
                )
                pipe = context.active_object
                pipe.name = f"RECA_Pipe_{b}_{s}"
                # Align to direction
                z = Vector((0, 0, 1))
                if d != z and d != -z:
                    rot_axis = z.cross(d).normalized()
                    rot_angle = z.angle(d)
                    pipe.rotation_euler = Matrix.Rotation(rot_angle, 4, rot_axis).to_euler()
                elif d == -z:
                    pipe.rotation_euler = (math.pi, 0, 0)

                pipe.data.materials.append(mat)
                self._link_to_col(pipe, col)

                # Joint sphere
                bpy.ops.mesh.primitive_uv_sphere_add(
                    radius=pg.pipe_radius * 1.4,
                    location=end,
                    segments=12,
                    ring_count=8,
                )
                joint = context.active_object
                joint.name = f"RECA_Joint_{b}_{s}"
                joint.data.materials.append(mat)
                self._link_to_col(joint, col)

                pos = end


# ─────────────────────────────────────────────
#  UI
# ─────────────────────────────────────────────

def draw_panel(layout, context):
    pg = context.scene.reca_procedural_gen

    box = layout.box()
    box.label(text="Procedural Generator", icon='MOD_BUILD')
    box.prop(pg, "gen_type", text="")
    box.prop(pg, "seed")

    gt = pg.gen_type
    layout.separator()
    box = layout.box()

    if gt == 'BUILDING':
        box.label(text="Building", icon='HOME')
        box.prop(pg, "bld_width")
        box.prop(pg, "bld_depth")
        box.prop(pg, "bld_floors")
        box.prop(pg, "bld_floor_height")
        box.prop(pg, "bld_windows")
        if pg.bld_windows:
            box.prop(pg, "bld_window_rows")

    elif gt == 'TERRAIN':
        box.label(text="Terrain", icon='RNDCURVE')
        box.prop(pg, "terr_size")
        box.prop(pg, "terr_subdivisions")
        box.prop(pg, "terr_height")
        box.prop(pg, "terr_noise_scale")
        box.prop(pg, "terr_octaves")

    elif gt == 'TREE':
        box.label(text="Tree", icon='FORCE_WIND')
        box.prop(pg, "tree_trunk_height")
        box.prop(pg, "tree_trunk_radius")
        box.prop(pg, "tree_branches")
        box.prop(pg, "tree_leaf_size")
        box.prop(pg, "tree_leaf_density")

    elif gt == 'ROCKS':
        box.label(text="Rocks", icon='MESH_ICOSPHERE')
        box.prop(pg, "count")
        box.prop(pg, "rock_size_min")
        box.prop(pg, "rock_size_max")
        box.prop(pg, "rock_spread")
        box.prop(pg, "rock_roughness")

    elif gt == 'CITY':
        box.label(text="City Block", icon='MESH_GRID')
        box.prop(pg, "city_grid_x")
        box.prop(pg, "city_grid_y")
        box.prop(pg, "city_spacing")
        box.prop(pg, "city_height_min")
        box.prop(pg, "city_height_max")

    elif gt == 'ARRAY_PATTERN':
        box.label(text="Pattern", icon='PARTICLE_POINT')
        box.prop(pg, "pattern_type")
        if pg.pattern_type == 'GRID':
            box.prop(pg, "pattern_rows")
            box.prop(pg, "pattern_cols")
        else:
            box.prop(pg, "count")
        box.prop(pg, "pattern_spacing")
        if pg.pattern_type == 'RADIAL':
            box.prop(pg, "pattern_radius")
        box.prop(pg, "pattern_scale_variation", slider=True)

    elif gt == 'SCATTER':
        box.label(text="Object Scatter", icon='OUTLINER_OB_POINTCLOUD')
        box.prop(pg, "scatter_count")
        box.prop(pg, "scatter_scale_min")
        box.prop(pg, "scatter_scale_max")
        box.prop(pg, "scatter_random_rotation")
        box.prop(pg, "scatter_align_normal")

    elif gt == 'PIPE':
        box.label(text="Pipe Network", icon='CON_SPLINEIK')
        box.prop(pg, "pipe_segments")
        box.prop(pg, "pipe_radius")
        box.prop(pg, "pipe_length")
        box.prop(pg, "pipe_branches")

    layout.separator()
    layout.operator("reca.proc_generate", icon='PLAY', text="Generate")


# ─────────────────────────────────────────────
#  Registration
# ─────────────────────────────────────────────

classes = [
    RECA_PG_procedural_gen,
    RECA_OT_proc_generate,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.reca_procedural_gen = PointerProperty(type=RECA_PG_procedural_gen)


def unregister():
    del bpy.types.Scene.reca_procedural_gen
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
