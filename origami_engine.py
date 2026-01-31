import pygame
import math
import json

# --- CONFIGURACIÓN TÉCNICA ---
WIDTH, HEIGHT = 900, 800
FPS = 60
SNAP_ANGLE = 22.5
PAPER_SIZE_PX = 500
# El cuadrado de papel (100x100 unidades virtuales)
PAPER_RECT = pygame.Rect(
    (WIDTH - PAPER_SIZE_PX) // 2,
    (HEIGHT - PAPER_SIZE_PX) // 2,
    PAPER_SIZE_PX,
    PAPER_SIZE_PX,
)
PX_TO_UNITS = PAPER_SIZE_PX / 100.0

COLORS = {
    "bg": (15, 15, 15),
    "paper": (245, 245, 245),
    "grid": (200, 200, 200),
    "node": (30, 30, 30),
    "selected": (255, 200, 0),
    "branch": (0, 120, 255),
    "mountain": (255, 0, 0),
    "valley": (0, 0, 255),
    "circle": (0, 255, 100, 60),
    "error": (255, 50, 50, 150),  # Rojo para desborde o colisión
    "text": (220, 220, 220),
}


class OrigamiEngine:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Origami 22.5 - Tree Theory & Boundary Check")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Consolas", 14)

        self.origin = (WIDTH // 2, HEIGHT // 2)
        self.nodes = [{"pos": self.origin, "radius": 15.0}]
        self.branches = []
        self.creases = []

        self.selected_node_idx = 0
        self.active_radius = 15.0

    def get_snapped_pos(self, mouse_pos, ref_pos):
        dx, dy = mouse_pos[0] - ref_pos[0], mouse_pos[1] - ref_pos[1]
        dist = math.hypot(dx, dy)
        if dist < 1:
            return ref_pos, 0
        angle_deg = math.degrees(math.atan2(dy, dx))
        snapped_deg = round(angle_deg / SNAP_ANGLE) * SNAP_ANGLE
        rad = math.radians(snapped_deg)
        return (
            int(ref_pos[0] + dist * math.cos(rad)),
            int(ref_pos[1] + dist * math.sin(rad)),
        ), snapped_deg

    def check_out_of_bounds(self, node):
        """Verifica si un círculo se sale del cuadrado de papel."""
        r_px = node["radius"] * PX_TO_UNITS
        x, y = node["pos"]
        if (
            x - r_px < PAPER_RECT.left
            or x + r_px > PAPER_RECT.right
            or y - r_px < PAPER_RECT.top
            or y + r_px > PAPER_RECT.bottom
        ):
            return True
        return False

    def generate_creases(self):
        self.creases = []
        for i, node in enumerate(self.nodes):
            angles = []
            for b in self.branches:
                if i in b:
                    other = b[1] if b[0] == i else b[0]
                    angles.append(
                        math.atan2(
                            self.nodes[other]["pos"][1] - node["pos"][1],
                            self.nodes[other]["pos"][0] - node["pos"][0],
                        )
                    )
            if len(angles) >= 2:
                angles.sort()
                for j in range(len(angles)):
                    a1, a2 = angles[j], angles[(j + 1) % len(angles)]
                    diff = (a2 - a1) % (2 * math.pi)
                    bisect = a1 + diff / 2
                    length = 800
                    end = (
                        node["pos"][0] + length * math.cos(bisect),
                        node["pos"][1] + length * math.sin(bisect),
                    )
                    self.creases.append(
                        {"start": node["pos"], "end": end, "type": "mountain"}
                    )

    def run(self):
        running = True
        while running:
            self.screen.fill(COLORS["bg"])
            pygame.draw.rect(self.screen, COLORS["paper"], PAPER_RECT)

            mouse_pos = pygame.mouse.get_pos()
            ref_pos = self.nodes[self.selected_node_idx]["pos"]
            snapped_pos, _ = self.get_snapped_pos(mouse_pos, ref_pos)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_g:
                        self.generate_creases()
                    if event.key == pygame.K_z:
                        if len(self.nodes) > 1:
                            self.branches = [
                                b
                                for b in self.branches
                                if (len(self.nodes) - 1) not in b
                            ]
                            self.nodes.pop()
                            self.selected_node_idx = 0

                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        clicked = -1
                        for i, n in enumerate(self.nodes):
                            if (
                                math.hypot(
                                    mouse_pos[0] - n["pos"][0],
                                    mouse_pos[1] - n["pos"][1],
                                )
                                < 12
                            ):
                                clicked = i
                                break
                        if clicked != -1:
                            self.selected_node_idx = clicked
                        else:
                            self.nodes.append(
                                {"pos": snapped_pos, "radius": self.active_radius}
                            )
                            self.branches.append(
                                (self.selected_node_idx, len(self.nodes) - 1)
                            )
                            self.selected_node_idx = len(self.nodes) - 1
                    if event.button == 4:
                        self.active_radius += 2.0
                    if event.button == 5:
                        self.active_radius = max(0, self.active_radius - 2.0)

            # --- DIBUJO CON CLIPPING ---
            self.screen.set_clip(PAPER_RECT)
            for c in self.creases:
                pygame.draw.line(
                    self.screen, COLORS[c["type"]], c["start"], c["end"], 1
                )
            for b in self.branches:
                pygame.draw.line(
                    self.screen,
                    COLORS["branch"],
                    self.nodes[b[0]]["pos"],
                    self.nodes[b[1]]["pos"],
                    2,
                )
            for i, node in enumerate(self.nodes):
                r_px = int(node["radius"] * PX_TO_UNITS)
                if node["radius"] > 0:
                    s = pygame.Surface((r_px * 2, r_px * 2), pygame.SRCALPHA)
                    # Validación de bordes para el color
                    is_error = self.check_out_of_bounds(node)
                    color = COLORS["error"] if is_error else COLORS["circle"]
                    pygame.draw.circle(s, color, (r_px, r_px), r_px)
                    self.screen.blit(s, (node["pos"][0] - r_px, node["pos"][1] - r_px))
                n_col = (
                    COLORS["selected"]
                    if i == self.selected_node_idx
                    else COLORS["node"]
                )
                pygame.draw.circle(self.screen, n_col, node["pos"], 5)
            self.screen.set_clip(None)

            # UI
            pygame.draw.line(self.screen, (150, 150, 150), ref_pos, snapped_pos, 1)
            info = [
                f"Radio: {self.active_radius}u",
                "Rojo = Error (Fuera de papel)",
                "G: Bisectrices | Z: Deshacer",
            ]
            for i, txt in enumerate(info):
                self.screen.blit(
                    self.font.render(txt, True, COLORS["text"]), (15, 15 + i * 20)
                )

            pygame.display.flip()
            self.clock.tick(FPS)
        pygame.quit()


if __name__ == "__main__":
    OrigamiEngine().run()
