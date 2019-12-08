"""docstring"""
import pygame as pg
import pygame.gfxdraw as gdraw
import netblob_animation
from netblob_config import *
import math
import random


class Player:
	"""dd"""
	def __init__(self, player_name, position = (0,0), radius = START_RADIUS):
		self.name = player_name
		self.x, self.y = position
		self.color_idx = random.randrange(len(PLAYER_PALETTE))
		self.radius = radius  # Er þetta slæmur siður að nota self.var_name og var_name á sama stað?
		self.inputs = UserInputs()
		self.scale = 1
		self.draw_info = None

	def eat(self, other):
		self.radius += 0.02*other.radius

	def move(self, time_delta):
		"""Moves the player based on its inputs and time_delta"""
		mouse_x, mouse_y = self.inputs.x, self.inputs.y
		mouse_distance = math.sqrt(mouse_x*mouse_x + mouse_y*mouse_y)
		if mouse_distance == 0: return

		norm_x, norm_y = mouse_x/mouse_distance, mouse_y/mouse_distance
		velocity = BASE_VELOCITY
		velocity *= math.pow(START_RADIUS/self.radius, VELOCITY_SLOW_FACTOR)
		vel_x, vel_y = velocity*norm_x, velocity*norm_y
		if mouse_distance < self.radius:
			# Slows down when the mouse is within the player's body
			vel_x *= mouse_distance/self.radius
			vel_y *= mouse_distance/self.radius
		else:
			# Prevents an unpleasant stuttering effect
			if abs(vel_x) < 30: vel_x = 0
			if abs(vel_y) < 30: vel_y = 0

		self.x = min(WIDTH-1, max(0, self.x + time_delta*vel_x))
		self.y = min(HEIGHT-1, max(0, self.y + time_delta*vel_y))

	def erase(self):
		if self.draw_info: netblob_animation.erase_obj(self.draw_info)

	def draw(self, window, player):
		self.scale = math.pow(self.radius/START_RADIUS, VIEW_GROWTH_RATE)
		self.draw_info = netblob_animation.get_draw_info(window, self, player)

		window, x, y, radius = self.draw_info
		if x < -self.radius or x > window.get_width() + self.radius:
			return
		if y < -self.radius or y > window.get_height() + self.radius:
			return
		sub_radius = max(0, radius - min(BORDER_SIZE, int(0.3*radius)))
		border_color = BORDER_PALETTE[self.color_idx]
		body_color = PLAYER_PALETTE[self.color_idx]
		netblob_animation.draw_circle(window, x, y, radius, border_color)
		netblob_animation.draw_circle(window, x, y, sub_radius, body_color)

		text = TITLE_FONT.render(self.name, 1, BLACK)
		text_width, text_height = text.get_size()
		window.blit(text, (x-text_width//2, y-text_height//2))


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
		self.draw_info = None

	def erase(self):
		if self.draw_info: netblob_animation.erase_obj(self.draw_info)

	def draw(self, window, player):
		if not self.active: return
		self.draw_info = netblob_animation.get_draw_info(window, self, player)

		window, x, y, radius = self.draw_info
		gdraw.aacircle(window, x, y, radius, self.color)


class Orb:
	"""dd"""
	def __init__(self, position = (0,0)):
		self.x, self.y = position
		self.radius = random.randint(MIN_ORB_RADIUS, MAX_ORB_RADIUS)
		self.color_idx = random.randrange(len(ORB_PALETTE))
		self.draw_info = None

	def erase(self):
		if self.draw_info: netblob_animation.erase_obj(self.draw_info)

	def draw(self, window, player):
		self.draw_info = netblob_animation.get_draw_info(window, self, player)

		window, x, y, radius = self.draw_info
		if x < -MAX_ORB_RADIUS or x > window.get_width() + MAX_ORB_RADIUS:
			return
		if y < -MAX_ORB_RADIUS or y > window.get_height() + MAX_ORB_RADIUS:
			return
		body_color = ORB_PALETTE[self.color_idx]
		netblob_animation.draw_circle(window, x, y, radius, body_color)

	def __hash__(self):
		return hash((self.x, self.y))

	def __eq__(self, other):
		if isinstance(other, Orb):
			return (self.x, self.y) == (other.x, other.y)
		return False