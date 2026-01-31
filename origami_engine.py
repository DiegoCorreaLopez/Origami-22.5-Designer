import pygame
import math

# --- CONFIGURACIÓN Y CONSTANTES ---
WIDTH, HEIGHT = 900, 800
FPS = 60
SNAP_ANGLE = 22.5
PAPER_UNITS = 100.0
PX_TO_UNITS = WIDTH / PAPER_UNITS

COLORS = {
    "bg": (25, 25, 25),
    "grid": (50, 50, 50),
    "node": (200, 200, 200),
    "selected": (255, 255, 0),
    "branch": (0, 150, 255),
    "river": (255, 100, 0),
    "crease": (255, 0, 255, 180),  # Magenta para pliegues
    "circle": (0, 255, 100, 40),
    "text": (220, 220, 220),
}


class OrigamiEngine:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Origami 22.5 - Fase 3: Gestión Axial y Ríos")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Consolas", 14)

        self.origin = (WIDTH // 2, HEIGHT // 2)
        self.nodes = [{"pos": self.origin, "radius": 0}]
        self.branches = []
        self.bisectors = []

        self.selected_node_idx = 0
        self.active_radius = 10.0

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

    def is_leaf(self, node_idx):
        """Determina si un nodo es una punta (hoja del árbol)."""
        count = sum(1 for b in self.branches if node_idx in b)
        return count <= 1

    def undo(self):
        """Elimina el último nodo y su rama asociada."""
        if len(self.nodes) > 1:
            last_idx = len(self.nodes) - 1
            # Eliminar ramas conectadas al último nodo
            self.branches = [b for b in self.branches if last_idx not in b]
            self.nodes.pop()
            # Resetear selección al origen si el nodo seleccionado ya no existe
            if self.selected_node_idx >= len(self.nodes):
                self.selected_node_idx = 0
            # Limpiar bisectrices para forzar regeneración
            self.bisectors = []

    def generate_bisectors(self):
        """Calcula las bisectrices. Si el radio es 0, usa una longitud fija."""
        self.bisectors = []
        for i, node in enumerate(self.nodes):
            connected_angles = []
            for b in self.branches:
                if i in b:
                    other_idx = b[1] if b[0] == i else b[0]
                    dx = self.nodes[other_idx]["pos"][0] - self.nodes[i]["pos"][0]
                    dy = self.nodes[other_idx]["pos"][1] - self.nodes[i]["pos"][1]
                    connected_angles.append(math.atan2(dy, dx))

            if len(connected_angles) >= 2:
                connected_angles.sort()
                for j in range(len(connected_angles)):
                    a1 = connected_angles[j]
                    a2 = connected_angles[(j + 1) % len(connected_angles)]
                    diff = (a2 - a1) % (2 * math.pi)
                    bisect_angle = a1 + diff / 2

                    # Longitud: Si es punta usa el radio, si es interno usa 80px
                    if node["radius"] > 0:
                        length = node["radius"] * (PX_TO_UNITS / 5)
                    else:
                        length = 80

                    end_x = node["pos"][0] + length * math.cos(bisect_angle)
                    end_y = node["pos"][1] + length * math.sin(bisect_angle)
                    self.bisectors.append((node["pos"], (int(end_x), int(end_y))))

    def run(self):
        running = True
        while running:
            self.screen.fill(COLORS["bg"])
            mouse_pos = pygame.mouse.get_pos()
            ref_node_pos = self.nodes[self.selected_node_idx]["pos"]
            snapped_pos, current_angle = self.get_snapped_pos(mouse_pos, ref_node_pos)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_g:
                        self.generate_bisectors()
                    if event.key == pygame.K_z:  # Deshacer
                        self.undo()

                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # Seleccionar o Crear
                        clicked_idx = -1
                        for i, node in enumerate(self.nodes):
                            if (
                                math.hypot(
                                    mouse_pos[0] - node["pos"][0],
                                    mouse_pos[1] - node["pos"][1],
                                )
                                < 12
                            ):
                                clicked_idx = i
                                break

                        if clicked_idx != -1:
                            self.selected_node_idx = clicked_idx
                        else:
                            self.nodes.append(
                                {"pos": snapped_pos, "radius": self.active_radius}
                            )
                            self.branches.append(
                                (self.selected_node_idx, len(self.nodes) - 1)
                            )
                            self.selected_node_idx = len(self.nodes) - 1

                    if event.button == 3:  # Reset al origen
                        self.selected_node_idx = 0

                    if event.button == 4:  # Rueda Arriba
                        self.active_radius += 2.0
                    if event.button == 5:  # Rueda Abajo
                        self.active_radius = max(0, self.active_radius - 2.0)

            # --- DIBUJO ---
            # 1. Bisectrices
            for start, end in self.bisectors:
                pygame.draw.line(self.screen, COLORS["crease"], start, end, 1)

            # 2. Ramas (Ríos en naranja, Puntas en azul)
            for b in self.branches:
                is_river = not (self.is_leaf(b[0]) or self.is_leaf(b[1]))
                color = COLORS["river"] if is_river else COLORS["branch"]
                pygame.draw.line(
                    self.screen,
                    color,
                    self.nodes[b[0]]["pos"],
                    self.nodes[b[1]]["pos"],
                    5 if is_river else 2,
                )

            # 3. Círculos y Nodos
            for i, node in enumerate(self.nodes):
                r_px = int(node["radius"] * (PX_TO_UNITS / 5))
                if node["radius"] > 0:
                    s = pygame.Surface((r_px * 2, r_px * 2), pygame.SRCALPHA)
                    pygame.draw.circle(s, COLORS["circle"], (r_px, r_px), r_px)
                    self.screen.blit(s, (node["pos"][0] - r_px, node["pos"][1] - r_px))

                n_color = (
                    COLORS["selected"]
                    if i == self.selected_node_idx
                    else COLORS["node"]
                )
                pygame.draw.circle(self.screen, n_color, node["pos"], 6)

            # Previsualización
            pygame.draw.line(self.screen, (100, 100, 100), ref_node_pos, snapped_pos, 1)

            # UI
            info = [
                f"Radio Puntero: {self.active_radius:.1f} u",
                "G: Generar Bisectrices | Z: Deshacer",
                "L-Click: Nodo/Dibujar | R-Click: Origen",
            ]
            for i, line in enumerate(info):
                self.screen.blit(
                    self.font.render(line, True, COLORS["text"]), (15, 15 + i * 22)
                )

            pygame.display.flip()
            self.clock.tick(FPS)
        pygame.quit()


if __name__ == "__main__":
    app = OrigamiEngine()
    app.run()
