import pygame
import math

# --- CONFIGURACIÓN Y CONSTANTES ---
WIDTH, HEIGHT = 900, 800
FPS = 60
SNAP_ANGLE = 22.5  
COLORS = {
    'bg': (30, 30, 30),
    'grid': (60, 60, 60),
    'node': (255, 255, 255),
    'branch': (0, 200, 255),
    'preview': (0, 255, 100, 100),
    'circle': (0, 255, 100, 50),   # Verde transparente
    'error': (255, 50, 50, 120),    # Rojo para colisiones
    'text': (200, 200, 200)
}

class OrigamiEngine:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Origami 22.5 - Fase 2: Circle Packing & Collision")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Consolas", 14)
        
        # Estado del modelo: ahora cada nodo es un diccionario
        self.origin = (WIDTH // 2, HEIGHT // 2)
        self.nodes = [{'pos': self.origin, 'radius': 0}] 
        self.branches = []  
        
        # Radio activo para la previsualización
        self.active_radius = 50

    def get_snapped_pos(self, mouse_pos, last_node_pos):
        """Calcula la posición del ratón restringida a 22.5 grados."""
        dx = mouse_pos[0] - last_node_pos[0]
        dy = mouse_pos[1] - last_node_pos[1]
        dist = math.sqrt(dx**2 + dy**2)
        if dist < 1: return last_node_pos, 0
        
        angle_deg = math.degrees(math.atan2(dy, dx))
        snapped_deg = round(angle_deg / SNAP_ANGLE) * SNAP_ANGLE
        snapped_rad = math.radians(snapped_deg)
        
        new_x = last_node_pos[0] + dist * math.cos(snapped_rad)
        new_y = last_node_pos[1] + dist * math.sin(snapped_rad)
        return (int(new_x), int(new_y)), snapped_deg

    def check_collisions(self):
        """Detecta qué nodos solapan sus círculos de papel."""
        collisions = set()
        for i in range(len(self.nodes)):
            for j in range(i + 1, len(self.nodes)):
                node_a = self.nodes[i]
                node_b = self.nodes[j]
                dist = math.hypot(node_a['pos'][0] - node_b['pos'][0], 
                                  node_a['pos'][1] - node_b['pos'][1])
                if dist < (node_a['radius'] + node_b['radius']):
                    collisions.add(i)
                    collisions.add(j)
        return collisions

    def draw_radial_grid(self, center_pos):
        for i in range(16):
            angle = math.radians(i * SNAP_ANGLE)
            end_x = center_pos[0] + 1000 * math.cos(angle)
            end_y = center_pos[1] + 1000 * math.sin(angle)
            pygame.draw.line(self.screen, COLORS['grid'], center_pos, (end_x, end_y), 1)

    def run(self):
        running = True
        while running:
            self.screen.fill(COLORS['bg'])
            mouse_pos = pygame.mouse.get_pos()
            last_node_pos = self.nodes[-1]['pos']
            snapped_pos, current_angle = self.get_snapped_pos(mouse_pos, last_node_pos)
            
            # Verificación de colisiones
            collisions = self.check_collisions()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1: # Clic izquierdo: Fijar nodo
                        self.nodes.append({'pos': snapped_pos, 'radius': self.active_radius})
                        self.branches.append((len(self.nodes) - 2, len(self.nodes) - 1))
                    
                    if event.button == 3: # Clic derecho: Volver al origen
                        self.nodes.append({'pos': self.origin, 'radius': 0})
                    
                    # Rueda del ratón: Ajustar radio
                    if event.button == 4: self.active_radius += 10
                    if event.button == 5: self.active_radius = max(0, self.active_radius - 10)

            # --- DIBUJO ---
            self.draw_radial_grid(last_node_pos)
            
            # 1. Dibujar Círculos (Circle Packing)
            for idx, node in enumerate(self.nodes):
                if node['radius'] > 0:
                    color = COLORS['error'] if idx in collisions else COLORS['circle']
                    # Superficie para transparencia
                    s = pygame.Surface((node['radius']*2, node['radius']*2), pygame.SRCALPHA)
                    pygame.draw.circle(s, color, (node['radius'], node['radius']), node['radius'])
                    self.screen.blit(s, (node['pos'][0]-node['radius'], node['pos'][1]-node['radius']))

            # 2. Dibujar Ramas
            for start_idx, end_idx in self.branches:
                pygame.draw.line(self.screen, COLORS['branch'], self.nodes[start_idx]['pos'], self.nodes[end_idx]['pos'], 3)
            
            # 3. Dibujar Nodos
            for node in self.nodes:
                pygame.draw.circle(self.screen, COLORS['node'], node['pos'], 4)

            # 4. Previsualización
            # Línea
            pygame.draw.line(self.screen, COLORS['preview'], last_node_pos, snapped_pos, 2)
            # Círculo fantasma
            if self.active_radius > 0:
                ghost_s = pygame.Surface((self.active_radius*2, self.active_radius*2), pygame.SRCALPHA)
                pygame.draw.circle(ghost_s, (150, 150, 150, 60), (self.active_radius, self.active_radius), self.active_radius, 1)
                self.screen.blit(ghost_s, (snapped_pos[0]-self.active_radius, snapped_pos[1]-self.active_radius))

            # 5. UI Información
            info_text = [
                f"Nodos: {len(self.nodes)}",
                f"Radio Activo: {self.active_radius}",
                f"Ángulo Snap: {current_angle % 360:.1f}°",
                "Rueda Mouse: +/- Radio",
                "L-Click: Dibujar / R-Click: Origen"
            ]
            for i, line in enumerate(info_text):
                img = self.font.render(line, True, COLORS['text'])
                self.screen.blit(img, (10, 10 + i * 20))

            pygame.display.flip()
            self.clock.tick(FPS)
        pygame.quit()

if __name__ == "__main__":
    app = OrigamiEngine()
    app.run()