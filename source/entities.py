"""docstring"""
import math
import random
import pygame as pg
import source.config as cfg


class Player:
    """dd"""
    def __init__(self, player_name, player_id, field_size,
                position = (0,0), radius = cfg.START_RADIUS):
        self.name = player_name
        self.x, self.y = position
        self.id = player_id
        self.color_idx = random.randrange(len(cfg.PLAYER_PALETTE))
        self.radius = radius
        self.inputs = UserInputs()
        self.field_size = field_size
        self.scale = 1
        self.name_surface = cfg.TITLE_FONT.render(self.name, 1, cfg.BLACK)
        self.scoreboard_surface = cfg.SCORE_FONT.render(self.name, 1, cfg.BLACK)
        self.draw_info = None

    def find_distance(self, entity):
        dx, dy = (self.x-entity.x), (self.y-entity.y)
        return math.sqrt(dx*dx + dy*dy)

    def eat(self, other):
        """server-side function"""
        adjusted_radius = other.radius - cfg.EAT_VALUE_OFFSET
        self.radius = math.sqrt(
            self.radius*self.radius + adjusted_radius*adjusted_radius)
        self.radius = min(self.radius, cfg.MAX_RADIUS)
        self.scale = math.pow(self.radius/cfg.START_RADIUS, cfg.VIEW_GROWTH_RATE)

    def move(self, time_delta):
        """Moves the player based on its inputs and time_delta"""
        mouse_x, mouse_y = self.inputs.x, self.inputs.y
        mouse_distance = math.sqrt(mouse_x*mouse_x + mouse_y*mouse_y)
        if mouse_distance == 0: return

        norm_x, norm_y = mouse_x/mouse_distance, mouse_y/mouse_distance
        velocity = cfg.BASE_VELOCITY
        velocity *= math.pow(cfg.START_RADIUS/self.radius, cfg.VELOCITY_SLOW_FACTOR)
        vel_x, vel_y = velocity*norm_x, velocity*norm_y
        scaled_radius = self.radius/self.scale
        if mouse_distance < scaled_radius:
            # Slows down when the mouse is within the player's body
            vel_x *= mouse_distance/scaled_radius
            vel_y *= mouse_distance/scaled_radius
        else:
            # Prevents an unpleasant stuttering effect
            if abs(vel_x) < 30: vel_x = 0
            if abs(vel_y) < 30: vel_y = 0

        self.x = min(self.field_size[0]-1, max(0, self.x + time_delta*vel_x))
        self.y = min(self.field_size[1]-1, max(0, self.y + time_delta*vel_y))


class UserInputs:
    """dd"""
    def __init__(self, mouse_position = (0,0)):
        self.x, self.y = mouse_position


class Tracker:
    """dd"""
    def __init__(self, tracker_title, tracker_color):
        self.x, self.y = 0, 0
        self.radius = 0
        self.color = tracker_color
        self.title = tracker_title
        self.active = True
        self.scoreboard_surface = cfg.SCORE_FONT.render(self.title, 1, tracker_color)


class Orb:
    """dd"""
    def __init__(self, position = (0,0), orb_id = 0):
        self.x, self.y = position
        self.id = orb_id
        self.radius = random.randint(cfg.MIN_ORB_RADIUS, cfg.MAX_ORB_RADIUS)
        self.color_idx = random.randrange(len(cfg.ORB_PALETTE))
