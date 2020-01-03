"""Barebones animation module. Provides an interface for the game display."""

import os
import math
import random
import time
import pygame as pg
import pygame.gfxdraw as gdraw
import source.config as cfg


class GameWindow:
    def __init__(self, observer, caption, map_size):
        self.caption = caption
        self.window = self._get_window(cfg.DEFAULT_WINDOW_SIZE)
        self.width, self.height = cfg.DEFAULT_WINDOW_SIZE
        self.map_size = map_size
        self.observer = observer
        self.ratio = 1
        self.transition_speed = 0
        self.observer_x = self.observer.x - self.width//2
        self.observer_y = self.observer.y - self.height//2
        self.drawings = []
        self.scoreboard_texts = {}
        self.statistics_texts = {}
        self._transition()

    def _get_window(self, window_size):
        window = pg.display.set_mode(window_size, pg.DOUBLEBUF)
        window.fill(cfg.WHITE)
        window.set_alpha(None)
        pg.display.set_caption(self.caption)
        return window

    def set_size(self, window_size):
        self.width, self.height = window_size
        self.window = self._get_window(window_size)

    def set_observer(self, observer):
        self.observer = observer
        self._transition()

    def clear(self, time_delta):
        while self.drawings:
            x, y, (width, height) = self.drawings.pop()
            surface = pg.Rect(x-2, y-2, width+4, height+4)
            pg.draw.rect(self.window, cfg.WHITE, surface)
        self._update(time_delta)

    def _update(self, time_delta):
        self._draw_grid(cfg.WHITE)
        observer_ratio = 1/self.observer.scale
        if self.transition_speed:
            self.ratio -= time_delta*self.transition_speed*cfg.VIEW_SCALE_RATE
            if (self.transition_speed > 0 and self.ratio < observer_ratio
                or self.transition_speed < 0 and self.ratio > observer_ratio):
                self.transition_speed = 0
                self.ratio = observer_ratio
        elif abs(self.ratio - observer_ratio) > 0.05*observer_ratio:
            self._transition()
        self.observer_x = int(self.observer.x*self.ratio - self.width/2)
        self.observer_y = int(self.observer.y*self.ratio - self.height/2)
        self._draw_grid(cfg.LIGHT_GRAY)

    def _transition(self):
        self.transition_speed = self.ratio - 1/self.observer.scale

    def _draw_grid(self, color):
        for i in range(self.map_size[0]//cfg.MAP_CELL_SIZE[0] + 2):
            x, y = i*cfg.MAP_CELL_SIZE[0], i*cfg.MAP_CELL_SIZE[1]
            x, _, thickness = self._adjust_values(x, 0, 0)
            _, y, thickness = self._adjust_values(0, y, 0)
            if 0 <= x < self.width:
                pg.draw.line(self.window, color, (x,0), (x, self.height))
            if 0 <= y < self.height and i <= self.map_size[1]//cfg.MAP_CELL_SIZE[1] + 1:
                pg.draw.line(self.window, color, (0,y), (self.width, y))

    def draw_text(self, text_surface, x, y, right_align = False):
        if right_align:
            self.drawings.append((self.width - x, y, text_surface.get_size()))
            self.window.blit(text_surface, (self.width - x, y))
        else:
            self.drawings.append((x, y, text_surface.get_size()))
            self.window.blit(text_surface, (x, y))

    def draw_player(self, player):
        x, y, radius = self._adjust_values(player.x, player.y, player.radius)
        if x < -radius or y < -radius or x > self.width + radius or y > self.width + radius: return
        self.drawings.append((x-radius, y-radius, (2*radius,2*radius)))
        sub_radius = max(0, radius - min(cfg.BORDER_SIZE, int(0.08*radius)+2))
        border_color = cfg.BORDER_PALETTE[player.color_idx]
        body_color = cfg.PLAYER_PALETTE[player.color_idx]
        self.draw_filled_circle(x, y, radius, border_color)
        self.draw_filled_circle(x, y, sub_radius, body_color)

        text_width, text_height = player.name_surface.get_size()
        self.draw_text(player.name_surface, x-text_width//2, y-text_height//2)
    
    def draw_tracker(self, tracker):
        if not tracker.active: return
        x, y, radius = self._adjust_values(tracker.x, tracker.y, tracker.radius)
        self.drawings.append((x-radius, y-radius, (2*radius,2*radius)))
        self.draw_circle(x, y, radius, tracker.color)

    def draw_orb(self, orb):
        x, y, radius = self._adjust_values(orb.x, orb.y, orb.radius)
        if x < -radius or y < -radius or x > self.width + radius or y > self.width + radius: return
        self.drawings.append((x-radius, y-radius, (2*radius,2*radius)))
        body_color = cfg.ORB_PALETTE[orb.color_idx]
        self.draw_filled_circle(x, y, radius, body_color)

    def _adjust_values(self, x, y, radius):
        adjusted_x = int(x*self.ratio) - self.observer_x
        adjusted_y = int(y*self.ratio) - self.observer_y
        adjusted_radius = int(radius*self.ratio)
        return adjusted_x, adjusted_y, adjusted_radius

    def draw_filled_circle(self, x, y, radius, color):
        gdraw.aacircle(self.window, x, y, radius, color)
        gdraw.filled_circle(self.window, x, y, radius, color)

    def draw_circle(self, x, y, radius, color):
        gdraw.aacircle(self.window, x, y, radius, color)
