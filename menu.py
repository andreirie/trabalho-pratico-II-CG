import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import sys
import os
import random # Importação necessária para a chuva de meteoros

try:
    # Tenta importar o NumPy, necessário para algumas acelerações do PyOpenGL
    import numpy as np
except ImportError:
    print("AVISO: O pacote 'numpy' não foi encontrado. O PyOpenGL pode ter problemas.")
    np = None

try:
    # Tenta importar o jogo principal (assumindo que está em 'game.py')
    from game import main as run_game_main
except ImportError:
    print("AVISO: O arquivo 'game.py' (com a função main) não foi encontrado.")
    print("O menu será exibido, mas a opção 'INICIAR JOGO' não funcionará.")
    run_game_main = None

# --- Configurações ---
DISPLAY_SIZE = (1280, 720)

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (180, 180, 180)
YELLOW = (255, 255, 0) 

# Variáveis globais para 3D
rotation_angle = 0.0
globe_texture = None 
stars_texture = None 
meteor_texture = None # Novo: Textura do meteoro
meteors = [] # Lista para armazenar os meteoros
METEOR_COLOR = (0.8, 0.4, 0.1) # Cor marrom-avermelhada para os meteoros (fallback)

# ----------------------------------------------------------------------
## Funções de Suporte 3D
# ----------------------------------------------------------------------

def init_gl():
    """Configurações iniciais do OpenGL."""
    glClearColor(0.0, 0.0, 0.0, 0.0) 
    glEnable(GL_DEPTH_TEST) 
    glEnable(GL_LIGHTING) 
    glEnable(GL_LIGHT0) 
    # Luz direcional vindo da frente/cima
    glLightfv(GL_LIGHT0, GL_POSITION, (1, 1, 1, 0)) 
    glLightfv(GL_LIGHT0, GL_AMBIENT, (0.2, 0.2, 0.2, 1))
    glLightfv(GL_LIGHT0, GL_DIFFUSE, (0.8, 0.8, 0.8, 1))
    
    glEnable(GL_TEXTURE_2D)
    
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    # Aumenta o far clipping plane para que os meteoros distantes sejam visíveis
    gluPerspective(45, (DISPLAY_SIZE[0] / DISPLAY_SIZE[1]), 0.1, 100.0) 
    
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    
def load_texture(filename):
    """Carrega uma textura do Pygame e a converte para o formato OpenGL."""
    global np
    try:
        # Tenta carregar de 'textures/nome_do_arquivo'
        filepath = os.path.join(os.path.dirname(__file__), "textures", filename)
        
        # Inverte o carregamento no eixo Y (necessário para Pygame -> OpenGL)
        image = pygame.image.load(filepath).convert_alpha()
        image = pygame.transform.flip(image, False, True) 
        
        texture_data = pygame.image.tostring(image, "RGBA", 1) 
        width, height = image.get_size()
        
        texture_id = glGenTextures(1)
        
        # Garante o tipo de dado correto
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
    """Gera um novo meteoro com posição inicial aleatória, longe do centro."""
    # Gera uma posição inicial em um grande cubo longe do centro
    # X, Y entre -15 e 15. Z bem atrás, entre -40 e -30.
    x = random.uniform(-15.0, 15.0)
    y = random.uniform(-15.0, 15.0)
    z = random.uniform(-40.0, -30.0) 
    
    # Velocidade (se move em direção a Z=-5, onde está a Terra)
    speed = random.uniform(0.1, 0.3) 
    
    # Tamanho
    size = random.uniform(0.05, 0.15)
    
    # Meteoro: [x, y, z, speed, size]
    return [x, y, z, speed, size]


def draw_scene(globe_texture_id, stars_texture_id, angle, meteors):
    """Desenha a cena 3D (estrelas de fundo, Terra girando e meteoros)."""
    
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    
    # ----------------------------------------------------
    # A. DESENHA O BACKGROUND DE ESTRELAS
    # ----------------------------------------------------
    if stars_texture_id:
        glLoadIdentity()
        # Move para trás para garantir que cubra a área de visão e fique atrás do globo
        glTranslatef(0.0, 0.0, -15.0) 
        
        glBindTexture(GL_TEXTURE_2D, stars_texture_id)
        glDisable(GL_LIGHTING)
        glColor3f(1.0, 1.0, 1.0) 
        glDisable(GL_DEPTH_TEST) # Desabilita o teste de profundidade para desenhar o fundo
        
        # Desenha um grande quadrado que cobre toda a cena
        glBegin(GL_QUADS)
        glTexCoord2f(0.0, 0.0); glVertex3f(-10.0, -10.0, 0.0) 
        glTexCoord2f(1.0, 0.0); glVertex3f( 10.0, -10.0, 0.0) 
        glTexCoord2f(1.0, 1.0); glVertex3f( 10.0,  10.0, 0.0) 
        glTexCoord2f(0.0, 1.0); glVertex3f(-10.0,  10.0, 0.0) 
        glEnd()
        
        glEnable(GL_DEPTH_TEST) # Reabilita o teste de profundidade
        glEnable(GL_LIGHTING)
    
    # ----------------------------------------------------
    # B. DESENHA O GLOBO TERRESTRE (Por cima do fundo)
    # ----------------------------------------------------
    glLoadIdentity()
    
    glTranslatef(-0.2, -0.2, -5.0) # Posição da Terra
    
    glRotatef(angle, 0, 1, 0) # Rotação no eixo Y (vertical)
    
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
        
    # ----------------------------------------------------
    # C. DESENHA OS METEOROS
    # ----------------------------------------------------
    glLoadIdentity() # Reseta a transformação antes de desenhar os meteoros
    
    # Reutiliza um quadric para desenhar as esferas dos meteoros
    quadric_meteor = gluNewQuadric()
    gluQuadricNormals(quadric_meteor, GLU_SMOOTH)

    # Verifica se a textura do meteoro está carregada
    if meteor_texture:
        # Se houver textura, configura e usa
        glEnable(GL_TEXTURE_2D)
        gluQuadricTexture(quadric_meteor, GL_TRUE)
        glBindTexture(GL_TEXTURE_2D, meteor_texture)
        glDisable(GL_LIGHTING) # Desabilitamos lighting para que a textura apareça sem interferência
        glColor3f(1.0, 1.0, 1.0) # Cor branca para usar a cor completa da textura
    else:
        # Caso contrário, usa a cor sólida (fallback)
        glDisable(GL_TEXTURE_2D)
        glEnable(GL_LIGHTING)
        glColor3f(*METEOR_COLOR)
    
    for x, y, z, _, size in meteors:
        glPushMatrix()
        glTranslatef(x, y, z)
        
        # Desenha a esfera do meteoro (baixa resolução para performance)
        gluSphere(quadric_meteor, size, 5, 5) 
        
        glPopMatrix()

    gluDeleteQuadric(quadric_meteor) 

    # Limpeza do estado para garantir que o menu 2D funcione
    glEnable(GL_LIGHTING)
    glEnable(GL_TEXTURE_2D) # Reabilita para o menu overlay


# ----------------------------------------------------------------------
## Funções de Desenho 2D (Overlay)
# ----------------------------------------------------------------------

def draw_centered_text_2d(screen, font, text, y_offset, color=(255, 255, 255), outline_color=None):
    """
    Renderiza texto centralizado com contorno opcional.
    """
    text_surface = font.render(text, True, color)
    text_rect = text_surface.get_rect(center=(
        DISPLAY_SIZE[0] // 2, 
        DISPLAY_SIZE[1] // 2 + y_offset 
    ))
    
    # Desenha o Contorno (Outline)
    if outline_color is not None:
        outline_surface = font.render(text, True, outline_color)
        outline_offset = 2 
        
        # Desenha o contorno em 8 direções
        for dx in [-outline_offset, 0, outline_offset]:
            for dy in [-outline_offset, 0, outline_offset]:
                if dx != 0 or dy != 0:
                    screen.blit(outline_surface, (text_rect.x + dx, text_rect.y + dy))

    # Desenha o texto principal por cima
    screen.blit(text_surface, text_rect)


# ----------------------------------------------------------------------
## Função Principal do Menu
# ----------------------------------------------------------------------

def menu_main():
    """Loop principal para o Menu Inicial do Jogo."""
    
    global rotation_angle, globe_texture, stars_texture, meteor_texture, np, meteors
    
    # 1. Inicializa o Pygame 
    pygame.init()
    
    # Cria a tela em modo OpenGL
    screen = pygame.display.set_mode(DISPLAY_SIZE, DOUBLEBUF | OPENGL)
    pygame.display.set_caption("Catch the Meteors - Menu")
    
    # Configura o ambiente 3D
    init_gl()
    
    # Tenta carregar as texturas
    globe_texture = load_texture("earth.jpg") 
    stars_texture = load_texture("stars.jpg") 
    meteor_texture = load_texture("meteor.jpg")
    
    # Inicializa a lista de meteoros
    meteors = [generate_meteor() for _ in range(10)] # Começa com 10 meteoros
    
    # Inicializa as fontes
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
    
    # Superfície 2D para desenhar os elementos do menu (transparência)
    menu_surface = pygame.Surface(DISPLAY_SIZE, pygame.SRCALPHA)
    
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                
                # Navegação no menu
                if event.key == pygame.K_UP:
                    selected_option = (selected_option - 1) % len(menu_options)
                if event.key == pygame.K_DOWN:
                    selected_option = (selected_option + 1) % len(menu_options)
                    
                # Seleção de opção
                if event.key == pygame.K_RETURN:
                    if menu_options[selected_option] == "INICIAR JOGO":
                        pygame.quit()
                        if run_game_main:
                            run_game_main()
                        return 
                        
                    elif menu_options[selected_option] == "SAIR":
                        running = False
                        
        
        # --- Lógica 3D: Atualiza a rotação e os Meteoros ---
        rotation_angle += 0.25 
        if rotation_angle > 360:
            rotation_angle -= 360
            
        # Atualiza a posição dos meteoros
        new_meteors = []
        for x, y, z, speed, size in meteors:
            # Movimento em direção a Z mais positivo (em direção à câmera/Terra)
            z += speed 
            
            # Se o meteoro ainda estiver atrás da Terra (Z=-5 com raio 1, atingiria em Z=-4)
            if z < -4.0: 
                new_meteors.append([x, y, z, speed, size])
        
        meteors = new_meteors
        
        # Gera novos meteoros (Taxa de spawn)
        # 10% de chance de spawn a cada frame se houver menos de 50 meteoros
        if random.random() < 0.1 and len(meteors) < 50: 
            meteors.append(generate_meteor())
            
        # Chama a função de desenho de cena, passando a lista de meteoros
        draw_scene(globe_texture, stars_texture, rotation_angle, meteors) 
        
        
        # --- Lógica 2D: Desenho do Menu (Sobreposição) ---
        
        menu_surface.fill((0, 0, 0, 0)) 
        s = pygame.Surface(DISPLAY_SIZE, pygame.SRCALPHA)
        s.fill((0, 0, 0, 150)) 
        menu_surface.blit(s, (0, 0))

        # TÍTULO ESTILO STAR WARS: Preto no centro com contorno Amarelo
        draw_centered_text_2d(menu_surface, font_title, "GUERRA NAS ESFERAS", -150, BLACK, outline_color=YELLOW)

        y_offset_start = 50
        y_spacing = 70
        for i, option in enumerate(menu_options):
            color = YELLOW if i == selected_option else GRAY
            draw_centered_text_2d(menu_surface, font_menu, option, y_offset_start + i * y_spacing, color)

        # AVISO DE NAVEGAÇÃO
        draw_centered_text_2d(menu_surface, font_small, 
                              "Use as setas para navegar e ENTER para selecionar", 
                              250, GRAY)

        # Transfere a superfície 2D para o buffer de tela do OpenGL
        glDisable(GL_DEPTH_TEST) 
        
        # Converte a superfície Pygame em textura OpenGL
        texture_data = pygame.image.tostring(menu_surface, "RGBA", True) 
        width, height = menu_surface.get_size()
        
        # Cria a nova textura temporária para o menu 2D
        gl_texture = glGenTextures(1)
        
        if np is not None and isinstance(gl_texture, (list, tuple, np.ndarray)):
            gl_texture_id = int(gl_texture[0])
        else:
            gl_texture_id = int(gl_texture)
            
        glBindTexture(GL_TEXTURE_2D, gl_texture_id)
        
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, texture_data)
        
        # Configura a projeção 2D
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        gluOrtho2D(0, width, 0, height) 
        
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        
        # Configura o blend (transparência)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glDisable(GL_LIGHTING) 
        glColor3f(1.0, 1.0, 1.0)
        
        # Desenha o plano 2D com a textura do menu
        glBegin(GL_QUADS)
        glTexCoord2f(0, 0); glVertex2f(0, 0) 
        glTexCoord2f(1, 0); glVertex2f(width, 0) 
        glTexCoord2f(1, 1); glVertex2f(width, height) 
        glTexCoord2f(0, 1); glVertex2f(0, height) 
        glEnd()

        glEnable(GL_LIGHTING) 
        glDisable(GL_BLEND)
        
        # Restaura as matrizes 3D
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()
        
        # Limpa a textura 2D
        glDeleteTextures([gl_texture_id]) 
        glEnable(GL_DEPTH_TEST)


        # Atualiza a tela 
        pygame.display.flip()
        clock.tick(60) 

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    if run_game_main is not None:
        menu_main()
    else:
        # Se 'game.py' não foi encontrado, ainda executa o menu para visualização.
        menu_main()