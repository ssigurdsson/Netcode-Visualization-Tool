"""Barebones animation module. Could use more entries."""
import pygame as pg
import pygame.gfxdraw as gdraw
from netblob_config import *


def get_draw_info(window, obj, player):
    window_width, window_height = window.get_size()
    ratio = int(100/player.scale)/100  # Creates discontinuity in the player-scale growth curve in order prevent an unpleasant visual effect
    adjusted_x = int(obj.x*ratio) - int(player.x*ratio) + window_width//2
    adjusted_y = int(obj.y*ratio) - int(player.y*ratio) + window_height//2
    adjusted_radius = int(obj.radius*ratio)
    return window, adjusted_x, adjusted_y, adjusted_radius

def erase_obj(draw_info):
    window, x, y, radius = draw_info  # Er svona draw info tuple slæmt
    pg.draw.circle(window, WHITE, (x,y), radius+5)

def draw_circle(window, x, y, radius, color):
    gdraw.aacircle(window, x, y, radius, color)
    gdraw.filled_circle(window, x, y, radius, color)