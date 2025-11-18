import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import sys
import os
import random

try:
    import numpy as np
except ImportError:
    print("AVISO: O pacote 'numpy' não foi encontrado. O PyOpenGL pode ter problemas.")
    np = None

try:
    from game import main as run_game_main
except ImportError:
    print("AVISO: O arquivo 'game.py' (com a função main) não foi encontrado.")
    print("O menu será exibido, mas a opção 'INICIAR JOGO' não funcionará.")
    run_game_main = None

DISPLAY_SIZE = (1280, 720)

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (180, 180, 180)
YELLOW = (255, 255, 0) 

rotation_angle = 0.0
globe_texture = None 
stars_texture = None 
meteor_texture = None 
meteors = [] 
METEOR_COLOR = (0.8, 0.4, 0.1) 

def init_gl():
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
    
def load_texture(filename):
    global np
    try:
        filepath = os.path.join(os.path.dirname(__file__), "textures", filename)
        
        image = pygame.image.load(filepath).convert_alpha()
        image = pygame.transform.flip(image, False, True) 
        
        texture_data = pygame.image.tostring(image, "RGBA", 1) 
        width, height = image.get_size()
        
        texture_id = glGenTextures(1)
        
        if np is not None and isinstance(texture_id, (list, tuple, np.ndarray)):
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

def generate_meteor():
    x = random.uniform(-15.0, 15.0)
    y = random.uniform(-15.0, 15.0)
    z = random.uniform(-40.0, -30.0) 
    
    speed = random.uniform(0.1, 0.3) 
    
    size = random.uniform(0.05, 0.15)
    
    return [x, y, z, speed, size]


def draw_scene(globe_texture_id, stars_texture_id, angle, meteors):
    
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
        glTexCoord2f(1.0, 0.0); glVertex3f( 10.0, -10.0, 0.0) 
        glTexCoord2f(1.0, 1.0); glVertex3f( 10.0,  10.0, 0.0) 
        glTexCoord2f(0.0, 1.0); glVertex3f(-10.0,  10.0, 0.0) 
        glEnd()
        
        glEnable(GL_DEPTH_TEST) 
        glEnable(GL_LIGHTING)
    
    glLoadIdentity()
    
    glTranslatef(-0.2, -0.2, -5.0) 
    
    glRotatef(angle, 0, 1, 0) 
    
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

    if meteor_texture:
        glEnable(GL_TEXTURE_2D)
        gluQuadricTexture(quadric_meteor, GL_TRUE)
        glBindTexture(GL_TEXTURE_2D, meteor_texture)
        glDisable(GL_LIGHTING) 
        glColor3f(1.0, 1.0, 1.0) 
    else:
        glDisable(GL_TEXTURE_2D)
        glEnable(GL_LIGHTING)
        glColor3f(*METEOR_COLOR)
    
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


def menu_main():
    
    global rotation_angle, globe_texture, stars_texture, meteor_texture, np, meteors
    
    pygame.init()
    
    screen = pygame.display.set_mode(DISPLAY_SIZE, DOUBLEBUF | OPENGL)
    pygame.display.set_caption("Catch the Meteors - Menu")
    
    init_gl()
    
    globe_texture = load_texture("earth.jpg") 
    stars_texture = load_texture("stars.jpg") 
    meteor_texture = load_texture("meteor.jpg")
    
    meteors = [generate_meteor() for _ in range(10)] 
    
    try:
        pygame.font.init()
        font_title = pygame.font.Font(None, 120)
        font_menu = pygame.font.Font(None, 48)
        font_small = pygame.font.Font(None, 24)
    except:
        font_title = pygame.font.SysFont('Arial', 80)
        font_menu = pygame.font.SysFont('Arial', 48)
        font_small = pygame.font.SysFont('Arial', 24)

    running = True
    clock = pygame.time.Clock()
    
    menu_options = ["INICIAR JOGO", "SAIR"] 
    selected_option = 0
    
    menu_surface = pygame.Surface(DISPLAY_SIZE, pygame.SRCALPHA)
    
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                
                if event.key == pygame.K_UP:
                    selected_option = (selected_option - 1) % len(menu_options)
                if event.key == pygame.K_DOWN:
                    selected_option = (selected_option + 1) % len(menu_options)
                    
                if event.key == pygame.K_RETURN:
                    if menu_options[selected_option] == "INICIAR JOGO":
                        pygame.quit()
                        if run_game_main:
                            run_game_main()
                        return 
                        
                    elif menu_options[selected_option] == "SAIR":
                        running = False
                        
        
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
            meteors.append(generate_meteor())
            
        draw_scene(globe_texture, stars_texture, rotation_angle, meteors) 
        
        
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
        
        if np is not None and isinstance(gl_texture, (list, tuple, np.ndarray)):
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

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    menu_main()