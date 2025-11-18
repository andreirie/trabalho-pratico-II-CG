import math
import time
import pygame
from OpenGL.GL import *
from OpenGL.GLU import *

pygame.mixer.init()

sound_on = pygame.mixer.Sound("sounds/saber_on.mp3")
sound_off = pygame.mixer.Sound("sounds/saber_off.mp3")

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
        [(-0.5, -0.5,  0.5), ( 0.5, -0.5,  0.5), ( 0.5,  0.5,  0.5), (-0.5,  0.5,  0.5)],
        [(-0.5, -0.5, -0.5), ( 0.5, -0.5, -0.5), ( 0.5,  0.5, -0.5), (-0.5,  0.5, -0.5)],
        [(-0.5, -0.5, -0.5), (-0.5, -0.5,  0.5), (-0.5,  0.5,  0.5), (-0.5,  0.5, -0.5)],
        [( 0.5, -0.5, -0.5), ( 0.5, -0.5,  0.5), ( 0.5,  0.5,  0.5), ( 0.5,  0.5, -0.5)],
        [(-0.5,  0.5,  0.5), ( 0.5,  0.5,  0.5), ( 0.5,  0.5, -0.5), (-0.5,  0.5, -0.5)],
        [(-0.5, -0.5,  0.5), ( 0.5, -0.5,  0.5), ( 0.5, -0.5, -0.5), (-0.5, -0.5, -0.5)]
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

    glColor4f(r*1.4, g*1.4, b*1.4, core_alpha)
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
        sound_on.play()
    else:
        sound_off.play()
