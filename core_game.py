"""docstring"""
import random
import os
import pygame as pg
import pygame.gfxdraw as gdraw
from config import *
import time
import math


class Graphics:
	"""Barebones graphics class. Could use more entries."""
	def draw_sphere(self, draw_info, color, border = (0,WHITE)):
		window, x, y, radius = draw_info
		if border[0]:
			gdraw.aacircle(window, x, y, radius, border[1])
			gdraw.filled_circle(window, x, y, radius, border[1])
		border_size = min(border[0], int(0.3*radius))
		gdraw.aacircle(window, x, y, max(0,radius-border_size), color)
		gdraw.filled_circle(window, x, y, max(0,radius-border_size), color)

	def draw_circle(self, draw_info, color):
		window, x, y, radius = draw_info
		gdraw.aacircle(window, x, y, radius, color)

	def draw_title(self, title, draw_info):
		window, x, y, radius = draw_info
		text = TITLE_FONT.render(title, 1, BLACK)
		window.blit(text, (x-text.get_width()//2, y-text.get_height()//2))

	def erase_sphere(self, draw_info):
		window, x, y, radius = draw_info
		pg.draw.circle(window, WHITE, (x,y), radius+5)

	def get_draw_info(self, window, obj, player):
		window_width, window_height = window.get_size()
		ratio = int(100/player.scale)/100
		adjusted_x = int(obj.x*ratio) - int(player.x*ratio) + window_width//2
		adjusted_y = int(obj.y*ratio) - int(player.y*ratio) + window_height//2
		adjusted_radius = int(obj.radius*ratio)
		return window, adjusted_x, adjusted_y, adjusted_radius

# Vil ég svona?
# class DrawObj:
# 	window = None
# 	x, y = 0, 0
# 	radius = 0

class Player(Graphics):
	def __init__(self, player_name, position = (0,0), radius = START_RADIUS):
		self.name = player_name
		self.x, self.y = position
		self.color_idx = random.randrange(len(PLAYER_PALETTE))
		self.radius = radius  # Er þetta slæmur siður að nota self.var_name og var_name á sama stað?
		self.inputs = UserInputs()
		self.scale = 1
		self.draw_info = None

	def eat(self, other):
		new_area = self.radius*self.radius + other.radius*other.radius/4
		self.radius = math.sqrt(new_area)
		self.scale = math.pow(self.radius/START_RADIUS, 0.15)

	def move(self, time_delta):
		"""Moves the player based on its inputs and time_delta"""
		mouse_x, mouse_y = self.inputs.x, self.inputs.y
		mouse_distance = math.sqrt(mouse_x*mouse_x + mouse_y*mouse_y)
		if mouse_x == 0:
			if mouse_y >= 0: angle = math.pi/2
			else: angle = -math.pi/2
		else:
			angle = math.atan(mouse_y/mouse_x)
			if mouse_x < 0: angle += math.pi

		# Velocity drops off as the player gets larger by the below formula
		slow_effect = (self.radius-START_RADIUS)/VEL_DROP_OFF
		velocity = max(MIN_VELOCITY, START_VELOCITY - slow_effect)
		vel_x, vel_y = velocity*math.cos(angle), velocity*math.sin(angle)
		if mouse_distance < self.radius:
			# Slows down when the mouse is within the player's body
			vel_x *= mouse_distance/self.radius
			vel_y *= mouse_distance/self.radius
		else:
			# Prevents an unpleasant stuttering effect
			if abs(vel_x) < 40: vel_x = 0
			if abs(vel_y) < 40: vel_y = 0
		self.x = min(WIDTH-1, max(0, self.x + time_delta*vel_x))
		self.y = min(HEIGHT-1, max(0, self.y + time_delta*vel_y))

	def erase(self):
		if self.draw_info: self.erase_sphere(self.draw_info)

	def draw(self, window, player):
		self.draw_info = self.get_draw_info(window, self, player)
		self.draw_sphere(self.draw_info, PLAYER_PALETTE[self.color_idx], \
			(BORDER_SIZE, BORDER_PALETTE[self.color_idx]))
		self.draw_title(self.name, self.draw_info)


class UserInputs:
	def __init__(self, mouse_pos = (0,0), jump=False):
		self.x, self.y = mouse_pos
		self.JUMP = jump


class Tracker(Graphics):
	def __init__(self, tracker_title, tracker_color):
		self.x, self.y = 0, 0
		self.radius = 0
		self.color = tracker_color
		self.title = tracker_title
		self.active = True
		self.draw_info = (None,0,0,0)

	def erase(self):
		if self.draw_info[0]: self.erase_sphere(self.draw_info)

	def draw(self, window, player):
		if not self.active: return
		self.draw_info = self.get_draw_info(window, self, player)
		self.draw_circle(self.draw_info, self.color)


class Orb(Graphics):
	def __init__(self, position = (0,0)):
		self.x, self.y = position
		self.radius = random.randint(MIN_ORB_RADIUS, MAX_ORB_RADIUS)
		self.color_idx = random.randrange(len(ORB_PALETTE))
		self.draw_info = None

	def erase(self):
		if self.draw_info: self.erase_sphere(self.draw_info)

	def draw(self, window, player):
		self.draw_info = self.get_draw_info(window, self, player)
		self.draw_sphere(self.draw_info, ORB_PALETTE[self.color_idx])

	def __hash__(self):
		return hash((self.x, self.y))

	def __eq__(self, other):
		if isinstance(other, Orb):
			return (self.x, self.y) == (other.x, other.y)
		return False


class Network:

	def encode_inputs(self, inputs):
		return (int(inputs.x), int(inputs.y), inputs.JUMP)

	def decode_inputs(self, encoded_inputs):
		mouse_x, mouse_y, jump = encoded_inputs
		assert(isinstance(mouse_x,int) and isinstance(mouse_y,int))
		assert(isinstance(jump,bool))
		return UserInputs((mouse_x, mouse_y), jump)

	def encode_player(self, player):
		return (player.name, int(player.x), int(player.y), player.color_idx, \
				int(player.radius), self.encode_inputs(player.inputs))

	def decode_player(self, encoded_player):
		name, x, y, color_idx, radius, inputs = encoded_player
		assert(isinstance(name, str) and len(name) <= MAX_NAME_LENGTH)
		assert(isinstance(x, int) and isinstance(y, int))
		assert(0 <= x < WIDTH and 0 <= y < HEIGHT)
		assert(isinstance(color_idx, int) and 0 <= color_idx < len(PLAYER_PALETTE))
		assert(isinstance(radius, int) and START_RADIUS <= radius < HEIGHT/2)
		decoded_player = Player(name, (x,y), radius)
		decoded_player.inputs = self.decode_inputs(inputs)
		decoded_player.color_idx = color_idx
		return decoded_player

	def encode_orb(self, orb):
		return (orb.x, orb.y)

	def decode_orb(self, encoded_orb):
		x, y = encoded_orb
		assert(isinstance(x, int) and isinstance(y, int))
		assert(0 <= x < WIDTH and 0 <= y < HEIGHT)
		return Orb((x,y))