import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import numpy as np
import math
import random
from PIL import Image

# --- Variáveis Globais para as Texturas ---
skybox_texture_id = None
meteor_texture_id = None
earth_texture_id = None
earth_rotation_angle = 0.0 

# Onde o objeto para de cair (superfície da esfera de fundo)
# Centro Y (-130.0) + Raio (100.0) = -30.0
EARTH_SURFACE_Y = -30.0 
# O PLANO DO CHÃO DO JOGADOR (Invisível, mas limita o movimento)
PENALTY_GROUND_Y = 0.0

# --- Limites do Grid de Jogo (Novas Variáveis) ---
GRID_LIMIT = 20.0 

# --- Variáveis para o CRAWL TEXT da Introdução (MODIFICADAS) ---
crawl_title = "GUERRA NAS ESFERAS" # NOVO: Título do Jogo

crawl_text = [
    "EPISÓDIO I: AMEAÇA METEÓRICA",
    "",
    "A Terra está sob ameaça! Chuvas de meteoros atingem o planeta,",
    "e a humanidade corre risco. Sua missão, como defensor espacial,",
    "é interceptar os meteoros antes que eles atinjam o solo.",
    "Cada interceptação garante 10 pontos de vida para a Terra.",
    "Contudo, cada meteoro que atinge a superfície causa uma",
    "penalidade de 5 pontos. Se a pontuação cair abaixo de zero,",
    "a missão falha. Defenda a Terra e alcance 100 pontos!",
    "",
    "COMANDOS:",
    "W, A, S, D: Movimento",
    "SHIFT ESQUERDO: Corrida (Usa Estamina)",
    "Mouse: Olhar/Girar a Câmera",
    "ESC: Sair do Jogo",
    "",
    "PREPARE-SE PARA A DEFESA!",
    ""
]
crawl_y_offset = 0.0 
crawl_speed = 0.5 

# --- Variáveis para o Fade do Título  ---
title_fade_timer = 0 
TITLE_STILL_DURATION =  240 # 4 segundos em 60 FPS
TITLE_FADE_DURATION = 90  # 1.5 segundos em 60 FPS


# --- Configurações da Câmera ---
class Camera:
    def __init__(self):
        self.position = np.array([0.0, 1.8, 5.0])
        self.yaw = -90.0
        self.pitch = 0.0
        self.fov = 70.0
        self.sensitivity = 0.25
        
        self.base_speed = 0.1
        self.sprint_speed = 0.3
        self.speed = self.base_speed
        
        self.max_stamina = 200.0
        self.current_stamina = 200.0
        self.stamina_drain_rate = 1.0
        self.stamina_recover_rate = 0.5
        
        self.up = np.array([0.0, 1.0, 0.0])

    def get_direction(self):
        yaw_rad = np.radians(self.yaw)
        pitch_rad = np.radians(self.pitch)

        x = np.cos(yaw_rad) * np.cos(pitch_rad)
        y = np.sin(pitch_rad)
        z = np.sin(yaw_rad) * np.cos(pitch_rad)
        
        direction = np.array([x, y, z])
        return direction / np.linalg.norm(direction) if np.linalg.norm(direction) > 0 else np.array([0, 0, 0])

    def process_mouse_movement(self, dx, dy):
        self.yaw += dx * self.sensitivity
        self.pitch += dy * self.sensitivity
        
        if self.pitch > 89.0:
            self.pitch = 89.0
        if self.pitch < -89.0:
            self.pitch = -89.0

    def update_movement(self, keys):
        global GRID_LIMIT
        
        is_moving = keys[K_w] or keys[K_s] or keys[K_a] or keys[K_d]
        wants_to_sprint = keys[K_LSHIFT] and is_moving
        
        is_sprinting = wants_to_sprint and self.current_stamina > 0.0
        
        if is_sprinting:
            self.speed = self.sprint_speed
            self.current_stamina = max(0.0, self.current_stamina - self.stamina_drain_rate)
            
            if self.current_stamina == 0.0:
                self.speed = self.base_speed
            
        else:
            self.speed = self.base_speed
            self.current_stamina = min(self.max_stamina, self.current_stamina + self.stamina_recover_rate)

        forward_dir = self.get_direction()
        
        right_dir = np.cross(forward_dir, self.up)
        right_dir = right_dir / np.linalg.norm(right_dir)
        
        forward_xz = np.array([forward_dir[0], 0.0, forward_dir[2]])
        forward_xz_norm = np.linalg.norm(forward_xz)
        forward_xz = forward_xz / forward_xz_norm if forward_xz_norm > 0 else np.array([0, 0, 0])

        new_position = self.position.copy()

        if keys[K_w]:
            new_position += forward_xz * self.speed
        if keys[K_s]:
            new_position -= forward_xz * self.speed
        if keys[K_a]:
            new_position -= right_dir * self.speed
        if keys[K_d]:
            new_position += right_dir * self.speed
            
        # Garante que a câmera permaneça na altura padrão (simulando o chão)
        new_position[1] = 1.8 
        
        # --- NOVO: Limita o movimento do jogador ao Grid ---
        new_position[0] = np.clip(new_position[0], -GRID_LIMIT, GRID_LIMIT)
        new_position[2] = np.clip(new_position[2], -GRID_LIMIT, GRID_LIMIT)
        
        self.position = new_position # Aplica a nova posição limitada

    def update_view(self):
        direction = self.get_direction()
        look_at = self.position + direction
        
        gluLookAt(
            self.position[0], self.position[1], self.position[2],
            look_at[0], look_at[1], look_at[2],
            self.up[0], self.up[1], self.up[2]
        )

# --- Objeto que Cai (Meteoro) ---
class DroppingObject:
    def __init__(self):
        # Os meteoros continuam nascendo aleatoriamente dentro dos limites do grid
        self.x = random.uniform(-GRID_LIMIT, GRID_LIMIT) 
        self.y = random.uniform(50.0, 100.0)
        self.z = random.uniform(-GRID_LIMIT, GRID_LIMIT) 
        
        self.size = random.uniform(1.0, 3.0)
        
        self.color = (random.random(), random.random(), random.random())
        self.speed = random.uniform(0.05, 0.15)
        self.active = True
        self.has_hit_earth = False 
        
        self.rotation_angle = random.uniform(0.0, 360.0) 
        self.rotation_speed = random.uniform(1.0, 5.0) 
        self.rotation_axis = np.array([random.random(), random.random(), random.random()])
        self.rotation_axis /= np.linalg.norm(self.rotation_axis) 

    def update(self):
        global EARTH_SURFACE_Y
        
        if self.active:
            self.y -= self.speed
            self.rotation_angle += self.rotation_speed
            
            # Desativa o objeto quando ele atinge a superfície da Terra (Y=-30.0)
            if self.y <= EARTH_SURFACE_Y:
                self.active = False
                
    def draw(self):
        global meteor_texture_id
        
        if self.active or self.y > EARTH_SURFACE_Y: 
            glPushMatrix()
            glTranslatef(self.x, self.y, self.z)
            
            # --- Aplica Rotação ---
            glRotatef(self.rotation_angle, self.rotation_axis[0], self.rotation_axis[1], self.rotation_axis[2])
            # ----------------------
            
            if meteor_texture_id:
                glEnable(GL_TEXTURE_2D)
                glBindTexture(GL_TEXTURE_2D, meteor_texture_id)
                glColor3f(1.0, 1.0, 1.0)
            else:
                glColor3f(*self.color)
            
            quadric = gluNewQuadric()
            gluQuadricTexture(quadric, GL_TRUE) 
            
            gluSphere(quadric, self.size, 5, 5)
            gluDeleteQuadric(quadric)
            
            if meteor_texture_id:
                glBindTexture(GL_TEXTURE_2D, 0)
                glDisable(GL_TEXTURE_2D)
            
            glPopMatrix()

    def check_collision(self, player_pos):
        if not self.active:
            return False
        
        player_x = player_pos[0]
        player_y = player_pos[1]  
        player_z = player_pos[2]
        
        meteor_x = self.x
        meteor_y = self.y
        meteor_z = self.z
        
        distance_3d = math.sqrt(
            (meteor_x - player_x)**2 + 
            (meteor_y - player_y)**2 + 
            (meteor_z - player_z)**2
        )
        
        collision_radius = self.size + 0.5 
        
        if distance_3d < collision_radius:
            self.active = False
            return True
            
        return False

# ----------------------------------------------------
# --- Funções de Texturização e Desenho 3D ---
# ----------------------------------------------------

def load_texture(filename):
    """Carrega uma imagem e a converte para uma textura OpenGL."""
    try:
        img = Image.open(filename)
        if img.mode != 'RGBA':
            img = img.convert('RGBA') 
            
        img_data = img.tobytes("raw", "RGBA")
        width, height = img.size
    except FileNotFoundError:
        print(f"ERRO: Arquivo de textura '{filename}' não encontrado. O objeto será desenhado sem textura.")
        return 0
    except Exception as e:
        print(f"ERRO ao carregar a textura '{filename}': {e}")
        return 0

    texture_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, texture_id)

    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT) 
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)

    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, img_data)
    
    glBindTexture(GL_TEXTURE_2D, 0)
    return texture_id

def draw_skybox(texture_id, size=500.0):
    """Desenha um cubo texturizado gigante (skybox) centrado na câmera."""
    
    glPushMatrix()
    
    R = glGetFloatv(GL_MODELVIEW_MATRIX)
    R[3, 0] = R[3, 1] = R[3, 2] = 0.0 
    glLoadMatrixf(R)

    glDisable(GL_LIGHTING)
    glDisable(GL_DEPTH_TEST) 
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, texture_id)
    glColor3f(1.0, 1.0, 1.0) 
    
    s = size / 2.0
    
    # Texturas do Skybox devem ser CLAMPED para evitar costuras
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE) 
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)

    glBegin(GL_QUADS)
    
    # Face FRONTAL (+Z)
    glTexCoord2f(0.0, 0.0); glVertex3f(-s, -s, s)
    glTexCoord2f(1.0, 0.0); glVertex3f( s, -s, s)
    glTexCoord2f(1.0, 1.0); glVertex3f( s,  s, s)
    glTexCoord2f(0.0, 1.0); glVertex3f(-s,  s, s)

    # Face TRASEIRA (-Z)
    glTexCoord2f(1.0, 0.0); glVertex3f(-s, -s, -s)
    glTexCoord2f(1.0, 1.0); glVertex3f(-s,  s, -s)
    glTexCoord2f(0.0, 1.0); glVertex3f( s,  s, -s)
    glTexCoord2f(0.0, 0.0); glVertex3f( s, -s, -s)
    
    # Face SUPERIOR (+Y)
    glTexCoord2f(0.0, 1.0); glVertex3f(-s, s, -s)
    glTexCoord2f(0.0, 0.0); glVertex3f(-s, s,  s)
    glTexCoord2f(1.0, 0.0); glVertex3f( s, s,  s)
    glTexCoord2f(1.0, 1.0); glVertex3f( s, s, -s)
    
    # Face INFERIOR (-Y)
    glTexCoord2f(0.0, 0.0); glVertex3f(-s, -s, -s)
    glTexCoord2f(1.0, 0.0); glVertex3f( s, -s, -s)
    glTexCoord2f(1.0, 1.0); glVertex3f( s, -s,  s)
    glTexCoord2f(0.0, 1.0); glVertex3f(-s, -s,  s)

    # Face DIREITA (+X)
    glTexCoord2f(1.0, 0.0); glVertex3f( s, -s, -s)
    glTexCoord2f(1.0, 1.0); glVertex3f( s,  s, -s)
    glTexCoord2f(0.0, 1.0); glVertex3f( s,  s,  s)
    glTexCoord2f(0.0, 0.0); glVertex3f( s, -s,  s)
    
    # Face ESQUERDA (-X)
    glTexCoord2f(0.0, 0.0); glVertex3f(-s, -s, -s)
    glTexCoord2f(1.0, 0.0); glVertex3f(-s, -s,  s)
    glTexCoord2f(1.0, 1.0); glVertex3f(-s,  s,  s)
    glTexCoord2f(0.0, 1.0); glVertex3f(-s,  s, -s)
    
    glEnd()
    
    glBindTexture(GL_TEXTURE_2D, 0)
    glDisable(GL_TEXTURE_2D)
    glEnable(GL_DEPTH_TEST) 
    glPopMatrix() 
    
    # Restaura o modo REPEAT para as texturas normais
    if texture_id:
        glBindTexture(GL_TEXTURE_2D, texture_id)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT) 
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
        glBindTexture(GL_TEXTURE_2D, 0)

def draw_ground():
    """CORRIGIDO: Não desenha mais o chão, apenas a esfera da Terra será visível."""
    pass 

def draw_half_sphere():
    """Desenha uma meia esfera (hemisfério inferior) centrada abaixo do chão com textura da Terra."""
    global earth_texture_id, earth_rotation_angle 
    
    center_y = -130.0 
    radius = 100.0 
    
    glPushMatrix()
    glTranslatef(0.0, center_y, 0.0) 
    
    glRotatef(earth_rotation_angle, 0.0, 1.0, 0.0)
    glRotatef(90.0, 1.0, 0.0, 0.0) # Ajusta a orientação da esfera
    
    if earth_texture_id:
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, earth_texture_id)
        glColor3f(1.0, 1.0, 1.0) 
    else:
        glColor3f(0.0, 0.0, 0.5) 
    
    quadric = gluNewQuadric()
    gluQuadricDrawStyle(quadric, GLU_FILL) 
    gluQuadricTexture(quadric, GL_TRUE) 
    
    # Desenha a esfera
    gluSphere(quadric, radius, 30, 30)
    
    gluDeleteQuadric(quadric)
    
    if earth_texture_id:
        glBindTexture(GL_TEXTURE_2D, 0)
        glDisable(GL_TEXTURE_2D)
    
    glPopMatrix()


def draw_scene(dropping_objects, skybox_id):
    """Função principal de desenho da cena."""
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    
    glMatrixMode(GL_MODELVIEW) 
    
    # 1. Desenha o Skybox 
    if skybox_id:
        draw_skybox(skybox_id) 
    
    # 2. Desenha o Chão e a Terra
    draw_half_sphere() # Desenha a Terra (esfera)
    draw_ground() # Desenha o plano do chão em Y=0.0 (AGORA INVISÍVEL)
    
    # 3. Desenha os Meteoros
    for obj in dropping_objects:
        obj.draw()
        
# ----------------------------------------------------
# --- Funções de Desenho 2D (Overlay/HUD) ---
# ----------------------------------------------------

def setup_2d_projection(display_size):
    """Configura a matriz de projeção para desenho 2D."""
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    width, height = display_size
    glOrtho(0, width, 0, height, -1, 1)
    
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    
    glDisable(GL_DEPTH_TEST)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

def restore_3d_projection():
    """Restaura a matriz de projeção para desenho 3D."""
    glDisable(GL_BLEND)
    glEnable(GL_DEPTH_TEST)
    glPopMatrix() 
    glMatrixMode(GL_PROJECTION)
    glPopMatrix() 
    glMatrixMode(GL_MODELVIEW)

def draw_text_2d(text, x, y, font, color=(255, 255, 255, 255)):
    """Renderiza texto 2D na tela usando Pygame Surfaces."""
    setup_2d_projection(pygame.display.get_surface().get_size())
    
    # O Pygame Surfaces não suporta alpha no texto diretamente, 
    # então o color[3] (alpha) é usado no glColor para o DrawPixels.
    text_surface = font.render(text, True, color[:3]) 
    text_data = pygame.image.tostring(text_surface, "RGBA", True)

    width, height = pygame.display.get_surface().get_size()
    # Inverte Y para Pygame (topo = 0) vs OpenGL (baixo = 0)
    # A cor deve ser definida com o alpha ANTES do glDrawPixels
    
    # Configura a cor e alpha (importante para o fade-out do título)
    glColor4ub(*color)
    
    glRasterPos2i(x, height - y - text_surface.get_height()) 
    
    glDrawPixels(text_surface.get_width(), text_surface.get_height(), 
                 GL_RGBA, GL_UNSIGNED_BYTE, text_data)
    
    # Restaura a cor para branco (sem alpha)
    glColor4f(1.0, 1.0, 1.0, 1.0)
    
    restore_3d_projection()

def draw_centered_text(text, font, display_size, y_offset=0, color=(255, 255, 255, 255)):
    """Renderiza texto 2D centralizado na tela."""
    setup_2d_projection(display_size)
    
    width, height = display_size
    text_surface = font.render(text, True, color[:3]) # Cor sem alpha para renderização do Pygame
    text_w, text_h = text_surface.get_size()
    
    x = (width - text_w) // 2
    y_center = (height - text_h) // 2 + y_offset 
    
    text_data = pygame.image.tostring(text_surface, "RGBA", True)

    # Configura a cor e alpha (importante para o fade-out do título)
    glColor4ub(*color)

    # Inverte Y para Pygame (topo = 0) vs OpenGL (baixo = 0)
    glRasterPos2i(x, height - y_center - text_h) 
    
    glDrawPixels(text_w, text_h, GL_RGBA, GL_UNSIGNED_BYTE, text_data)
    
    # Restaura a cor para branco (sem alpha)
    glColor4f(1.0, 1.0, 1.0, 1.0)
    
    restore_3d_projection()
    
# --- FUNÇÃO NOVA/MODIFICADA PARA O TÍTULO VAZADO ---
def draw_outlined_text(text, font, display_size, y_offset=0, fill_color=(0, 0, 0, 0), outline_color=(255, 210, 0, 255), outline_size=3):
    """
    Renderiza texto centralizado com contorno, simulando o efeito vazado (preenchimento preto).
    """
    setup_2d_projection(display_size)
    width, height = display_size
    
    # 1. Renderiza a superfície do contorno (Outline)
    outline_surface = font.render(text, True, outline_color[:3]) 
    outline_w, outline_h = outline_surface.get_size()
    
    # Posições de base (centralizadas)
    base_x = (width - outline_w) // 2
    base_y = (height - outline_h) // 2 + y_offset 

    # Desenha o contorno movendo a posição do glRasterPos2i
    
    # Configura a cor e alpha do contorno (Amarelo Star Wars)
    glColor4ub(*outline_color)
    outline_data = pygame.image.tostring(outline_surface, "RGBA", True)

    offsets = [
        (-outline_size, -outline_size), (outline_size, -outline_size), 
        (-outline_size, outline_size), (outline_size, outline_size), 
        (0, -outline_size), (0, outline_size), 
        (-outline_size, 0), (outline_size, 0)
    ]
    
    # Desenha o contorno (8 vezes)
    for dx, dy in offsets:
        # Inverte Y para Pygame (topo = 0) vs OpenGL (baixo = 0)
        raster_y = height - (base_y + dy) - outline_h 
        glRasterPos2i(base_x + dx, raster_y) 
        glDrawPixels(outline_w, outline_h, GL_RGBA, GL_UNSIGNED_BYTE, outline_data)

    
    # 2. Renderiza a superfície do preenchimento (Fill)
    # A cor do preenchimento é preta (0, 0, 0) para o efeito vazado no fundo preto do espaço.
    fill_surface = font.render(text, True, fill_color[:3]) 
    
    # Configura a cor e alpha do preenchimento 
    glColor4ub(*fill_color)
    fill_data = pygame.image.tostring(fill_surface, "RGBA", True)
    
    # Posição central (sem offset)
    raster_y = height - base_y - outline_h
    glRasterPos2i(base_x, raster_y) 
    
    glDrawPixels(outline_w, outline_h, GL_RGBA, GL_UNSIGNED_BYTE, fill_data)
    
    # Restaura a cor para branco (sem alpha)
    glColor4f(1.0, 1.0, 1.0, 1.0)
    
    restore_3d_projection()
    
def draw_star_wars_crawl(font, display_size):
    """Desenha e anima o texto de abertura subindo no estilo de rolagem (2D)."""
    global crawl_y_offset, crawl_text, crawl_speed
    
    setup_2d_projection(display_size)
    width, height = display_size
    
    line_spacing = 40 
    crawl_color = (255, 210, 0, 255) 
    
    num_lines = len(crawl_text)
    # Calcula a altura total do bloco de texto
    total_text_height = num_lines * line_spacing
    
    # 1. POSIÇÃO DE INÍCIO (Start Base Y)
    start_base_y = -total_text_height 

    # 2. CONDIÇÃO DE TÉRMINO
    if crawl_y_offset > total_text_height + height:
        restore_3d_projection()
        return True 

    # Renderiza cada linha
    for i, line in enumerate(crawl_text):
        # A cor do crawl é amarela e opaca, mas precisa ser definida aqui
        glColor4ub(*crawl_color)
        
        text_surface = font.render(line, True, crawl_color[:3])
        text_w, text_h = text_surface.get_size()
        
        # O índice invertido garante que o primeiro texto da lista (EPISÓDIO VI) 
        # apareça primeiro na parte inferior da tela.
        inverted_index = num_lines - 1 - i 
        
        # Posição Y da linha na tela (coordenada OpenGL: y=0 é o fundo)
        line_y = start_base_y + (inverted_index * line_spacing) + crawl_y_offset

        # Se a linha estiver fora dos limites visíveis, não renderiza
        if line_y < -text_h or line_y > height + text_h:
            continue

        # Calcula a posição X centralizada
        x = (width - text_w) // 2
        
        # glRasterPos2i espera a coordenada OpenGL (y=0 é o fundo da janela)
        glRasterPos2i(x, int(line_y))
        
        # Desenha a linha
        text_data = pygame.image.tostring(text_surface, "RGBA", True)
        glDrawPixels(text_w, text_h, GL_RGBA, GL_UNSIGNED_BYTE, text_data)

    # Restaura a cor para branco (sem alpha)
    glColor4f(1.0, 1.0, 1.0, 1.0)
        
    # Atualiza o offset para a próxima frame (movimento para cima)
    crawl_y_offset += crawl_speed
    
    restore_3d_projection()
    return False

def draw_stamina_bar(current, max_stamina, display_size):
    """Desenha a barra de estamina no canto inferior esquerdo da tela."""
    
    setup_2d_projection(display_size)
    
    bar_width_max = 200
    bar_height = 15
    bar_padding_bottom = 30
    bar_padding_left = 30 
    
    bar_x = bar_padding_left 
    bar_y = bar_padding_bottom 
    
    stamina_ratio = current / max_stamina
    bar_width_current = bar_width_max * stamina_ratio
    
    # 1. Fundo da barra
    glColor4f(0.2, 0.2, 0.2, 0.8) 
    glBegin(GL_QUADS)
    glVertex2f(bar_x, bar_y)
    glVertex2f(bar_x + bar_width_max, bar_y)
    glVertex2f(bar_x + bar_width_max, bar_y + bar_height)
    glVertex2f(bar_x, bar_y + bar_height)
    glEnd()
    
    # 2. Preenchimento da estamina
    if stamina_ratio > 0:
        r = 1.0 if stamina_ratio < 0.5 else 1.0 - (stamina_ratio - 0.5) * 2.0
        g = 1.0 if stamina_ratio > 0.5 else stamina_ratio * 2.0
        b = 0.0
        glColor4f(r, g, b, 0.9)
        
        glBegin(GL_QUADS)
        glVertex2f(bar_x, bar_y)
        glVertex2f(bar_x + bar_width_current, bar_y)
        glVertex2f(bar_x + bar_width_current, bar_y + bar_height)
        glVertex2f(bar_x, bar_y + bar_height)
        glEnd()

    # 3. Borda
    glColor4f(1.0, 1.0, 1.0, 1.0)
    glLineWidth(2.0)
    glBegin(GL_LINE_LOOP)
    glVertex2f(bar_x, bar_y)
    glVertex2f(bar_x + bar_width_max, bar_y)
    glVertex2f(bar_x + bar_width_max, bar_y + bar_height)
    glVertex2f(bar_x, bar_y + bar_height)
    glEnd()
    
    restore_3d_projection()


STAR_WARS_THEME_PATH = "sounds/star_wars_theme.mp3" 
WILHELM_SCREAM_PATH = "sounds/scream.mp3" 
wilhelm_scream_sound = None 

# --- Função Principal (MODIFICADA) ---
def main():
    global skybox_texture_id, meteor_texture_id, earth_texture_id, earth_rotation_angle, crawl_y_offset, wilhelm_scream_sound
    global title_fade_timer, crawl_title, TITLE_STILL_DURATION, TITLE_FADE_DURATION
    
    pygame.init()
    
    # Inicializa o mixer de áudio
    pygame.mixer.init()
    
    display = (1280, 720)
    pygame.display.set_mode(display, DOUBLEBUF | OPENGL)
    pygame.display.set_caption("PyOpenGL Catch the Meteors") 
    
    # Mouse inicialmente visível e livre para a tela de título/intro
    pygame.mouse.set_visible(True) 
    pygame.event.set_grab(False)
    
    cam = Camera()
    
    # --- Carrega as Texturas (ATENÇÃO: ajuste os caminhos se necessário) ---
    skybox_texture_id = load_texture("textures/stars.jpg") 
    meteor_texture_id = load_texture("textures/meteor.jpg")
    earth_texture_id = load_texture("textures/earth.jpg") 

    # Configuração da Perspectiva
    glMatrixMode(GL_PROJECTION)
    gluPerspective(cam.fov, (display[0] / display[1]), 0.1, 1000.0) 
    
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    
    # Configurações do OpenGL
    glEnable(GL_DEPTH_TEST)
    glClearColor(0.0, 0.0, 0.0, 1.0) 
    
    score = 0
    
    try:
        pygame.font.init()
        font = pygame.font.Font(None, 36) 
        # MODIFICAÇÃO: Aumenta o tamanho da fonte do título
        font_large = pygame.font.Font(None, 120) 
        font_crawl = pygame.font.Font(None, 48)
    except:
        font = pygame.font.SysFont('Arial', 36)
        # MODIFICAÇÃO: Aumenta o tamanho da fonte do título
        font_large = pygame.font.SysFont('Arial', 120)
        font_crawl = pygame.font.SysFont('Arial', 48)

    # --- Carregamento do Wilhelm Scream ---
    try:
        wilhelm_scream_sound = pygame.mixer.Sound(WILHELM_SCREAM_PATH)
        print(f"Som '{WILHELM_SCREAM_PATH}' carregado com sucesso.")
    except pygame.error as e:
        print(f"AVISO: ERRO ao carregar o som do Game Over: {e}. Verifique se o arquivo '{WILHELM_SCREAM_PATH}' existe.")
        wilhelm_scream_sound = None
    # ------------------------------------------

    dropping_objects = []
    
    object_spawn_timer = 0
    SPAWN_INTERVAL = 60 
    WIN_SCORE = 100
    
    # ESTADO INICIAL: Tela de Título
    game_state = "TITLE_SCREEN" 
    
    clock = pygame.time.Clock()
    running = True
    
    EARTH_ROTATION_SPEED = 0.1 
    
    # Lógica de Carregamento e Início da Música
    try:
        pygame.mixer.music.load(STAR_WARS_THEME_PATH)
        # Toca a música em loop (-1) para garantir que ela não pare antes da intro
        pygame.mixer.music.play(-1) 
        print(f"Música '{STAR_WARS_THEME_PATH}' iniciada.")
    except pygame.error as e:
        print(f"ERRO ao carregar ou tocar a música: {e}. Verifique se o arquivo de áudio está correto.")
        pass


    while running:
        # Gerenciamento de Eventos 
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE: 
                    running = False
                
                # Pular TITLE_SCREEN / INTRO
                if (game_state == "TITLE_SCREEN" or game_state == "INTRO") and event.key == pygame.K_SPACE:
                    game_state = "RUNNING"
                    pygame.mouse.set_visible(False)
                    pygame.event.set_grab(True)
                    pygame.mixer.music.stop() 
                    
            if game_state == "RUNNING":
                if event.type == pygame.MOUSEMOTION:
                    dx, dy = event.rel
                    cam.process_mouse_movement(dx, -dy)

        keys = pygame.key.get_pressed()
        
        # --- Lógica de Estado ---
        if game_state == "TITLE_SCREEN":
            # Gira a Terra, mas não move a câmera
            glLoadIdentity()
            cam.update_view()
            draw_scene(dropping_objects, skybox_texture_id) 
            
            # --- Lógica do Título com Fade Out (NOVA) ---
            
            if title_fade_timer < TITLE_STILL_DURATION:
                # Título Estático
                alpha = 1.0
            elif title_fade_timer < TITLE_STILL_DURATION + TITLE_FADE_DURATION:
                # Título em Fade Out
                fade_time = title_fade_timer - TITLE_STILL_DURATION
                alpha = 1.0 - (fade_time / TITLE_FADE_DURATION)
            else:
                # Transição para o CRAWL
                game_state = "INTRO"
                title_fade_timer = 0 # Reinicia para não influenciar o próximo estado
                
            title_fade_timer += 1
            
            # Garante que o alpha não fique negativo ou maior que 1
            alpha = max(0.0, min(1.0, alpha))
            
            # Cor do contorno (Amarelo Star Wars) com Alpha (Desvanecimento)
            # O Pygame usa 0-255 para o componente alpha
            outline_color = (255, 210, 0, int(alpha * 255))
            
            # Cor do preenchimento: PRETO (cor do fundo do espaço) para dar o efeito vazado
            fill_color = (0, 0, 0, int(alpha * 255)) 
            
            # --- MODIFICAÇÃO: Usa a função de texto contornado e vazado ---
            draw_outlined_text(
                crawl_title, 
                font_large, 
                display, 
                y_offset=-50, 
                fill_color=fill_color,
                outline_color=outline_color,
                outline_size=3 # Tamanho do contorno
            )
            # ----------------------------------------------------------------

            # Adiciona um texto para pular
            draw_centered_text("Pressione ESPAÇO para Pular", font, display, y_offset=300, color=(150, 150, 150, 255))
            
        
        elif game_state == "INTRO":
            # Gira a Terra, mas não move a câmera
            glLoadIdentity()
            cam.update_view()
            draw_scene(dropping_objects, skybox_texture_id) 
            
            # Atualiza e desenha o CRAWL TEXT
            intro_finished = draw_star_wars_crawl(font_crawl, display)
            
            if intro_finished:
                game_state = "RUNNING"
                pygame.mouse.set_visible(False)
                pygame.event.set_grab(True)
                # Para a música quando a intro termina
                pygame.mixer.music.stop() 
            
            # Adiciona um texto para pular
            draw_centered_text("Pressione ESPAÇO para Pular", font, display, y_offset=300, color=(150, 150, 150, 255))
            
        elif game_state == "RUNNING":
            # Lógica RUNNING inalterada
            
            # Movimento e Câmera
            cam.update_movement(keys)
            glLoadIdentity()
            cam.update_view()
            
            # Lógica do Jogo (Objetos, Colisão e Rotação)
            
            # Rotação da Terra
            earth_rotation_angle += EARTH_ROTATION_SPEED
            if earth_rotation_angle >= 360.0:
                earth_rotation_angle -= 360.0
                
            for obj in list(dropping_objects): 
                obj.update() 
                
                # Colisão com o Jogador (Ganha Pontos)
                if obj.check_collision(cam.position):
                    score += 10 
                    dropping_objects.remove(obj) 
                    continue 
                
                # Penalidade por Atingir a Terra (Y <= EARTH_SURFACE_Y)
                if not obj.active and not obj.has_hit_earth:
                    score -= 5 
                    obj.has_hit_earth = True 
                    
                # Remoção por Atingir a Terra (Y=-30.0)
                if not obj.active and obj.has_hit_earth:
                    dropping_objects.remove(obj)


            object_spawn_timer += 1
            if object_spawn_timer >= SPAWN_INTERVAL:
                dropping_objects.append(DroppingObject())
                object_spawn_timer = 0
            
            # Checagem de Estado: Game Over ou Win
            if score < 0:
                game_state = "GAME_OVER"
                pygame.mouse.set_visible(True)
                pygame.event.set_grab(False)
                pygame.mixer.music.stop() 
                # --- NOVO: Toca o Wilhelm Scream ---
                if wilhelm_scream_sound:
                    wilhelm_scream_sound.play() 
                # ------------------------------------
            elif score >= WIN_SCORE:
                game_state = "WIN"
                pygame.mouse.set_visible(True)
                pygame.event.set_grab(False)
                pygame.mixer.music.stop() 
                
            # Desenho da Cena 3D ---
            draw_scene(dropping_objects, skybox_texture_id)

            # Desenho do Placar e Estamina 2D (Overlay) ---
            score_text = f"SCORE: {score} / {WIN_SCORE}"
            draw_text_2d(score_text, 10, 10, font) 
            draw_stamina_bar(cam.current_stamina, cam.max_stamina, display)
        
        elif game_state == "GAME_OVER" or game_state == "WIN":
            # Lógica GAME_OVER/WIN 
            
            # Mantém a última cena 3D visível
            glLoadIdentity()
            cam.update_view()
            draw_scene(dropping_objects, skybox_texture_id)
            
            # Configurações 2D para a tela de fundo
            setup_2d_projection(display)
            
            # Fundo preto semi-transparente
            glColor4f(0.0, 0.0, 0.0, 0.8) 
            glBegin(GL_QUADS)
            glVertex2f(0, 0); glVertex2f(display[0], 0); glVertex2f(display[0], display[1]); glVertex2f(0, display[1])
            glEnd()
            
            restore_3d_projection()
            
            # Textos
            score_text = f"SCORE: {score} / {WIN_SCORE}"
            draw_text_2d(score_text, 10, 10, font) 
            
            if game_state == "GAME_OVER":
                draw_centered_text("GAME OVER", font_large, display, y_offset=-50, color=(255, 0, 0, 255))
                draw_centered_text("Pressione ESC para sair", font, display, y_offset=60, color=(150, 150, 150, 255))
            else: # WIN
                draw_centered_text("VITÓRIA!", font_large, display, y_offset=-50, color=(0, 255, 0, 255))
                draw_centered_text(f"Você defendeu a Terra!", font, display, y_offset=0, color=(255, 255, 255, 255))
                draw_centered_text("Pressione ESC para sair", font, display, y_offset=60, color=(150, 150, 150, 255))


        # --- 6. Atualização da Tela ---
        pygame.display.flip()
        clock.tick(60)

    # Libera o mixer
    pygame.mixer.quit()
        
    pygame.quit()

if __name__ == "__main__":
    main()
