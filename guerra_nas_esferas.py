import math
import os
import random
import sys
import time

import numpy as np
import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
from PIL import Image

DISPLAY_SIZE = (1280, 720)

BLACK = (0, 0, 0)
GRAY = (180, 180, 180)
YELLOW = (255, 255, 0)


sound_on = None
sound_off = None


def _load_saber_sounds():
    """Carrega os sons do sabre. Antes isso rodava no nível do módulo,
    antes de pygame.init() ser chamado em main() — funcionava só porque
    pygame.mixer.Sound() não exige pygame.init(), apenas mixer.init().
    Isso era uma dependência de ordem de execução implícita e frágil:
    qualquer reorganização do topo do arquivo (ou import deste módulo por
    outro código antes de qualquer init do pygame) poderia quebrar
    silenciosamente. Agora é chamada explicitamente por main(), depois
    de pygame.init()/pygame.mixer.init()."""
    global sound_on, sound_off
    try:
        sound_on = pygame.mixer.Sound("sounds/saber_on.mp3")
        sound_off = pygame.mixer.Sound("sounds/saber_off.mp3")
    except pygame.error as e:
        print(f"AVISO: não foi possível carregar os sons do sabre: {e}")
        sound_on = None
        sound_off = None


SABER_ON = False
blade_progress = 0.0
BLADE_GROW_SPEED = 2.0

_last_time = time.time()

HILT_LENGTH = 0.3
HILT_RADIUS = 0.06
BLADE_LENGTH = 2.0
BLADE_RADIUS = 0.03
GLOW_RADIUS = 0.06
CYL_SEGMENTS = 32

BLADE_COLOR = (0.0, 0.8, 1.0)


def draw_cylinder(length, radius, segments):
    glBegin(GL_QUAD_STRIP)
    for i in range(segments + 1):
        t = i / segments
        ang = t * 2 * math.pi
        x = math.cos(ang) * radius
        z = math.sin(ang) * radius
        glVertex3f(x, 0.0, z)
        glVertex3f(x, length, z)
    glEnd()


def draw_hilt():
    glPushMatrix()
    glColor3f(0.1, 0.1, 0.1)
    glScalef(HILT_RADIUS, HILT_LENGTH, HILT_RADIUS)

    faces = [
        [(-0.5, -0.5, 0.5), (0.5, -0.5, 0.5), (0.5, 0.5, 0.5), (-0.5, 0.5, 0.5)],
        [(-0.5, -0.5, -0.5), (0.5, -0.5, -0.5), (0.5, 0.5, -0.5), (-0.5, 0.5, -0.5)],
        [(-0.5, -0.5, -0.5), (-0.5, -0.5, 0.5), (-0.5, 0.5, 0.5), (-0.5, 0.5, -0.5)],
        [(0.5, -0.5, -0.5), (0.5, -0.5, 0.5), (0.5, 0.5, 0.5), (0.5, 0.5, -0.5)],
        [(-0.5, 0.5, 0.5), (0.5, 0.5, 0.5), (0.5, 0.5, -0.5), (-0.5, 0.5, -0.5)],
        [(-0.5, -0.5, 0.5), (0.5, -0.5, 0.5), (0.5, -0.5, -0.5), (-0.5, -0.5, -0.5)],
    ]

    glBegin(GL_QUADS)
    for face in faces:
        for v in face:
            glVertex3f(*v)
    glEnd()
    glPopMatrix()


def get_pulse_factor():
    t = time.time()
    return 0.5 + 0.5 * math.sin(t * 6.0)


def draw_blade():
    r, g, b = BLADE_COLOR
    current_length = BLADE_LENGTH * blade_progress

    pulse = get_pulse_factor()

    glow_radius = GLOW_RADIUS * (1.0 + 0.12 * pulse)

    glow_alpha = 0.10 + 0.10 * pulse
    core_alpha = 0.75 + 0.20 * pulse

    glDisable(GL_DEPTH_TEST)

    glColor4f(r, g, b, glow_alpha)
    draw_cylinder(current_length, glow_radius, CYL_SEGMENTS)

    glColor4f(r * 1.4, g * 1.4, b * 1.4, core_alpha)
    draw_cylinder(current_length, BLADE_RADIUS, CYL_SEGMENTS)

    glEnable(GL_DEPTH_TEST)


def _update_saber_internal():
    global blade_progress, _last_time

    now = time.time()
    dt = now - _last_time
    _last_time = now

    if SABER_ON:
        blade_progress += dt * BLADE_GROW_SPEED
        blade_progress = min(blade_progress, 1.0)
    else:
        blade_progress -= dt * BLADE_GROW_SPEED
        blade_progress = max(blade_progress, 0.0)


def draw_lightsaber(cam):
    _update_saber_internal()

    glPushMatrix()

    glTranslatef(*cam.position)
    glRotatef(-cam.yaw - 90, 0, 1, 0)
    glRotatef(cam.pitch, 1, 0, 0)

    glTranslatef(0.35, -0.5, -1.0)
    glRotatef(30.0, 0, 1, 0)

    draw_hilt()

    if blade_progress > 0.001:
        glTranslatef(0.0, HILT_LENGTH * 0.5, 0.0)
        draw_blade()

    glPopMatrix()


def toggle_saber():
    global SABER_ON

    SABER_ON = not SABER_ON

    if SABER_ON:
        if sound_on:
            sound_on.play()
    else:
        if sound_off:
            sound_off.play()


MENU_METEOR_COLOR = (0.8, 0.4, 0.1)


menu_globe_texture_id = None
menu_stars_texture_id = None
menu_meteor_texture_id = None


def menu_init_gl():
    glClearColor(0.0, 0.0, 0.0, 0.0)
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glLightfv(GL_LIGHT0, GL_POSITION, (1, 1, 1, 0))
    glLightfv(GL_LIGHT0, GL_AMBIENT, (0.2, 0.2, 0.2, 1))
    glLightfv(GL_LIGHT0, GL_DIFFUSE, (0.8, 0.8, 0.8, 1))

    glEnable(GL_TEXTURE_2D)

    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(45, (DISPLAY_SIZE[0] / DISPLAY_SIZE[1]), 0.1, 100.0)

    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()


def menu_load_texture(filename):
    try:
        filepath = os.path.join(os.path.dirname(__file__), "textures", filename)

        image = pygame.image.load(filepath).convert_alpha()
        image = pygame.transform.flip(image, False, True)

        texture_data = pygame.image.tostring(image, "RGBA", 1)
        width, height = image.get_size()

        texture_id = glGenTextures(1)

        if isinstance(texture_id, (list, tuple, np.ndarray)):
            texture_id = int(texture_id[0])
        else:
            texture_id = int(texture_id)

        glBindTexture(GL_TEXTURE_2D, texture_id)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, texture_data)

        print(f"Textura '{filename}' carregada com sucesso.")
        return texture_id
    except pygame.error as e:
        print(f"AVISO: Não foi possível carregar a textura '{filename}': {e}")
        return None
    except FileNotFoundError:
        print(f"AVISO: O arquivo de textura '{filename}' não foi encontrado em '{filepath}'.")
        return None


def menu_generate_meteor():
    x = random.uniform(-15.0, 15.0)
    y = random.uniform(-15.0, 15.0)
    z = random.uniform(-40.0, -30.0)

    speed = random.uniform(0.1, 0.3)
    size = random.uniform(0.05, 0.15)

    return [x, y, z, speed, size]


def menu_draw_scene(globe_texture_id, stars_texture_id, meteor_texture_id, angle, meteors):
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

    if stars_texture_id:
        glLoadIdentity()
        glTranslatef(0.0, 0.0, -15.0)

        glBindTexture(GL_TEXTURE_2D, stars_texture_id)
        glDisable(GL_LIGHTING)
        glColor3f(1.0, 1.0, 1.0)
        glDisable(GL_DEPTH_TEST)

        glBegin(GL_QUADS)
        glTexCoord2f(0.0, 0.0); glVertex3f(-10.0, -10.0, 0.0)
        glTexCoord2f(1.0, 0.0); glVertex3f(10.0, -10.0, 0.0)
        glTexCoord2f(1.0, 1.0); glVertex3f(10.0, 10.0, 0.0)
        glTexCoord2f(0.0, 1.0); glVertex3f(-10.0, 10.0, 0.0)
        glEnd()

        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)

    glLoadIdentity()

    glTranslatef(-0.2, -0.2, -5.0)

    glRotatef(angle, 0, 1, 0)

    glRotatef(90.0, 1.0, 0.0, 0.0)

    if globe_texture_id:
        glBindTexture(GL_TEXTURE_2D, globe_texture_id)
        glEnable(GL_COLOR_MATERIAL)
        glColor3f(1.0, 1.0, 1.0)
    else:
        glDisable(GL_TEXTURE_2D)
        glColor3f(0.1, 0.2, 0.9)

    quadric_earth = gluNewQuadric()
    gluQuadricNormals(quadric_earth, GLU_SMOOTH)
    gluQuadricTexture(quadric_earth, GL_TRUE)

    gluSphere(quadric_earth, 1.0, 32, 32)
    gluDeleteQuadric(quadric_earth)

    if globe_texture_id:
        glDisable(GL_COLOR_MATERIAL)
        glEnable(GL_TEXTURE_2D)

    glLoadIdentity()

    quadric_meteor = gluNewQuadric()
    gluQuadricNormals(quadric_meteor, GLU_SMOOTH)

    if meteor_texture_id:
        glEnable(GL_TEXTURE_2D)
        gluQuadricTexture(quadric_meteor, GL_TRUE)
        glBindTexture(GL_TEXTURE_2D, meteor_texture_id)
        glDisable(GL_LIGHTING)
        glColor3f(1.0, 1.0, 1.0)
    else:
        glDisable(GL_TEXTURE_2D)
        glEnable(GL_LIGHTING)
        glColor3f(*MENU_METEOR_COLOR)

    for x, y, z, _, size in meteors:
        glPushMatrix()
        glTranslatef(x, y, z)

        gluSphere(quadric_meteor, size, 5, 5)

        glPopMatrix()

    gluDeleteQuadric(quadric_meteor)

    glEnable(GL_LIGHTING)
    glEnable(GL_TEXTURE_2D)


def draw_centered_text_2d(screen, font, text, y_offset, color=(255, 255, 255), outline_color=None):
    text_surface = font.render(text, True, color)
    text_rect = text_surface.get_rect(center=(
        DISPLAY_SIZE[0] // 2,
        DISPLAY_SIZE[1] // 2 + y_offset
    ))

    if outline_color is not None:
        outline_surface = font.render(text, True, outline_color)
        outline_offset = 2

        for dx in [-outline_offset, 0, outline_offset]:
            for dy in [-outline_offset, 0, outline_offset]:
                if dx != 0 or dy != 0:
                    screen.blit(outline_surface, (text_rect.x + dx, text_rect.y + dy))

    screen.blit(text_surface, text_rect)


def run_menu():
    screen = pygame.display.get_surface()

    menu_init_gl()

    global menu_globe_texture_id, menu_stars_texture_id, menu_meteor_texture_id
    if menu_globe_texture_id is None:
        menu_globe_texture_id = menu_load_texture("earth.jpg")
    if menu_stars_texture_id is None:
        menu_stars_texture_id = menu_load_texture("stars.jpg")
    if menu_meteor_texture_id is None:
        menu_meteor_texture_id = menu_load_texture("meteor.jpg")

    globe_texture = menu_globe_texture_id
    stars_texture = menu_stars_texture_id
    meteor_texture = menu_meteor_texture_id

    meteors = [menu_generate_meteor() for _ in range(10)]

    try:
        pygame.font.init()
        font_title = pygame.font.Font(None, 120)
        font_menu = pygame.font.Font(None, 48)
        font_small = pygame.font.Font(None, 24)
    except Exception:
        font_title = pygame.font.SysFont('Arial', 80)
        font_menu = pygame.font.SysFont('Arial', 48)
        font_small = pygame.font.SysFont('Arial', 24)

    rotation_angle = 0.0
    menu_options = ["INICIAR JOGO", "SAIR"]
    selected_option = 0

    menu_surface = pygame.Surface(DISPLAY_SIZE, pygame.SRCALPHA)

    clock = pygame.time.Clock()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "QUIT"

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return "QUIT"

                if event.key == pygame.K_UP:
                    selected_option = (selected_option - 1) % len(menu_options)
                if event.key == pygame.K_DOWN:
                    selected_option = (selected_option + 1) % len(menu_options)

                if event.key == pygame.K_RETURN:
                    if menu_options[selected_option] == "INICIAR JOGO":
                        return "GAME"
                    elif menu_options[selected_option] == "SAIR":
                        return "QUIT"

        rotation_angle += 0.25
        if rotation_angle > 360:
            rotation_angle -= 360

        new_meteors = []
        for x, y, z, speed, size in meteors:
            z += speed

            if z < -4.0:
                new_meteors.append([x, y, z, speed, size])

        meteors = new_meteors

        if random.random() < 0.1 and len(meteors) < 50:
            meteors.append(menu_generate_meteor())

        menu_draw_scene(globe_texture, stars_texture, meteor_texture, rotation_angle, meteors)

        menu_surface.fill((0, 0, 0, 0))
        s = pygame.Surface(DISPLAY_SIZE, pygame.SRCALPHA)
        s.fill((0, 0, 0, 150))
        menu_surface.blit(s, (0, 0))

        draw_centered_text_2d(menu_surface, font_title, "GUERRA NAS ESFERAS", -150, BLACK, outline_color=YELLOW)

        y_offset_start = 50
        y_spacing = 70
        for i, option in enumerate(menu_options):
            color = YELLOW if i == selected_option else GRAY
            draw_centered_text_2d(menu_surface, font_menu, option, y_offset_start + i * y_spacing, color)

        draw_centered_text_2d(menu_surface, font_small,
                               "Use as setas para navegar e ENTER para selecionar",
                               250, GRAY)

        glDisable(GL_DEPTH_TEST)

        texture_data = pygame.image.tostring(menu_surface, "RGBA", True)
        width, height = menu_surface.get_size()

        gl_texture = glGenTextures(1)

        if isinstance(gl_texture, (list, tuple, np.ndarray)):
            gl_texture_id = int(gl_texture[0])
        else:
            gl_texture_id = int(gl_texture)

        glBindTexture(GL_TEXTURE_2D, gl_texture_id)

        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, texture_data)

        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        gluOrtho2D(0, width, 0, height)

        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()

        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glDisable(GL_LIGHTING)
        glColor3f(1.0, 1.0, 1.0)

        glBegin(GL_QUADS)
        glTexCoord2f(0, 0); glVertex2f(0, 0)
        glTexCoord2f(1, 0); glVertex2f(width, 0)
        glTexCoord2f(1, 1); glVertex2f(width, height)
        glTexCoord2f(0, 1); glVertex2f(0, height)
        glEnd()

        glEnable(GL_LIGHTING)
        glDisable(GL_BLEND)

        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()

        glDeleteTextures([gl_texture_id])
        glEnable(GL_DEPTH_TEST)

        pygame.display.flip()
        clock.tick(60)

skybox_texture_id = None
meteor_texture_id = None
earth_texture_id = None
earth_rotation_angle = 0.0

MAX_GAME_TIME_SECONDS = 61
game_timer_ms = MAX_GAME_TIME_SECONDS * 1000

EARTH_SURFACE_Y = -30.0

GRID_LIMIT = 20.0

crawl_title = "GUERRA NAS ESFERAS"

crawl_text = [
    "EPISÓDIO I: AMEAÇA METEÓRICA",
    "",
    "A Terra está sob AMEAÇA! Chuvas de meteoros atingem o planeta,",
    "e a humanidade corre risco. SUA MISSÃO, como defensor espacial,",
    "é interceptar os meteoros antes que eles atinjam o solo.",
    "",
    "Cada interceptação BEM-SUCEDIDA é crucial para a defesa da TERRA.",
    "Contudo, cada meteoro que atinge a superfície, aproxima o fim.",
    "",
    "A missão FALHA se a a Terra sofrer muitos ataques.",
    "Proteja a Terra até que o TEMPO acabe!",
    "",
    "COMANDOS:",
    "W, A, S, D: Movimento",
    "SHIFT ESQUERDO: Corrida (Usa Estamina)",
    "Mouse: Olhar/Girar a Câmera",
    "ESPAÇO: Ativar/DESATIVAR Sabre",
    "ESC: Sair do Jogo",
    "",
    "PREPARE-SE PARA A DEFESA!",
    "",
]
crawl_y_offset = 0.0
crawl_speed = 0.5

title_fade_timer = 0
TITLE_STILL_DURATION = 240
TITLE_FADE_DURATION = 90


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
        self.stamina_recover_rate = 0.75

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

        new_position[1] = 1.8

        new_position[0] = np.clip(new_position[0], -GRID_LIMIT, GRID_LIMIT)
        new_position[2] = np.clip(new_position[2], -GRID_LIMIT, GRID_LIMIT)

        self.position = new_position

    def update_view(self):
        direction = self.get_direction()
        look_at = self.position + direction

        gluLookAt(
            self.position[0], self.position[1], self.position[2],
            look_at[0], look_at[1], look_at[2],
            self.up[0], self.up[1], self.up[2]
        )


class DroppingObject:
    def __init__(self):
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

            if self.y <= EARTH_SURFACE_Y:
                self.active = False

    def draw(self):
        global meteor_texture_id

        if self.active or self.y > EARTH_SURFACE_Y:
            glPushMatrix()
            glTranslatef(self.x, self.y, self.z)

            glRotatef(self.rotation_angle, self.rotation_axis[0], self.rotation_axis[1], self.rotation_axis[2])

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
            (meteor_x - player_x) ** 2 +
            (meteor_y - player_y) ** 2 +
            (meteor_z - player_z) ** 2
        )

        collision_radius = self.size + 2

        if distance_3d < collision_radius:
            self.active = False
            return True

        return False


def game_load_texture(filename):
    filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
    try:
        img = Image.open(filepath)
        if img.mode != 'RGBA':
            img = img.convert('RGBA')

        img_data = img.tobytes("raw", "RGBA")
        width, height = img.size
        img.close()
    except FileNotFoundError:
        print(f"ERRO: Arquivo de textura '{filepath}' não encontrado. O objeto será desenhado sem textura.")
        return 0
    except Exception as e:
        print(f"ERRO ao carregar a textura '{filepath}': {e}")
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

    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)

    glBegin(GL_QUADS)

    glTexCoord2f(0.0, 0.0); glVertex3f(-s, -s, s)
    glTexCoord2f(1.0, 0.0); glVertex3f(s, -s, s)
    glTexCoord2f(1.0, 1.0); glVertex3f(s, s, s)
    glTexCoord2f(0.0, 1.0); glVertex3f(-s, s, s)

    glTexCoord2f(1.0, 0.0); glVertex3f(-s, -s, -s)
    glTexCoord2f(1.0, 1.0); glVertex3f(-s, s, -s)
    glTexCoord2f(0.0, 1.0); glVertex3f(s, s, -s)
    glTexCoord2f(0.0, 0.0); glVertex3f(s, -s, -s)

    glTexCoord2f(0.0, 1.0); glVertex3f(-s, s, -s)
    glTexCoord2f(0.0, 0.0); glVertex3f(-s, s, s)
    glTexCoord2f(1.0, 0.0); glVertex3f(s, s, s)
    glTexCoord2f(1.0, 1.0); glVertex3f(s, s, -s)

    glTexCoord2f(0.0, 0.0); glVertex3f(-s, -s, -s)
    glTexCoord2f(1.0, 0.0); glVertex3f(s, -s, -s)
    glTexCoord2f(1.0, 1.0); glVertex3f(s, -s, s)
    glTexCoord2f(0.0, 1.0); glVertex3f(-s, -s, s)

    glTexCoord2f(1.0, 0.0); glVertex3f(s, -s, -s)
    glTexCoord2f(1.0, 1.0); glVertex3f(s, s, -s)
    glTexCoord2f(0.0, 1.0); glVertex3f(s, s, s)
    glTexCoord2f(0.0, 0.0); glVertex3f(s, -s, s)

    glTexCoord2f(0.0, 0.0); glVertex3f(-s, -s, -s)
    glTexCoord2f(1.0, 0.0); glVertex3f(-s, -s, s)
    glTexCoord2f(1.0, 1.0); glVertex3f(-s, s, s)
    glTexCoord2f(0.0, 1.0); glVertex3f(-s, s, -s)

    glEnd()

    glBindTexture(GL_TEXTURE_2D, 0)
    glDisable(GL_TEXTURE_2D)
    glEnable(GL_DEPTH_TEST)
    glPopMatrix()

    if texture_id:
        glBindTexture(GL_TEXTURE_2D, texture_id)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
        glBindTexture(GL_TEXTURE_2D, 0)


def draw_ground():
    pass


def draw_half_sphere():
    global earth_texture_id, earth_rotation_angle

    center_y = -130.0
    radius = 100.0

    glPushMatrix()
    glTranslatef(0.0, center_y, 0.0)

    glRotatef(earth_rotation_angle, 0.0, 1.0, 0.0)
    glRotatef(90.0, 1.0, 0.0, 0.0)

    if earth_texture_id:
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, earth_texture_id)
        glColor3f(1.0, 1.0, 1.0)
    else:
        glColor3f(0.0, 0.0, 0.5)

    quadric = gluNewQuadric()
    gluQuadricDrawStyle(quadric, GLU_FILL)
    gluQuadricTexture(quadric, GL_TRUE)

    gluSphere(quadric, radius, 30, 30)

    gluDeleteQuadric(quadric)

    if earth_texture_id:
        glBindTexture(GL_TEXTURE_2D, 0)
        glDisable(GL_TEXTURE_2D)

    glPopMatrix()


def game_draw_scene(dropping_objects, skybox_id):
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

    glMatrixMode(GL_MODELVIEW)

    if skybox_id:
        draw_skybox(skybox_id)

    draw_half_sphere()
    draw_ground()

    for obj in dropping_objects:
        obj.draw()


def setup_2d_projection(display_size):
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
    glDisable(GL_BLEND)
    glEnable(GL_DEPTH_TEST)
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)


def draw_text_2d(text, x, y, font, color=(255, 255, 255, 255)):
    setup_2d_projection(pygame.display.get_surface().get_size())

    text_surface = font.render(text, True, color[:3])
    text_data = pygame.image.tostring(text_surface, "RGBA", True)

    width, height = pygame.display.get_surface().get_size()

    glColor4ub(*color)

    glRasterPos2i(x, height - y - text_surface.get_height())

    glDrawPixels(text_surface.get_width(), text_surface.get_height(),
                 GL_RGBA, GL_UNSIGNED_BYTE, text_data)

    glColor4f(1.0, 1.0, 1.0, 1.0)

    restore_3d_projection()


def draw_centered_text(text, font, display_size, y_offset=0, color=(255, 255, 255, 255)):
    setup_2d_projection(display_size)

    width, height = display_size
    text_surface = font.render(text, True, color[:3])
    text_w, text_h = text_surface.get_size()

    x = (width - text_w) // 2
    y_center = (height - text_h) // 2 + y_offset

    text_data = pygame.image.tostring(text_surface, "RGBA", True)

    glColor4ub(*color)

    glRasterPos2i(x, height - y_center - text_h)

    glDrawPixels(text_w, text_h, GL_RGBA, GL_UNSIGNED_BYTE, text_data)

    glColor4f(1.0, 1.0, 1.0, 1.0)

    restore_3d_projection()


def draw_outlined_text(text, font, display_size, y_offset=0, fill_color=(0, 0, 0, 0), outline_color=(255, 210, 0, 255), outline_size=3):
    setup_2d_projection(display_size)
    width, height = display_size

    outline_surface = font.render(text, True, outline_color[:3])
    outline_w, outline_h = outline_surface.get_size()

    base_x = (width - outline_w) // 2
    base_y = (height - outline_h) // 2 + y_offset

    glColor4ub(*outline_color)
    outline_data = pygame.image.tostring(outline_surface, "RGBA", True)

    offsets = [
        (-outline_size, -outline_size), (outline_size, -outline_size),
        (-outline_size, outline_size), (outline_size, outline_size),
        (0, -outline_size), (0, outline_size),
        (-outline_size, 0), (outline_size, 0)
    ]

    for dx, dy in offsets:
        raster_y = height - (base_y + dy) - outline_h
        glRasterPos2i(base_x + dx, raster_y)
        glDrawPixels(outline_w, outline_h, GL_RGBA, GL_UNSIGNED_BYTE, outline_data)

    fill_surface = font.render(text, True, fill_color[:3])

    glColor4ub(*fill_color)
    fill_data = pygame.image.tostring(fill_surface, "RGBA", True)

    raster_y = height - base_y - outline_h
    glRasterPos2i(base_x, raster_y)

    glDrawPixels(outline_w, outline_h, GL_RGBA, GL_UNSIGNED_BYTE, fill_data)

    glColor4f(1.0, 1.0, 1.0, 1.0)

    restore_3d_projection()


def draw_star_wars_crawl(font, display_size):
    global crawl_y_offset, crawl_text, crawl_speed

    setup_2d_projection(display_size)
    width, height = display_size

    line_spacing = 40
    crawl_color = (255, 210, 0, 255)

    num_lines = len(crawl_text)
    total_text_height = num_lines * line_spacing

    start_base_y = -total_text_height

    if crawl_y_offset > total_text_height + height:
        restore_3d_projection()
        return True

    for i, line in enumerate(crawl_text):
        glColor4ub(*crawl_color)

        text_surface = font.render(line, True, crawl_color[:3])
        text_w, text_h = text_surface.get_size()

        inverted_index = num_lines - 1 - i

        line_y = start_base_y + (inverted_index * line_spacing) + crawl_y_offset

        if line_y < -text_h or line_y > height + text_h:
            continue

        x = (width - text_w) // 2

        glRasterPos2i(x, int(line_y))

        text_data = pygame.image.tostring(text_surface, "RGBA", True)
        glDrawPixels(text_w, text_h, GL_RGBA, GL_UNSIGNED_BYTE, text_data)

    glColor4f(1.0, 1.0, 1.0, 1.0)

    crawl_y_offset += crawl_speed

    restore_3d_projection()
    return False


def draw_health_bar(current, max_health, display_size):
    setup_2d_projection(display_size)

    bar_width_max = 1000
    bar_height = 20
    bar_padding_top = 30

    width, height = display_size

    bar_x = (width - bar_width_max) // 2

    bar_y = height - bar_padding_top - bar_height

    health_ratio = current / max_health
    bar_width_current = bar_width_max * max(0.0, health_ratio)

    glColor4f(0.2, 0.2, 0.2, 0.8)
    glBegin(GL_QUADS)
    glVertex2f(bar_x, bar_y)
    glVertex2f(bar_x + bar_width_max, bar_y)
    glVertex2f(bar_x + bar_width_max, bar_y + bar_height)
    glVertex2f(bar_x, bar_y + bar_height)
    glEnd()

    if health_ratio > 0:
        if health_ratio >= 0.5:
            r = (1.0 - health_ratio) * 2.0
            g = 1.0
        else:
            r = 1.0
            g = health_ratio * 2.0
        b = 0.0

        glColor4f(r, g, b, 0.9)

        glBegin(GL_QUADS)
        glVertex2f(bar_x, bar_y)
        glVertex2f(bar_x + bar_width_current, bar_y)
        glVertex2f(bar_x + bar_width_current, bar_y + bar_height)
        glVertex2f(bar_x, bar_y + bar_height)
        glEnd()

    glColor4f(1.0, 1.0, 1.0, 1.0)
    glLineWidth(2.0)
    glBegin(GL_LINE_LOOP)
    glVertex2f(bar_x, bar_y)
    glVertex2f(bar_x + bar_width_max, bar_y)
    glVertex2f(bar_x + bar_width_max, bar_y + bar_height)
    glVertex2f(bar_x, bar_y + bar_height)
    glEnd()

    health_text = "TERRA"
    font = pygame.font.Font(None, 24)
    text_surface = font.render(health_text, True, (255, 255, 255))
    text_w, text_h = text_surface.get_size()

    text_x = bar_x + (bar_width_max - text_w) // 2
    text_y = bar_y - text_h - 5

    text_data = pygame.image.tostring(text_surface, "RGBA", True)

    glColor4f(1.0, 1.0, 1.0, 1.0)
    glRasterPos2i(text_x, int(text_y))
    glDrawPixels(text_w, text_h, GL_RGBA, GL_UNSIGNED_BYTE, text_data)

    restore_3d_projection()


def draw_stamina_bar(current, max_stamina, display_size):
    setup_2d_projection(display_size)

    bar_width_max = 200
    bar_height = 15
    bar_padding_bottom = 30
    bar_padding_left = 30

    bar_x = bar_padding_left
    bar_y = bar_padding_bottom

    stamina_ratio = current / max_stamina
    bar_width_current = bar_width_max * stamina_ratio

    glColor4f(0.2, 0.2, 0.2, 0.8)
    glBegin(GL_QUADS)
    glVertex2f(bar_x, bar_y)
    glVertex2f(bar_x + bar_width_max, bar_y)
    glVertex2f(bar_x + bar_width_max, bar_y + bar_height)
    glVertex2f(bar_x, bar_y + bar_height)
    glEnd()

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


def game_init_gl(display, fov):
    """Reseta o estado da OpenGL deixado pelo menu (lighting/texturas
    ativadas) para o estado que o jogo espera (lighting desativado,
    controle manual de texturas por função)."""
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(fov, (display[0] / display[1]), 0.1, 1000.0)

    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    glDisable(GL_LIGHTING)
    glDisable(GL_TEXTURE_2D)
    glEnable(GL_DEPTH_TEST)
    glClearColor(0.0, 0.0, 0.0, 1.0)


def run_game():
    """
    Laço principal do jogo. Roda dentro do mesmo processo/janela do menu.
    Retorna "MENU" se o jogador apertar ESC na tela de GAME OVER/VITÓRIA
    (volta ao menu), ou "QUIT" se apertar ESC durante o jogo ou fechar
    a janela (encerra o programa).
    """
    global skybox_texture_id, meteor_texture_id, earth_texture_id, earth_rotation_angle
    global crawl_y_offset, wilhelm_scream_sound
    global title_fade_timer
    global game_timer_ms

    earth_rotation_angle = 0.0
    crawl_y_offset = 0.0
    title_fade_timer = 0
    game_timer_ms = MAX_GAME_TIME_SECONDS * 1000

    display = DISPLAY_SIZE

    pygame.mouse.set_visible(True)
    pygame.event.set_grab(False)

    cam = Camera()

    if skybox_texture_id is None:
        skybox_texture_id = game_load_texture("textures/stars.jpg")
    if meteor_texture_id is None:
        meteor_texture_id = game_load_texture("textures/meteor.jpg")
    if earth_texture_id is None:
        earth_texture_id = game_load_texture("textures/earth.jpg")

    game_init_gl(display, cam.fov)

    MAX_HEALTH = 100
    score = 100

    try:
        pygame.font.init()
        font = pygame.font.Font(None, 36)
        font_large = pygame.font.Font(None, 120)
        font_crawl = pygame.font.Font(None, 48)
    except Exception:
        font = pygame.font.SysFont('Arial', 36)
        font_large = pygame.font.SysFont('Arial', 120)
        font_crawl = pygame.font.SysFont('Arial', 48)

    if wilhelm_scream_sound is None:
        try:
            wilhelm_scream_sound = pygame.mixer.Sound(WILHELM_SCREAM_PATH)
            print(f"Som '{WILHELM_SCREAM_PATH}' carregado com sucesso.")
        except pygame.error as e:
            print(f"AVISO: ERRO ao carregar o som do Game Over: {e}. Verifique se o arquivo '{WILHELM_SCREAM_PATH}' existe.")
            wilhelm_scream_sound = None

    dropping_objects = []

    object_spawn_timer = 0
    SPAWN_INTERVAL = 60

    game_state = "TITLE_SCREEN"

    clock = pygame.time.Clock()

    EARTH_ROTATION_SPEED = 0.1

    last_time = pygame.time.get_ticks()

    try:
        pygame.mixer.music.load(STAR_WARS_THEME_PATH)
        pygame.mixer.music.play(-1)
        print(f"Música '{STAR_WARS_THEME_PATH}' iniciada.")
    except pygame.error as e:
        print(f"ERRO ao carregar ou tocar a música: {e}. Verifique se o arquivo de áudio está correto.")

    while True:
        current_time = pygame.time.get_ticks()
        delta_time_ms = current_time - last_time
        last_time = current_time

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "QUIT"
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if game_state == "GAME_OVER" or game_state == "WIN":
                        pygame.mixer.music.stop()
                        return "MENU"
                    else:
                        return "QUIT"

                if (game_state == "TITLE_SCREEN" or game_state == "INTRO") and event.key == pygame.K_SPACE:
                    game_state = "RUNNING"
                    pygame.mouse.set_visible(False)
                    pygame.event.set_grab(True)
                    pygame.mixer.music.stop()

                if game_state == "RUNNING" and event.key == pygame.K_SPACE:
                    toggle_saber()

            if game_state == "RUNNING":
                if event.type == pygame.MOUSEMOTION:
                    dx, dy = event.rel
                    cam.process_mouse_movement(dx, -dy)

        keys = pygame.key.get_pressed()

        if game_state == "TITLE_SCREEN":
            glLoadIdentity()
            cam.update_view()
            game_draw_scene(dropping_objects, skybox_texture_id)

            if title_fade_timer < TITLE_STILL_DURATION:
                alpha = 1.0
            elif title_fade_timer < TITLE_STILL_DURATION + TITLE_FADE_DURATION:
                fade_time = title_fade_timer - TITLE_STILL_DURATION
                alpha = 1.0 - (fade_time / TITLE_FADE_DURATION)
            else:
                game_state = "INTRO"
                title_fade_timer = 0

            title_fade_timer += 1

            alpha = max(0.0, min(1.0, alpha))

            outline_color = (255, 210, 0, int(alpha * 255))
            fill_color = (0, 0, 0, int(alpha * 255))

            draw_outlined_text(
                crawl_title,
                font_large,
                display,
                y_offset=-50,
                fill_color=fill_color,
                outline_color=outline_color,
                outline_size=3
            )

            draw_centered_text("Pressione ESPAÇO para Pular", font, display, y_offset=300, color=(150, 150, 150, 255))

        elif game_state == "INTRO":
            glLoadIdentity()
            cam.update_view()
            game_draw_scene(dropping_objects, skybox_texture_id)

            intro_finished = draw_star_wars_crawl(font_crawl, display)

            if intro_finished:
                game_state = "RUNNING"
                pygame.mouse.set_visible(False)
                pygame.event.set_grab(True)
                pygame.mixer.music.stop()

            draw_centered_text("Pressione ESPAÇO para Pular", font, display, y_offset=300, color=(150, 150, 150, 255))

        elif game_state == "RUNNING":
            if game_timer_ms > 0:
                game_timer_ms -= delta_time_ms
                if game_timer_ms < 0:
                    game_timer_ms = 0

            if game_timer_ms <= 0:
                if game_state != "WIN":
                    game_state = "WIN"
                pygame.mouse.set_visible(True)
                pygame.event.set_grab(False)
                pygame.mixer.music.stop()

            cam.update_movement(keys)
            glLoadIdentity()
            cam.update_view()

            earth_rotation_angle += EARTH_ROTATION_SPEED
            if earth_rotation_angle >= 360.0:
                earth_rotation_angle -= 360.0

            for obj in list(dropping_objects):
                obj.update()

                if obj.check_collision(cam.position):
                    dropping_objects.remove(obj)
                    continue

                if not obj.active and not obj.has_hit_earth:
                    score -= 5
                    obj.has_hit_earth = True

                if not obj.active and obj.has_hit_earth:
                    dropping_objects.remove(obj)

            object_spawn_timer += 1
            if object_spawn_timer >= SPAWN_INTERVAL:
                dropping_objects.append(DroppingObject())
                object_spawn_timer = 0

            if score <= 0:
                game_state = "GAME_OVER"
                pygame.mouse.set_visible(True)
                pygame.event.set_grab(False)
                pygame.mixer.music.stop()
                if wilhelm_scream_sound:
                    wilhelm_scream_sound.play()

            game_draw_scene(dropping_objects, skybox_texture_id)

            draw_lightsaber(cam)

            draw_health_bar(score, MAX_HEALTH, display)

            draw_stamina_bar(cam.current_stamina, cam.max_stamina, display)

            time_remaining_ms = max(0, game_timer_ms)
            total_seconds = time_remaining_ms // 1000
            minutes = total_seconds // 60
            seconds = total_seconds % 60

            time_text = f"TEMPO RESTANTE: {minutes:02}:{seconds:02}"

            text_width, text_height = font.size(time_text)
            timer_x = display[0] - text_width - 10
            timer_y = display[1] - text_height - 10
            draw_text_2d(time_text, timer_x, timer_y, font)

        elif game_state == "GAME_OVER" or game_state == "WIN":
            glLoadIdentity()
            cam.update_view()
            game_draw_scene(dropping_objects, skybox_texture_id)

            setup_2d_projection(display)

            glColor4f(0.0, 0.0, 0.0, 0.8)
            glBegin(GL_QUADS)
            glVertex2f(0, 0); glVertex2f(display[0], 0); glVertex2f(display[0], display[1]); glVertex2f(0, display[1])
            glEnd()

            restore_3d_projection()

            if game_state == "GAME_OVER":
                draw_centered_text("DERROTA!", font_large, display, y_offset=-50, color=(255, 0, 0, 255))
                draw_centered_text("Não há mais vida na Terra.", font, display, y_offset=10, color=(255, 255, 255, 255))
                draw_centered_text("Pressione ESC para voltar ao menu", font, display, y_offset=60, color=(150, 150, 150, 255))
            else:
                draw_centered_text("VITÓRIA!", font_large, display, y_offset=-70, color=(0, 255, 0, 255))
                draw_centered_text("Você defendeu a Terra!", font, display, y_offset=10, color=(255, 255, 255, 255))
                draw_centered_text("Pressione ESC para voltar ao menu", font, display, y_offset=130, color=(150, 150, 150, 255))

        pygame.display.flip()
        clock.tick(60)


def main():
    pygame.init()
    pygame.mixer.init()
    _load_saber_sounds()

    pygame.display.set_mode(DISPLAY_SIZE, DOUBLEBUF | OPENGL)
    pygame.display.set_caption("Guerra nas Esferas")

    state = "MENU"
    while state != "QUIT":
        if state == "MENU":
            state = run_menu()
        elif state == "GAME":
            state = run_game()
        else:
            state = "QUIT"

    pygame.mixer.quit()
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
