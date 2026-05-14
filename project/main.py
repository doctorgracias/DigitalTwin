import bpy
import mathutils
import math
import heapq


# ─────────────────────────────────────────
#  УТИЛИТЫ AABB — вместо raycast
# ─────────────────────────────────────────

def get_obstacle_boxes(exclude_names):
    """
    Возвращает список AABB препятствий как (min_x, max_x, min_y, max_y).
    Работает 100% надёжно — не зависит от depsgraph.
    """
    boxes = []
    for obj in bpy.context.scene.objects:
        if obj.name in exclude_names:
            continue
        if obj.type != 'MESH':
            continue
        # Мировые координаты 8 углов bbox
        corners = [obj.matrix_world @ mathutils.Vector(c) for c in obj.bound_box]
        xs = [c.x for c in corners]
        ys = [c.y for c in corners]
        zs = [c.z for c in corners]
        # Игнорируем плоские объекты (пол/потолок) по Z
        if (max(zs) - min(zs)) < 0.05:
            continue
        boxes.append((min(xs), max(xs), min(ys), max(ys)))
    return boxes


def build_grid_from_boxes(obstacle_boxes, bounds, resolution, robot_radius=0.5):
    """
    Строит бинарную сетку из AABB-боксов.
    robot_radius: отступ вокруг препятствий (inflate for clearance).
    """
    min_x, max_x, min_y, max_y = bounds

    width  = int(math.ceil((max_x - min_x) / resolution))
    height = int(math.ceil((max_y - min_y) / resolution))
    grid   = [[False] * height for _ in range(width)]

    r = robot_radius  # inflate

    for (ox1, ox2, oy1, oy2) in obstacle_boxes:
        # Индексы ячеек, которые перекрываются с увеличенным препятствием
        ix1 = max(0, int((ox1 - r - min_x) / resolution))
        ix2 = min(width  - 1, int((ox2 + r - min_x) / resolution))
        iy1 = max(0, int((oy1 - r - min_y) / resolution))
        iy2 = min(height - 1, int((oy2 + r - min_y) / resolution))
        for ix in range(ix1, ix2 + 1):
            for iy in range(iy1, iy2 + 1):
                grid[ix][iy] = True

    return grid, width, height


# ─────────────────────────────────────────
#  THETA* — Any-angle pathfinding
# ─────────────────────────────────────────

class ThetaStar:
    """
    Theta* — оптимизированный A* с проверкой прямой видимости.
    Строит плавные маршруты без зигзагов по сетке.
    Сложность: O(N log N), N = кол-во проходимых ячеек.
    """

    def __init__(self, grid, width, height, resolution):
        self.grid       = grid
        self.width      = width
        self.height     = height
        self.resolution = resolution

    # ── эвристика: октилинейное расстояние (точнее Манхэттена) ──
    @staticmethod
    def heuristic(ax, ay, bx, by):
        dx, dy = abs(ax - bx), abs(ay - by)
        return (dx + dy) + (1.4142 - 2) * min(dx, dy)

    # ── проверка видимости по алгоритму Брезенхема ──
    def line_of_sight(self, x0, y0, x1, y1):
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        sx     = 1 if x0 < x1 else -1
        sy     = 1 if y0 < y1 else -1
        err    = dx - dy

        cx, cy = x0, y0
        while True:
            if not (0 <= cx < self.width and 0 <= cy < self.height):
                return False
            if self.grid[cx][cy]:
                return False
            if cx == x1 and cy == y1:
                return True
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                cx  += sx
            if e2 < dx:
                err += dx
                cy  += sy

    def plan(self, sx, sy, gx, gy):
        if self.grid[sx][sy] or self.grid[gx][gy]:
            print(f"❌ Старт или цель в препятствии! start={self.grid[sx][sy]} goal={self.grid[gx][gy]}")
            return None

        g_score = {(sx, sy): 0.0}
        parent  = {(sx, sy): (sx, sy)}

        open_heap = []
        heapq.heappush(open_heap, (self.heuristic(sx, sy, gx, gy), sx, sy))
        closed = set()

        while open_heap:
            _, cx, cy = heapq.heappop(open_heap)

            if (cx, cy) in closed:
                continue
            closed.add((cx, cy))

            if (cx, cy) == (gx, gy):
                return self._reconstruct(parent, gx, gy)

            px, py = parent[(cx, cy)]

            for nx, ny in self._neighbors(cx, cy):
                if (nx, ny) in closed:
                    continue

                # ── Theta*: пробуем связать с родителем напрямую ──
                if self.line_of_sight(px, py, nx, ny):
                    dx = nx - px
                    dy = ny - py
                    ng = g_score[(px, py)] + math.hypot(dx, dy)
                    if ng < g_score.get((nx, ny), float('inf')):
                        g_score[(nx, ny)] = ng
                        parent[(nx, ny)]  = (px, py)
                        f = ng + self.heuristic(nx, ny, gx, gy)
                        heapq.heappush(open_heap, (f, nx, ny))
                else:
                    # Стандартный шаг A*
                    step = 1.4142 if abs(nx - cx) + abs(ny - cy) == 2 else 1.0
                    ng   = g_score[(cx, cy)] + step
                    if ng < g_score.get((nx, ny), float('inf')):
                        g_score[(nx, ny)] = ng
                        parent[(nx, ny)]  = (cx, cy)
                        f = ng + self.heuristic(nx, ny, gx, gy)
                        heapq.heappush(open_heap, (f, nx, ny))

        return None

    def _neighbors(self, x, y):
        result = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                nx, ny = x + dx, y + dy
                if 0 <= nx < self.width and 0 <= ny < self.height:
                    if not self.grid[nx][ny]:
                        result.append((nx, ny))
        return result

    def _reconstruct(self, parent, gx, gy):
        path = []
        node = (gx, gy)
        while True:
            path.append(node)
            prev = parent[node]
            if prev == node:
                break
            node = prev
        return list(reversed(path))


# ─────────────────────────────────────────
#  КОНВЕРТАЦИЯ КООРДИНАТ
# ─────────────────────────────────────────

def world_to_grid(wx, wy, min_x, min_y, res):
    return int((wx - min_x) / res), int((wy - min_y) / res)

def grid_to_world(gx, gy, min_x, min_y, res):
    return min_x + gx * res + res / 2, min_y + gy * res + res / 2


# ─────────────────────────────────────────
#  СЦЕНА
# ─────────────────────────────────────────

def create_office_clear():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

    WIDTH, LENGTH, HEIGHT = 15, 28, 10

    def get_mat(name, color):
        m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
        m.diffuse_color = color
        return m

    floor_mat = get_mat("FloorTile", (0.2, 0.2, 0.2, 1))
    wall_mat  = get_mat("WallMat",   (0.7, 0.7, 0.7, 1))
    table_mat = get_mat("TableMat",  (0.05, 0.05, 0.05, 1))

    def add_wall(name, loc, scale):
        bpy.ops.mesh.primitive_cube_add(location=loc)
        w = bpy.context.active_object
        w.name = name
        w.scale = scale
        bpy.ops.object.transform_apply(scale=True)
        w.data.materials.append(wall_mat)

    # Пол
    bpy.ops.mesh.primitive_plane_add(size=1, location=(WIDTH/2, LENGTH/2, 0))
    floor = bpy.context.active_object
    floor.name = "Floor"
    floor.scale = (WIDTH, LENGTH, 1)
    bpy.ops.object.transform_apply(scale=True)
    floor.data.materials.append(floor_mat)

    # Стены
    add_wall("Wall_Back",  (WIDTH/2, 0,       HEIGHT/2), (WIDTH/2, 0.1, HEIGHT/2))
    add_wall("Wall_Front", (WIDTH/2, LENGTH,   HEIGHT/2), (WIDTH/2, 0.1, HEIGHT/2))
    add_wall("Wall_Right", (WIDTH,   LENGTH/2, HEIGHT/2), (0.1, LENGTH/2, HEIGHT/2))
    add_wall("Wall_Left",  (0,       LENGTH/2, HEIGHT/2), (0.1, LENGTH/2, HEIGHT/2))

    def add_table(x, y, sx, sy):
        bpy.ops.mesh.primitive_cube_add(location=(x, y, 0.5))
        t = bpy.context.active_object
        t.name = "OfficeTable"
        t.scale = (sx/2, sy/2, 0.5)
        bpy.ops.object.transform_apply(scale=True)
        t.data.materials.append(table_mat)

    add_table(4,    26,   7,   2)
    add_table(13,   26,   3,   2)
    add_table(1.5,  18,   2.5, 8)
    add_table(13,   18,   2.5, 6)
    add_table(10,   8,    8,   1.5)
    add_table(4.5,  5,    1.5, 5)
    add_table(10,   2,    8,   1.5)

    # Робот
    bpy.ops.mesh.primitive_cylinder_add(radius=0.4, depth=0.2, location=(2, 2, 0.1))
    robot = bpy.context.active_object
    robot.name = "Robot_Sim"

    # Цель
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.4, location=(13, 22, 0.5))
    goal = bpy.context.active_object
    goal.name = "Goal_Marker"

    bpy.context.view_layer.update()
    print("✅ Сцена создана.")


# ─────────────────────────────────────────
#  СИМУЛЯЦИЯ
# ─────────────────────────────────────────

EXPORT_PATH    = "C:/Users/rulko/Desktop/project/Untitled2.obj"
GRID_RES       = 0.3   # Увеличен для скорости (был 0.1)
ROBOT_RADIUS   = 0.6   # Зазор вокруг препятствий
STEP_SIZE      = 0.3
BOUNDS         = (0, 15, 0, 28)  # (min_x, max_x, min_y, max_y)

EXCLUDE = {"Floor", "Robot_Sim", "RobotPath", "Goal_Marker"}


def run_simulation():
    # ── Проверка наличия объектов ──
    robot = bpy.data.objects.get("Robot_Sim")
    if not robot:
        print("❌ Robot_Sim не найден в сцене!")
        print("   Объекты в сцене:", [o.name for o in bpy.context.scene.objects])
        return

    goal_marker = bpy.data.objects.get("Goal_Marker")
    if not goal_marker:
        print("❌ Goal_Marker не найден в сцене!")
        print("   Объекты в сцене:", [o.name for o in bpy.context.scene.objects])
        return

    start_pos = robot.location.copy()
    goal_pos  = goal_marker.location.copy()

    print(f"📍 Robot_Sim:   ({start_pos.x:.2f}, {start_pos.y:.2f}, {start_pos.z:.2f})")
    print(f"📍 Goal_Marker: ({goal_pos.x:.2f}, {goal_pos.y:.2f}, {goal_pos.z:.2f})")

    # ── Автоматический расчёт BOUNDS по реальным объектам сцены ──
    # Не хардкодим (0,15,0,28) — берём из фактических позиций
    all_x, all_y = [], []
    for obj in bpy.context.scene.objects:
        if obj.type != 'MESH':
            continue
        corners = [obj.matrix_world @ mathutils.Vector(c) for c in obj.bound_box]
        all_x.extend(c.x for c in corners)
        all_y.extend(c.y for c in corners)

    if not all_x:
        print("❌ Нет mesh-объектов для расчёта границ!")
        return

    margin = 1.0
    min_x = math.floor(min(all_x)) - margin
    max_x = math.ceil(max(all_x))  + margin
    min_y = math.floor(min(all_y)) - margin
    max_y = math.ceil(max(all_y))  + margin
    print(f"📐 Автоматические BOUNDS: x=[{min_x:.1f}, {max_x:.1f}], y=[{min_y:.1f}, {max_y:.1f}]")

    # ── Строим сетку ──
    obstacle_boxes = get_obstacle_boxes(EXCLUDE)
    print(f"🧱 Найдено препятствий (AABB): {len(obstacle_boxes)}")

    grid, W, H = build_grid_from_boxes(
        obstacle_boxes,
        (min_x, max_x, min_y, max_y),
        GRID_RES,
        ROBOT_RADIUS
    )
    print(f"🗺️  Сетка: {W}×{H}")

    # ── Конвертация координат ──
    sx, sy = world_to_grid(start_pos.x, start_pos.y, min_x, min_y, GRID_RES)
    gx, gy = world_to_grid(goal_pos.x,  goal_pos.y,  min_x, min_y, GRID_RES)

    sx = max(0, min(W-1, sx))
    sy = max(0, min(H-1, sy))
    gx = max(0, min(W-1, gx))
    gy = max(0, min(H-1, gy))

    print(f"⭐ Старт: сетка ({sx},{sy}), в препятствии: {grid[sx][sy]}")
    print(f"🎯 Цель:  сетка ({gx},{gy}), в препятствии: {grid[gx][gy]}")

    # ── Если старт/цель в препятствии — ищем ближайшую свободную ячейку ──
    def find_free_near(x, y):
        for r in range(1, 20):
            for dx in range(-r, r+1):
                for dy in range(-r, r+1):
                    nx, ny = x+dx, y+dy
                    if 0 <= nx < W and 0 <= ny < H and not grid[nx][ny]:
                        return nx, ny
        return None, None

    if grid[sx][sy]:
        print("⚠️  Старт в препятствии — ищу ближайшую свободную ячейку...")
        sx, sy = find_free_near(sx, sy)
        if sx is None:
            print("❌ Нет свободной ячейки рядом со стартом!")
            return
        wx, wy = grid_to_world(sx, sy, min_x, min_y, GRID_RES)
        print(f"   Скорректированный старт: сетка ({sx},{sy}), мир ({wx:.2f},{wy:.2f})")

    if grid[gx][gy]:
        print("⚠️  Цель в препятствии — ищу ближайшую свободную ячейку...")
        gx, gy = find_free_near(gx, gy)
        if gx is None:
            print("❌ Нет свободной ячейки рядом с целью!")
            return
        wx, wy = grid_to_world(gx, gy, min_x, min_y, GRID_RES)
        print(f"   Скорректированная цель: сетка ({gx},{gy}), мир ({wx:.2f},{wy:.2f})")

    # ── Theta* ──
    planner   = ThetaStar(grid, W, H, GRID_RES)
    path_grid = planner.plan(sx, sy, gx, gy)

    if not path_grid:
        print("❌ Путь не найден! Проверь что старт и цель не замурованы.")
        # Дополнительная диагностика: считаем процент занятых ячеек
        blocked = sum(grid[x][y] for x in range(W) for y in range(H))
        total   = W * H
        print(f"   Заблокировано ячеек: {blocked}/{total} ({100*blocked//total}%)")
        print(f"   Если >70% — уменьши ROBOT_RADIUS (сейчас {ROBOT_RADIUS})")
        return

    print(f"✅ Путь найден: {len(path_grid)} точек")

    # ── Конвертация в мировые координаты ──
    path_world = []
    for gxi, gyi in path_grid:
        wx, wy = grid_to_world(gxi, gyi, min_x, min_y, GRID_RES)
        path_world.append(mathutils.Vector((wx, wy, 0.5)))

    # ── Линия пути ──
    old_path = bpy.data.objects.get("RobotPath")
    if old_path:
        bpy.data.objects.remove(old_path, do_unlink=True)

    curve_data = bpy.data.curves.new('PathLine', type='CURVE')
    curve_data.dimensions = '3D'
    curve_data.bevel_depth = 0.05
    curve_obj = bpy.data.objects.new('RobotPath', curve_data)
    bpy.context.collection.objects.link(curve_obj)

    mat = bpy.data.materials.new("PathRed")
    mat.diffuse_color = (1, 0, 0, 1)
    curve_obj.data.materials.append(mat)

    spline = curve_data.splines.new('POLY')
    spline.points.add(len(path_world) - 1)
    for i, pt in enumerate(path_world):
        spline.points[i].co = (pt.x, pt.y, pt.z, 1)

    # ── Движение робота ──
    print("🚀 Движение робота...")
    for idx, waypoint in enumerate(path_world):
        delta = waypoint - robot.location
        dist  = delta.length
        if dist < 1e-4:
            continue
        direction = delta.normalized()
        steps = max(1, int(dist / STEP_SIZE))
        for _ in range(steps):
            robot.location += direction * STEP_SIZE
        if idx % 20 == 0:
            print(f"   [{idx}/{len(path_world)}] ({robot.location.x:.1f}, {robot.location.y:.1f})")

    robot.location = path_world[-1]

    try:
        bpy.ops.wm.obj_export(filepath=EXPORT_PATH)
    except AttributeError:
        bpy.ops.export_scene.obj(filepath=EXPORT_PATH)

    print(f"\n✨ Готово! Позиция: ({robot.location.x:.1f}, {robot.location.y:.1f})")


if __name__ == "__main__":
    # create_office_clear()  # можно закомментировать
    bpy.context.view_layer.update()
    run_simulation()