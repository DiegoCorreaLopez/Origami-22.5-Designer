import pygame
import math
import copy

# --- PARÁMETROS DE INGENIERÍA ---
WIDTH, HEIGHT = 1150, 850
FPS = 60
PAPER_SIZE = 580
PAPER_RECT = pygame.Rect(350, (HEIGHT - PAPER_SIZE) // 2, PAPER_SIZE, PAPER_SIZE)
SNAP_ANGLE = 22.5

COLORS = {
    "bg": (12, 12, 12),
    "paper": (255, 255, 255),
    "grid": (220, 220, 220, 35),
    "mountain": (220, 20, 60),
    "valley": (30, 100, 255),
    "tree": (0, 150, 255, 120),
    "node": (60, 60, 60),
    "selected": (255, 165, 0),
    "collision": (255, 50, 50, 100),
    "ok_circle": (0, 255, 150, 45),
    "ui_bg": (25, 25, 25),
    "text": (210, 210, 210),
    "preview": (0, 200, 100),
}


class OrigamiEngine:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Origami Engineering Pro - Full Feature Suite")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Consolas", 14, bold=True)

        self.grid_options = [0, 2, 4, 8, 16, 32]
        self.grid_idx = 3
        self.symmetry = True

        self.nodes = [{"pos": list(PAPER_RECT.center), "radius": 25.0, "parent": -1}]
        self.history = []
        self.selected_node = 0
        self.creases = []

    def save_state(self):
        self.history.append(copy.deepcopy(self.nodes))
        if len(self.history) > 60:
            self.history.pop(0)

    def optimize_radii_only(self):
        """Ajusta radios para tangencia SIN mover los vértices."""
        self.save_state()
        for i in range(len(self.nodes)):
            n1, new_r = self.nodes[i], 60.0
            for j, n2 in enumerate(self.nodes):
                if i == j:
                    continue
                dist_u = math.hypot(
                    n1["pos"][0] - n2["pos"][0], n1["pos"][1] - n2["pos"][1]
                ) / (PAPER_SIZE / 100)
                limit_r = dist_u - n2["radius"]
                if limit_r < new_r:
                    new_r = limit_r
            n1["radius"] = max(1.0, new_r)

    def get_hybrid_pos(self, mouse_pos):
        ref_pos = self.nodes[self.selected_node]["pos"]
        res = self.grid_options[self.grid_idx]
        if res > 0:
            step = PAPER_SIZE / res
            gx = PAPER_RECT.left + round((mouse_pos[0] - PAPER_RECT.left) / step) * step
            gy = PAPER_RECT.top + round((mouse_pos[1] - PAPER_RECT.top) / step) * step
            if math.hypot(mouse_pos[0] - gx, mouse_pos[1] - gy) < 18:
                return [int(gx), int(gy)], "REJILLA", 0
        dx, dy = mouse_pos[0] - ref_pos[0], mouse_pos[1] - ref_pos[1]
        dist = math.hypot(dx, dy)
        if dist < 1:
            return list(ref_pos), "CENTRO", 0
        ang = round(math.degrees(math.atan2(dy, dx)) / SNAP_ANGLE) * SNAP_ANGLE
        rad = math.radians(ang)
        return (
            [ref_pos[0] + dist * math.cos(rad), ref_pos[1] + dist * math.sin(rad)],
            "ÁNGULO",
            ang,
        )

    def solve_cp(self):
        self.creases = []
        c_nodes = copy.deepcopy(self.nodes)
        if self.symmetry:
            n_orig, cx = len(self.nodes), PAPER_RECT.centerx
            for i in range(n_orig):
                m_pos = [cx * 2 - self.nodes[i]["pos"][0], self.nodes[i]["pos"][1]]
                if abs(m_pos[0] - self.nodes[i]["pos"][0]) > 2:
                    p_mirr = (
                        self.nodes[i]["parent"] + n_orig
                        if self.nodes[i]["parent"] != -1
                        else -1
                    )
                    c_nodes.append(
                        {
                            "pos": m_pos,
                            "radius": self.nodes[i]["radius"],
                            "parent": p_mirr,
                        }
                    )

        for i, n in enumerate(c_nodes):
            if n["parent"] != -1 and n["parent"] < len(c_nodes):
                self.creases.append(
                    {"p1": n["pos"], "p2": c_nodes[n["parent"]]["pos"], "type": "M"}
                )

        rays = []
        for i, n in enumerate(c_nodes):
            conns = [
                nb["pos"]
                for j, nb in enumerate(c_nodes)
                if nb["parent"] == i or n["parent"] == j
            ]
            if len(conns) >= 2:
                angs = sorted(
                    [math.atan2(p[1] - n["pos"][1], p[0] - n["pos"][0]) for p in conns]
                )
                for k in range(len(angs)):
                    diff = (angs[(k + 1) % len(angs)] - angs[k]) % (2 * math.pi)
                    rays.append(
                        {"origin": n["pos"], "angle": angs[k] + diff / 2, "id": i}
                    )

        for r in rays:
            p1, p2 = r["origin"], [
                r["origin"][0] + 1500 * math.cos(r["angle"]),
                r["origin"][1] + 1500 * math.sin(r["angle"]),
            ]
            closest, min_d = p2, 1500
            for r2 in rays:
                if r["id"] == r2["id"]:
                    continue
                denom = (math.sin(r2["angle"])) * (p2[0] - p1[0]) - (
                    math.cos(r2["angle"])
                ) * (p2[1] - p1[1])
                if abs(denom) > 0.001:
                    ua = (
                        (math.cos(r2["angle"])) * (p1[1] - r2["origin"][1])
                        - (math.sin(r2["angle"])) * (p1[0] - r2["origin"][0])
                    ) / denom
                    if 0 < ua < 1:
                        d = math.hypot(ua * (p2[0] - p1[0]), ua * (p2[1] - p1[1]))
                        if d < min_d and d > 2:
                            min_d, closest = d, [
                                p1[0] + ua * (p2[0] - p1[0]),
                                p1[1] + ua * (p2[1] - p1[1]),
                            ]
            self.creases.append({"p1": p1, "p2": closest, "type": "V"})

    def draw_menu(self, mode, val):
        pygame.draw.rect(self.screen, COLORS["ui_bg"], (0, 0, 320, HEIGHT))
        y, grid_st = 40, (
            f"{self.grid_options[self.grid_idx]}x"
            if self.grid_options[self.grid_idx] > 0
            else "OFF"
        )
        ui = [
            "--- ORIGAMI ENGINEERING ---",
            "G: Generar CP",
            "C: Limpiar CP (Recuperado!)",
            "R: Optimizar Radios",
            "O: Optimizar Puntos",
            "S: Simetría Axial",
            "UP/DN: Grilla",
            "L-CLICK: Crear Nodo",
            "R-CLICK: Borrar",
            "",
            "--- DATOS ---",
            f"Snap: {mode} ({val})",
            f"Grilla: {grid_st}",
            f"Radio Selec: {self.nodes[self.selected_node]['radius']:.1f}u",
        ]
        for line in ui:
            color = COLORS["selected"] if "---" in line else COLORS["text"]
            self.screen.blit(self.font.render(line, True, color), (30, y))
            y += 26

    def run(self):
        while True:
            self.screen.fill(COLORS["bg"])
            pygame.draw.rect(self.screen, COLORS["paper"], PAPER_RECT)
            mouse_raw = pygame.mouse.get_pos()
            target_pos, mode, val = self.get_hybrid_pos(mouse_raw)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:
                        self.optimize_radii_only()
                    if event.key == pygame.K_o:
                        for _ in range(40):
                            for i, n1 in enumerate(self.nodes):
                                for j, n2 in enumerate(self.nodes):
                                    if i == j:
                                        continue
                                    d = math.hypot(
                                        n1["pos"][0] - n2["pos"][0],
                                        n1["pos"][1] - n2["pos"][1],
                                    )
                                    t = (n1["radius"] + n2["radius"]) * (
                                        PAPER_SIZE / 100
                                    )
                                    if d < t:
                                        ov = (t - d) * 0.15
                                        a = math.atan2(
                                            n2["pos"][1] - n1["pos"][1],
                                            n2["pos"][0] - n1["pos"][0],
                                        )
                                        if i != 0:
                                            n1["pos"][0] -= math.cos(a) * ov
                                            n1["pos"][1] -= math.sin(a) * ov
                                        n2["pos"][0] += math.cos(a) * ov
                                        n2["pos"][1] += math.sin(a) * ov
                    if event.key == pygame.K_g:
                        self.solve_cp()
                    if event.key == pygame.K_c:
                        self.creases = []
                    if event.key == pygame.K_s:
                        self.symmetry = not self.symmetry
                    if event.key == pygame.K_UP:
                        self.grid_idx = min(
                            len(self.grid_options) - 1, self.grid_idx + 1
                        )
                    if event.key == pygame.K_DOWN:
                        self.grid_idx = max(0, self.grid_idx - 1)
                    if event.key == pygame.K_z and self.history:
                        self.nodes = self.history.pop()

                if event.type == pygame.MOUSEBUTTONDOWN:
                    self.save_state()
                    clicked = next(
                        (
                            i
                            for i, n in enumerate(self.nodes)
                            if math.hypot(
                                mouse_raw[0] - n["pos"][0], mouse_raw[1] - n["pos"][1]
                            )
                            < 15
                        ),
                        -1,
                    )
                    if event.button == 1:
                        if clicked != -1:
                            self.selected_node = clicked
                        else:
                            self.nodes.append(
                                {
                                    "pos": target_pos,
                                    "radius": 20.0,
                                    "parent": self.selected_node,
                                }
                            )
                            self.selected_node = len(self.nodes) - 1
                    if event.button == 3 and clicked != -1:
                        if len(self.nodes) > 1:
                            self.nodes.pop(clicked)
                            self.selected_node = 0
                    if event.button == 4:
                        self.nodes[self.selected_node]["radius"] += 1.0
                    if event.button == 5:
                        self.nodes[self.selected_node]["radius"] = max(
                            1.0, self.nodes[self.selected_node]["radius"] - 1.0
                        )

            self.screen.set_clip(PAPER_RECT)
            if self.grid_options[self.grid_idx] > 0:
                step = PAPER_SIZE / self.grid_options[self.grid_idx]
                for i in range(self.grid_options[self.grid_idx] + 1):
                    pygame.draw.line(
                        self.screen,
                        COLORS["grid"],
                        (PAPER_RECT.left + i * step, PAPER_RECT.top),
                        (PAPER_RECT.left + i * step, PAPER_RECT.bottom),
                        1,
                    )
                    pygame.draw.line(
                        self.screen,
                        COLORS["grid"],
                        (PAPER_RECT.left, PAPER_RECT.top + i * step),
                        (PAPER_RECT.right, PAPER_RECT.top + i * step),
                        1,
                    )

            pygame.draw.line(
                self.screen,
                COLORS["preview"],
                self.nodes[self.selected_node]["pos"],
                target_pos,
                1,
            )
            for c in self.creases:
                pygame.draw.line(
                    self.screen,
                    COLORS["mountain"] if c["type"] == "M" else COLORS["valley"],
                    c["p1"],
                    c["p2"],
                    2 if c["type"] == "M" else 1,
                )

            for i, n in enumerate(self.nodes):
                r_px = int(n["radius"] * (PAPER_SIZE / 100))
                coll = any(
                    math.hypot(n["pos"][0] - o["pos"][0], n["pos"][1] - o["pos"][1])
                    < (n["radius"] + o["radius"]) * (PAPER_SIZE / 100) - 0.5
                    for j, o in enumerate(self.nodes)
                    if i != j
                )
                s = pygame.Surface((r_px * 2, r_px * 2), pygame.SRCALPHA)
                pygame.draw.circle(
                    s,
                    COLORS["collision"] if coll else COLORS["ok_circle"],
                    (r_px, r_px),
                    r_px,
                )
                self.screen.blit(s, (n["pos"][0] - r_px, n["pos"][1] - r_px))
                if n["parent"] != -1:
                    pygame.draw.line(
                        self.screen,
                        COLORS["tree"],
                        n["pos"],
                        self.nodes[n["parent"]]["pos"],
                        1,
                    )
                pygame.draw.circle(
                    self.screen,
                    COLORS["selected"] if i == self.selected_node else COLORS["node"],
                    n["pos"],
                    6,
                )
                if self.symmetry:
                    m_pos = [PAPER_RECT.centerx * 2 - n["pos"][0], n["pos"][1]]
                    pygame.draw.circle(self.screen, (100, 100, 100), m_pos, 4, 1)

            self.screen.set_clip(None)
            self.draw_menu(mode, val)
            pygame.display.flip()
            self.clock.tick(FPS)


if __name__ == "__main__":
    OrigamiEngine().run()
