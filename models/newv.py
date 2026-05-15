"""
╔══════════════════════════════════════════════════════════════╗
║           ROBOT NAVIGATOR — Blender N-Panel Addon            ║
║  Scripting → Run Script → N-панель → вкладка "Robot Nav"     ║
╠══════════════════════════════════════════════════════════════╣
║  Чтобы добавить новую сцену:                                 ║
║  1. Напиши функцию _build_<name>()                           ║
║  2. Создай SceneMeta с пресетами                             ║
║  3. Добавь в SCENE_REGISTRY одной строкой                    ║
╚══════════════════════════════════════════════════════════════╝
"""

import bpy
import mathutils
import math
import heapq
import random
from dataclasses import dataclass, field
from typing import List, Tuple, Callable, Optional


# ══════════════════════════════════════════════════════════════
#  SCENE META — описание одного помещения
# ══════════════════════════════════════════════════════════════

@dataclass
class SceneMeta:
    """
    Все данные об одной сцене.
    Координаты — мировые (x, y).
    """
    id:            str
    label:         str
    robot_name:    str
    goal_name:     str
    robot_start:   Tuple[float, float]
    goal_default:  Tuple[float, float]
    robot_presets: List[Tuple[float, float, str]] = field(default_factory=list)
    goal_presets:  List[Tuple[float, float, str]] = field(default_factory=list)
    builder:       Optional[Callable] = None


# ══════════════════════════════════════════════════════════════
#  СЦЕНА 1 — Офис 15×28
# ══════════════════════════════════════════════════════════════

def _build_office():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    W, L, H = 15, 28, 10

    def mat(name, color):
        m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
        m.diffuse_color = color
        return m

    floor_m = mat("FloorTile", (0.18, 0.18, 0.18, 1))
    wall_m  = mat("WallMat",   (0.72, 0.72, 0.72, 1))
    table_m = mat("TableMat",  (0.05, 0.05, 0.05, 1))
    robot_m = mat("RobotMat",  (0.1,  0.6,  1.0,  1))
    goal_m  = mat("GoalMat",   (1.0,  0.8,  0.0,  1))

    def add_cube(name, loc, sc, m):
        bpy.ops.mesh.primitive_cube_add(location=loc)
        o = bpy.context.active_object
        o.name = name; o.scale = sc
        bpy.ops.object.transform_apply(scale=True)
        o.data.materials.append(m)

    bpy.ops.mesh.primitive_plane_add(size=1, location=(W/2, L/2, 0))
    fl = bpy.context.active_object
    fl.name = "Floor"; fl.scale = (W, L, 1)
    bpy.ops.object.transform_apply(scale=True)
    fl.data.materials.append(floor_m)

    add_cube("Wall_Back",  (W/2, 0,   H/2), (W/2, 0.1, H/2), wall_m)
    add_cube("Wall_Front", (W/2, L,   H/2), (W/2, 0.1, H/2), wall_m)
    add_cube("Wall_Right", (W,   L/2, H/2), (0.1, L/2, H/2), wall_m)
    add_cube("Wall_Left",  (0,   L/2, H/2), (0.1, L/2, H/2), wall_m)

    def add_table(x, y, sx, sy):
        bpy.ops.mesh.primitive_cube_add(location=(x, y, 0.5))
        o = bpy.context.active_object
        o.name = "OfficeTable"; o.scale = (sx/2, sy/2, 0.5)
        bpy.ops.object.transform_apply(scale=True)
        o.data.materials.append(table_m)

    add_table(4,    26,   7,   2)
    add_table(13,   26,   3,   2)
    add_table(1.5,  18,   2.5, 8)
    add_table(13,   18,   2.5, 6)
    add_table(10,   8,    8,   1.5)
    add_table(4.5,  5,    1.5, 5)
    add_table(10,   2,    8,   1.5)

    bpy.ops.mesh.primitive_cylinder_add(radius=0.4, depth=0.2, location=(2, 2, 0.1))
    r = bpy.context.active_object; r.name = "Robot_Sim"
    r.data.materials.append(robot_m)

    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.4, location=(13, 22, 0.5))
    g = bpy.context.active_object; g.name = "Goal_Marker"
    g.data.materials.append(goal_m)

    bpy.context.view_layer.update()


OFFICE_SCENE = SceneMeta(
    id           = "office",
    label        = "Офис (15x28)",
    robot_name   = "Robot_Sim",
    goal_name    = "Goal_Marker",
    robot_start  = (2.0,  2.0),
    goal_default = (13.0, 22.0),
    robot_presets = [
        (2.0,  2.0,  "Вход (2, 2)"),
        (7.5,  14.0, "Центр (7.5, 14)"),
        (2.0,  24.0, "Угол СЗ (2, 24)"),
        (7.5,  11.0, "Коридор (7.5, 11)"),
        (13.0, 2.0,  "Угол ЮВ (13, 2)"),
    ],
    goal_presets = [
        (13.0, 22.0, "Зона А (13, 22)"),
        (7.5,  25.0, "Зона Б (7.5, 25)"),
        (2.0,  12.0, "Зона В (2, 12)"),
        (13.0, 12.0, "Зона Г (13, 12)"),
        (7.5,  2.0,  "Зона Д (7.5, 2)"),
    ],
    builder = _build_office,
)


# ══════════════════════════════════════════════════════════════
#  СЦЕНА 2 — Склад 20×30
# ══════════════════════════════════════════════════════════════

def _build_warehouse():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    W, L, H = 20, 30, 8

    def mat(name, color):
        m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
        m.diffuse_color = color
        return m

    floor_m = mat("WH_Floor", (0.30, 0.28, 0.25, 1))
    wall_m  = mat("WH_Wall",  (0.60, 0.58, 0.55, 1))
    shelf_m = mat("WH_Shelf", (0.40, 0.25, 0.10, 1))
    robot_m = mat("RobotMat", (0.1,  0.6,  1.0,  1))
    goal_m  = mat("GoalMat",  (1.0,  0.8,  0.0,  1))

    def add_cube(name, loc, sc, m):
        bpy.ops.mesh.primitive_cube_add(location=loc)
        o = bpy.context.active_object
        o.name = name; o.scale = sc
        bpy.ops.object.transform_apply(scale=True)
        o.data.materials.append(m)

    bpy.ops.mesh.primitive_plane_add(size=1, location=(W/2, L/2, 0))
    fl = bpy.context.active_object
    fl.name = "Floor"; fl.scale = (W, L, 1)
    bpy.ops.object.transform_apply(scale=True)
    fl.data.materials.append(floor_m)

    add_cube("Wall_Back",  (W/2, 0,   H/2), (W/2,  0.15, H/2), wall_m)
    add_cube("Wall_Front", (W/2, L,   H/2), (W/2,  0.15, H/2), wall_m)
    add_cube("Wall_Right", (W,   L/2, H/2), (0.15, L/2,  H/2), wall_m)
    add_cube("Wall_Left",  (0,   L/2, H/2), (0.15, L/2,  H/2), wall_m)

    # 3 ряда × 4 секции стеллажей
    for row_x in [4.0, 10.0, 16.0]:
        for sec_y in [5.0, 11.0, 17.0, 23.0]:
            add_cube("Shelf", (row_x, sec_y, 1.5), (1.0, 2.0, 1.5), shelf_m)

    bpy.ops.mesh.primitive_cylinder_add(radius=0.4, depth=0.2, location=(2, 2, 0.1))
    r = bpy.context.active_object; r.name = "Robot_Sim"
    r.data.materials.append(robot_m)

    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.4, location=(18, 27, 0.5))
    g = bpy.context.active_object; g.name = "Goal_Marker"
    g.data.materials.append(goal_m)

    bpy.context.view_layer.update()


WAREHOUSE_SCENE = SceneMeta(
    id           = "warehouse",
    label        = "Склад (20x30)",
    robot_name   = "Robot_Sim",
    goal_name    = "Goal_Marker",
    robot_start  = (2.0,  2.0),
    goal_default = (18.0, 27.0),
    robot_presets = [
        (2.0,  2.0,  "Вход (2, 2)"),
        (7.0,  2.0,  "Пост А (7, 2)"),
        (13.0, 2.0,  "Пост Б (13, 2)"),
        (2.0,  15.0, "Центр лев (2, 15)"),
        (18.0, 2.0,  "Пост В (18, 2)"),
    ],
    goal_presets = [
        (18.0, 27.0, "Разгрузка (18, 27)"),
        (2.0,  27.0, "Зона А (2, 27)"),
        (10.0, 15.0, "Центр (10, 15)"),
        (18.0, 15.0, "Зона Б (18, 15)"),
        (10.0, 2.0,  "Зона В (10, 2)"),
    ],
    builder = _build_warehouse,
)


# ══════════════════════════════════════════════════════════════
#  ГЛАВНЫЙ РЕЕСТР — добавляй новые сцены сюда
# ══════════════════════════════════════════════════════════════

SCENE_REGISTRY: List[SceneMeta] = [
    OFFICE_SCENE,
    WAREHOUSE_SCENE,
    # MY_NEW_SCENE,   <-- добавляй сюда
]


def get_scene_meta(scene_id: str) -> SceneMeta:
    for s in SCENE_REGISTRY:
        if s.id == scene_id:
            return s
    return SCENE_REGISTRY[0]

def scene_enum_items(self, context):
    return [(s.id, s.label, "") for s in SCENE_REGISTRY]


# ══════════════════════════════════════════════════════════════
#  CORE LOGIC — AABB + Theta*
# ══════════════════════════════════════════════════════════════

def get_obstacle_boxes(exclude_names):
    boxes = []
    for obj in bpy.context.scene.objects:
        if obj.name in exclude_names or obj.type != 'MESH':
            continue
        corners = [obj.matrix_world @ mathutils.Vector(c) for c in obj.bound_box]
        xs = [c.x for c in corners]; ys = [c.y for c in corners]; zs = [c.z for c in corners]
        if (max(zs) - min(zs)) < 0.05:
            continue
        boxes.append((min(xs), max(xs), min(ys), max(ys)))
    return boxes


def compute_bounds(margin=1.0):
    all_x, all_y = [], []
    for obj in bpy.context.scene.objects:
        if obj.type != 'MESH':
            continue
        corners = [obj.matrix_world @ mathutils.Vector(c) for c in obj.bound_box]
        all_x.extend(c.x for c in corners)
        all_y.extend(c.y for c in corners)
    if not all_x:
        return None
    return (
        math.floor(min(all_x)) - margin,
        math.ceil(max(all_x))  + margin,
        math.floor(min(all_y)) - margin,
        math.ceil(max(all_y))  + margin,
    )


def build_grid(obstacle_boxes, bounds, resolution, robot_radius):
    min_x, max_x, min_y, max_y = bounds
    W = int(math.ceil((max_x - min_x) / resolution))
    H = int(math.ceil((max_y - min_y) / resolution))
    grid = [[False] * H for _ in range(W)]
    r = robot_radius
    for (ox1, ox2, oy1, oy2) in obstacle_boxes:
        ix1 = max(0, int((ox1 - r - min_x) / resolution))
        ix2 = min(W-1, int((ox2 + r - min_x) / resolution))
        iy1 = max(0, int((oy1 - r - min_y) / resolution))
        iy2 = min(H-1, int((oy2 + r - min_y) / resolution))
        for ix in range(ix1, ix2+1):
            for iy in range(iy1, iy2+1):
                grid[ix][iy] = True
    return grid, W, H


def world_to_grid(wx, wy, min_x, min_y, res):
    return int((wx - min_x) / res), int((wy - min_y) / res)

def grid_to_world(gx, gy, min_x, min_y, res):
    return min_x + gx * res + res / 2, min_y + gy * res + res / 2


def build_nav_grid(props, exclude_names):
    """Строит навигационную сетку по текущей сцене."""
    bounds = compute_bounds()
    if not bounds:
        return None, 0, 0, None
    boxes = get_obstacle_boxes(exclude_names)
    grid, W, H = build_grid(boxes, bounds, props.grid_resolution, props.robot_radius)
    return grid, W, H, bounds


def random_free_world_pos(grid, W, H, bounds, res, exclude_cell=None):
    """
    Случайная свободная мировая позиция.
    exclude_cell: (gx, gy) — ячейка вокруг которой делаем отступ (≥3 ячейки),
                  чтобы робот и цель не оказались вплотную.
    """
    min_x, _, min_y, _ = bounds[0], bounds[1], bounds[2], bounds[3]
    free = [
        (x, y) for x in range(W) for y in range(H)
        if not grid[x][y]
        and (exclude_cell is None or abs(x - exclude_cell[0]) > 3 or abs(y - exclude_cell[1]) > 3)
    ]
    if not free:
        return None, None
    gx, gy = random.choice(free)
    return grid_to_world(gx, gy, bounds[0], bounds[2], res)


class ThetaStar:
    def __init__(self, grid, W, H):
        self.grid = grid; self.W = W; self.H = H

    @staticmethod
    def h(ax, ay, bx, by):
        dx, dy = abs(ax-bx), abs(ay-by)
        return (dx+dy) + (1.4142-2)*min(dx,dy)

    def los(self, x0, y0, x1, y1):
        dx, dy = abs(x1-x0), abs(y1-y0)
        sx = 1 if x0<x1 else -1; sy = 1 if y0<y1 else -1
        err = dx-dy; cx, cy = x0, y0
        while True:
            if not (0<=cx<self.W and 0<=cy<self.H): return False
            if self.grid[cx][cy]: return False
            if cx==x1 and cy==y1: return True
            e2 = 2*err
            if e2>-dy: err-=dy; cx+=sx
            if e2< dx: err+=dx; cy+=sy

    def plan(self, sx, sy, gx, gy):
        if self.grid[sx][sy] or self.grid[gx][gy]: return None
        g  = {(sx,sy): 0.0}
        par= {(sx,sy): (sx,sy)}
        heap = [(self.h(sx,sy,gx,gy), sx, sy)]
        closed = set()
        while heap:
            _, cx, cy = heapq.heappop(heap)
            if (cx,cy) in closed: continue
            closed.add((cx,cy))
            if (cx,cy)==(gx,gy): return self._recon(par,gx,gy)
            px, py = par[(cx,cy)]
            for nx, ny in self._nb(cx,cy):
                if (nx,ny) in closed: continue
                if self.los(px,py,nx,ny):
                    ng = g[(px,py)] + math.hypot(nx-px,ny-py)
                    if ng < g.get((nx,ny), 1e18):
                        g[(nx,ny)]=ng; par[(nx,ny)]=(px,py)
                        heapq.heappush(heap,(ng+self.h(nx,ny,gx,gy),nx,ny))
                else:
                    step = 1.4142 if abs(nx-cx)+abs(ny-cy)==2 else 1.0
                    ng = g[(cx,cy)]+step
                    if ng < g.get((nx,ny), 1e18):
                        g[(nx,ny)]=ng; par[(nx,ny)]=(cx,cy)
                        heapq.heappush(heap,(ng+self.h(nx,ny,gx,gy),nx,ny))
        return None

    def _nb(self, x, y):
        return [(x+dx,y+dy) for dx in(-1,0,1) for dy in(-1,0,1)
                if (dx or dy) and 0<=x+dx<self.W and 0<=y+dy<self.H
                and not self.grid[x+dx][y+dy]]

    def _recon(self, par, gx, gy):
        path=[]; node=(gx,gy)
        while True:
            path.append(node); prev=par[node]
            if prev==node: break
            node=prev
        return list(reversed(path))


# ══════════════════════════════════════════════════════════════
#  SIMULATION RUNNER
# ══════════════════════════════════════════════════════════════

def run_simulation(props):
    log = []; L = lambda m: (log.append(m), print(m))

    robot = bpy.data.objects.get(props.robot_object)
    goal  = bpy.data.objects.get(props.goal_object)
    if not robot: return [f"❌ Объект '{props.robot_object}' не найден!"]
    if not goal:  return [f"❌ Объект '{props.goal_object}' не найден!"]

    L(f"📍 Старт: ({robot.location.x:.2f}, {robot.location.y:.2f})")
    L(f"🎯 Цель:  ({goal.location.x:.2f},  {goal.location.y:.2f})")

    exclude = {props.robot_object, props.goal_object, "Floor", "RobotPath"}
    grid, W, H, bounds = build_nav_grid(props, exclude)
    if grid is None: return ["❌ Нет mesh-объектов в сцене!"]

    min_x, _, min_y, _ = bounds
    res = props.grid_resolution
    L(f"🗺️  Сетка {W}×{H}")

    sx, sy = world_to_grid(robot.location.x, robot.location.y, min_x, min_y, res)
    gx, gy = world_to_grid(goal.location.x,  goal.location.y,  min_x, min_y, res)
    sx=max(0,min(W-1,sx)); sy=max(0,min(H-1,sy))
    gx=max(0,min(W-1,gx)); gy=max(0,min(H-1,gy))

    def snap(x, y, lbl):
        if not grid[x][y]: return x, y
        L(f"⚠️  {lbl} в препятствии, ищу свободную ячейку...")
        for r in range(1,30):
            for dx in range(-r,r+1):
                for dy in range(-r,r+1):
                    nx,ny=x+dx,y+dy
                    if 0<=nx<W and 0<=ny<H and not grid[nx][ny]: return nx,ny
        return None, None

    sx,sy = snap(sx,sy,"Старт")
    if sx is None: return log+["❌ Нет свободных ячеек у старта!"]
    gx,gy = snap(gx,gy,"Цель")
    if gx is None: return log+["❌ Нет свободных ячеек у цели!"]

    L("⚙️  Theta*...")
    path = ThetaStar(grid,W,H).plan(sx,sy,gx,gy)
    if not path:
        blocked = sum(grid[x][y] for x in range(W) for y in range(H))
        return log+[f"❌ Путь не найден! Занято {100*blocked//(W*H)}% сетки",
                    f"   Уменьши Robot Radius (сейчас {props.robot_radius:.2f})"]

    L(f"✅ Путь: {len(path)} точек")

    path_w = [mathutils.Vector((*grid_to_world(gxi,gyi,min_x,min_y,res), 0.5))
               for gxi,gyi in path]

    # Кривая
    old = bpy.data.objects.get("RobotPath")
    if old: bpy.data.objects.remove(old, do_unlink=True)
    cd = bpy.data.curves.new('PathLine','CURVE')
    cd.dimensions='3D'; cd.bevel_depth=0.05
    co = bpy.data.objects.new('RobotPath',cd)
    bpy.context.collection.objects.link(co)
    pm = bpy.data.materials.new("PathRed"); pm.diffuse_color=(1,0,0,1)
    co.data.materials.append(pm)
    sp = cd.splines.new('POLY'); sp.points.add(len(path_w)-1)
    for i,pt in enumerate(path_w): sp.points[i].co=(pt.x,pt.y,pt.z,1)

    # Движение
    step = res
    for wp in path_w:
        d=wp-robot.location; dist=d.length
        if dist<1e-4: continue
        dn=d.normalized()
        for _ in range(max(1,int(dist/step))): robot.location+=dn*step
    robot.location=path_w[-1]

    ep = props.export_path.strip()
    if ep:
        try:    bpy.ops.wm.obj_export(filepath=ep); L(f"💾 {ep}")
        except Exception:
            try: bpy.ops.export_scene.obj(filepath=ep); L(f"💾 (legacy) {ep}")
            except Exception as e: L(f"⚠️  Экспорт: {e}")

    L(f"🏁 Финиш: ({robot.location.x:.2f}, {robot.location.y:.2f})")
    return log


# ══════════════════════════════════════════════════════════════
#  PROPERTIES
# ══════════════════════════════════════════════════════════════

def get_mesh_objects(self, context):
    items = [(o.name, o.name, "") for o in context.scene.objects if o.type=='MESH']
    return items or [("NONE","— нет объектов —","")]

def robot_preset_items(self, context):
    meta = get_scene_meta(context.scene.robot_nav_props.active_scene)
    items = [("RANDOM", "Случайная точка", "")]
    items += [(f"{x},{y}", label, "") for x,y,label in meta.robot_presets]
    return items

def goal_preset_items(self, context):
    meta = get_scene_meta(context.scene.robot_nav_props.active_scene)
    items = [("RANDOM", "Случайная точка", "")]
    items += [(f"{x},{y}", label, "") for x,y,label in meta.goal_presets]
    return items


class RobotNavProperties(bpy.types.PropertyGroup):
    active_scene: bpy.props.EnumProperty(
        name="Сцена", items=scene_enum_items,
    )
    robot_object: bpy.props.EnumProperty(
        name="Объект-робот", items=get_mesh_objects,
    )
    goal_object: bpy.props.EnumProperty(
        name="Объект-цель", items=get_mesh_objects,
    )
    robot_preset: bpy.props.EnumProperty(
        name="Позиция старта", items=robot_preset_items,
    )
    goal_preset: bpy.props.EnumProperty(
        name="Позиция цели", items=goal_preset_items,
    )
    grid_resolution: bpy.props.FloatProperty(
        name="Разрешение сетки", default=0.3, min=0.05, max=2.0, step=5, precision=2,
    )
    robot_radius: bpy.props.FloatProperty(
        name="Радиус робота", default=0.6, min=0.1, max=3.0, step=5, precision=2,
    )
    export_path: bpy.props.StringProperty(
        name="Экспорт .obj", default="", subtype='FILE_PATH',
    )
    log_text:  bpy.props.StringProperty(default="")
    show_help: bpy.props.BoolProperty(name="Справка", default=False)


# ══════════════════════════════════════════════════════════════
#  OPERATORS
# ══════════════════════════════════════════════════════════════

class ROBOTNAV_OT_CreateScene(bpy.types.Operator):
    """Создать выбранную сцену из реестра"""
    bl_idname="robot_nav.create_scene"; bl_label="Создать сцену"
    bl_options={'REGISTER','UNDO'}

    def execute(self, context):
        props = context.scene.robot_nav_props
        meta  = get_scene_meta(props.active_scene)
        if meta.builder is None:
            self.report({'ERROR'}, f"У '{meta.label}' нет builder-функции!")
            return {'CANCELLED'}
        meta.builder()
        if bpy.data.objects.get(meta.robot_name): props.robot_object = meta.robot_name
        if bpy.data.objects.get(meta.goal_name):  props.goal_object  = meta.goal_name
        msg = f"✅ {meta.label} создана"
        props.log_text = msg; self.report({'INFO'}, msg)
        return {'FINISHED'}


def _apply_preset(context, target):
    """
    Перемещает объект (робот или цель) в выбранную / случайную позицию.
    target: 'robot' | 'goal'
    """
    props     = context.scene.robot_nav_props
    meta      = get_scene_meta(props.active_scene)
    is_robot  = target == 'robot'
    preset    = props.robot_preset if is_robot else props.goal_preset
    obj_name  = props.robot_object  if is_robot else props.goal_object
    z         = 0.1 if is_robot else 0.5
    presets   = meta.robot_presets if is_robot else meta.goal_presets

    obj = bpy.data.objects.get(obj_name)
    if not obj: return False, f"❌ Объект '{obj_name}' не найден!"

    if preset == "RANDOM":
        exclude = {props.robot_object, props.goal_object, "Floor", "RobotPath"}
        grid, W, H, bounds = build_nav_grid(props, exclude)
        if grid is None: return False, "❌ Нет объектов для сетки!"

        # Ячейка другого объекта — чтобы не поставить вплотную
        other_name = props.goal_object if is_robot else props.robot_object
        other_obj  = bpy.data.objects.get(other_name)
        excl = None
        if other_obj:
            ox, oy = world_to_grid(other_obj.location.x, other_obj.location.y,
                                   bounds[0], bounds[2], props.grid_resolution)
            excl = (ox, oy)

        wx, wy = random_free_world_pos(grid, W, H, bounds, props.grid_resolution, excl)
        if wx is None: return False, "❌ Нет свободных ячеек на сетке!"
        obj.location = (wx, wy, z)
        return True, f"🎲 {obj_name} → ({wx:.2f}, {wy:.2f})"

    else:
        try:
            x, y = map(float, preset.split(","))
            obj.location = (x, y, z)
            label = next((lb for px,py,lb in presets if abs(px-x)<0.01 and abs(py-y)<0.01), preset)
            return True, f"📍 {obj_name} → {label}"
        except Exception as e:
            return False, f"❌ Ошибка пресета: {e}"


class ROBOTNAV_OT_ApplyRobotPreset(bpy.types.Operator):
    """Применить выбранную позицию для робота"""
    bl_idname="robot_nav.apply_robot_preset"; bl_label="Применить"
    bl_options={'REGISTER','UNDO'}
    def execute(self, context):
        ok, msg = _apply_preset(context, 'robot')
        context.scene.robot_nav_props.log_text = msg
        self.report({'INFO' if ok else 'ERROR'}, msg)
        return {'FINISHED' if ok else 'CANCELLED'}


class ROBOTNAV_OT_ApplyGoalPreset(bpy.types.Operator):
    """Применить выбранную позицию для цели"""
    bl_idname="robot_nav.apply_goal_preset"; bl_label="Применить"
    bl_options={'REGISTER','UNDO'}
    def execute(self, context):
        ok, msg = _apply_preset(context, 'goal')
        context.scene.robot_nav_props.log_text = msg
        self.report({'INFO' if ok else 'ERROR'}, msg)
        return {'FINISHED' if ok else 'CANCELLED'}


class ROBOTNAV_OT_RunSim(bpy.types.Operator):
    """Запустить Theta* и переместить робота"""
    bl_idname="robot_nav.run_simulation"; bl_label="  Запустить симуляцию"
    bl_options={'REGISTER','UNDO'}
    def execute(self, context):
        props = context.scene.robot_nav_props
        if props.robot_object == props.goal_object:
            msg = f"❌ Робот и цель — один объект: '{props.robot_object}'"
            props.log_text = msg; self.report({'ERROR'}, msg)
            return {'CANCELLED'}
        log = run_simulation(props)
        props.log_text = "\n".join(log)
        self.report({'INFO'}, log[-1] if log else "—")
        return {'FINISHED'}


class ROBOTNAV_OT_ClearPath(bpy.types.Operator):
    """Удалить линию пути со сцены"""
    bl_idname="robot_nav.clear_path"; bl_label="Убрать путь"
    bl_options={'REGISTER','UNDO'}
    def execute(self, context):
        obj = bpy.data.objects.get("RobotPath")
        if obj: bpy.data.objects.remove(obj, do_unlink=True)
        msg = "🗑️  RobotPath удалён" if obj else "Путь не найден"
        context.scene.robot_nav_props.log_text = msg
        self.report({'INFO'}, msg)
        return {'FINISHED'}


class ROBOTNAV_OT_ResetRobot(bpy.types.Operator):
    """Вернуть робота на стартовую позицию сцены"""
    bl_idname="robot_nav.reset_robot"; bl_label="Сброс позиции"
    bl_options={'REGISTER','UNDO'}
    def execute(self, context):
        props = context.scene.robot_nav_props
        meta  = get_scene_meta(props.active_scene)
        robot = bpy.data.objects.get(props.robot_object)
        if not robot:
            self.report({'ERROR'}, f"'{props.robot_object}' не найден!"); return {'CANCELLED'}
        x, y = meta.robot_start
        robot.location = (x, y, 0.1)
        msg = f"↩️  {robot.name} → ({x}, {y})"
        props.log_text = msg; self.report({'INFO'}, msg)
        return {'FINISHED'}


# ══════════════════════════════════════════════════════════════
#  PANEL UI
# ══════════════════════════════════════════════════════════════

class ROBOTNAV_PT_MainPanel(bpy.types.Panel):
    bl_label="Robot Navigator"; bl_idname="ROBOTNAV_PT_main"
    bl_space_type='VIEW_3D'; bl_region_type='UI'; bl_category="Robot Nav"

    def draw(self, context):
        layout = self.layout
        props  = context.scene.robot_nav_props
        meta   = get_scene_meta(props.active_scene)

        # ── Сцена ─────────────────────────────────────
        box = layout.box()
        box.label(text="Помещение", icon='WORLD')
        box.prop(props, "active_scene", text="")
        r = box.row(); r.scale_y = 1.4
        r.operator("robot_nav.create_scene", icon='ADD',
                   text=f"Создать: {meta.label}")

        layout.separator()

        # ── Объекты ───────────────────────────────────
        box = layout.box()
        box.label(text="Объекты сцены", icon='OBJECT_DATA')
        box.prop(props, "robot_object", icon='ARMATURE_DATA')
        box.prop(props, "goal_object",  icon='MARKER')
        if props.robot_object == props.goal_object and props.robot_object != "NONE":
            r = box.row(); r.alert = True
            r.label(text="Робот и цель — один объект!", icon='ERROR')

        layout.separator()

        # ── Позиции ───────────────────────────────────
        box = layout.box()
        box.label(text="Стартовая позиция робота", icon='ARMATURE_DATA')
        r = box.row(align=True)
        r.prop(props, "robot_preset", text="")
        r.operator("robot_nav.apply_robot_preset", icon='SNAP_ON', text="Применить")

        box = layout.box()
        box.label(text="Позиция цели", icon='MARKER')
        r = box.row(align=True)
        r.prop(props, "goal_preset", text="")
        r.operator("robot_nav.apply_goal_preset", icon='SNAP_ON', text="Применить")

        layout.separator()

        # ── Параметры ─────────────────────────────────
        box = layout.box()
        box.label(text="Параметры Theta*", icon='SETTINGS')
        box.prop(props, "grid_resolution")
        box.prop(props, "robot_radius")
        if props.grid_resolution < 0.15:
            box.label(text="Маленькое разрешение = медленно!", icon='ERROR')
        if props.robot_radius > 1.5:
            box.label(text="Большой радиус — путь может не найтись", icon='ERROR')

        layout.separator()

        # ── Экспорт ───────────────────────────────────
        box = layout.box()
        box.label(text="Экспорт .obj (опционально)", icon='EXPORT')
        box.prop(props, "export_path", text="")

        layout.separator()

        # ── Запуск ────────────────────────────────────
        r = layout.row(); r.scale_y = 2.2
        r.operator("robot_nav.run_simulation", icon='PLAY')

        layout.separator()

        # ── Сервис ────────────────────────────────────
        r = layout.row(align=True)
        r.operator("robot_nav.clear_path",  icon='TRASH',     text="Убрать путь")
        r.operator("robot_nav.reset_robot", icon='LOOP_BACK', text="Сброс позиции")

        layout.separator()

        # ── Лог ───────────────────────────────────────
        if props.log_text:
            box = layout.box()
            box.label(text="Лог:", icon='INFO')
            for line in props.log_text.split("\n"):
                if line.strip():
                    r = box.row(); r.scale_y = 0.7; r.label(text=line)

        # ── Справка ───────────────────────────────────
        layout.separator()
        box = layout.box()
        box.prop(props, "show_help", icon='QUESTION', text="Справка")
        if props.show_help:
            col = box.column(); col.scale_y = 0.75
            for tip in [
                "1. Выбери сцену → Создать сцену",
                "2. Выбери объект-робот и объект-цель",
                "3. Выбери пресет или 'Случайная точка'",
                "   → нажми Применить",
                "4. Нажми Запустить симуляцию",
                "─────────────────────────────",
                "Добавить новую сцену в реестр:",
                "  1. Напиши _build_<name>()",
                "  2. Создай SceneMeta с пресетами",
                "  3. Добавь в SCENE_REGISTRY",
                "─────────────────────────────",
                "Алгоритм: Theta* (any-angle A*)",
                "Путь: красная кривая RobotPath",
            ]:
                col.label(text=tip)


# ══════════════════════════════════════════════════════════════
#  REGISTRATION
# ══════════════════════════════════════════════════════════════

CLASSES = [
    RobotNavProperties,
    ROBOTNAV_OT_CreateScene,
    ROBOTNAV_OT_ApplyRobotPreset,
    ROBOTNAV_OT_ApplyGoalPreset,
    ROBOTNAV_OT_RunSim,
    ROBOTNAV_OT_ClearPath,
    ROBOTNAV_OT_ResetRobot,
    ROBOTNAV_PT_MainPanel,
]

def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.robot_nav_props = bpy.props.PointerProperty(type=RobotNavProperties)
    print("✅ Robot Navigator зарегистрирован → N-панель → 'Robot Nav'")

def unregister():
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.robot_nav_props

if __name__ == "__main__":
    try: unregister()
    except Exception: pass
    register()