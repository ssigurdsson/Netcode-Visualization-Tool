"""docstring"""
import os
import pygame as pg
import udp_client
from core_game import Tracker
from config import *
import random


class ClientMenu:
	"""d"""
	def __init__(self):
		os.environ["SDL_VIDEO_CENTERED"] = '1'
		self.name_box = InputField(512, 345, 320, \
				"Player Name:", max_len=MAX_NAME_LENGTH)
		self.address_box = InputField(512, 440, 320, \
				"Server IP Address:", DEFAULT_IP, 15)
		self.play_button = PlayButton(512, 510, 230, 50)

		self.run = True
		self.window = self._get_window()
		self.client = udp_client.Client()
		self.menu_message = ''
		self.game_run_time = 1

	def _get_window(self):
		window = pg.display.set_mode(MENU_WINDOW_SIZE, pg.HWSURFACE)
		pg.display.set_caption("Agar NetCode Visualization Tool")
		return window

	def collapse_menu(self):
		self.window = None
	
	def resume_menu(self, end_game_msg = ''):
		self.window = self._get_window()
		self.menu_message = end_game_msg
		self.client = udp_client.Client()

	def stop(self):
		self.collapse_menu()
		self.run = False

	def play_game(self):
		if self.play_button.clicked:
			self.play_button.clicked = False
			self.menu_message = 'Connecting...'
			self._update_display()
			self.client.connect(self.name_box.text, self.address_box.text)
			if self.client.is_connected(): return True
			self.menu_message = 'Error: Could not connect to server.'
		return False

	def get_client(self):
		return self.client

	def is_running(self):
		return self.run

	def main_loop(self):
		self._update_display()

		for event in pg.event.get():
			self._handle_event(event)

	def _handle_event(self, event):
		if event.type == pg.QUIT:
			self.stop()
		else:
			self.play_button.handle_event(event)
			self.name_box.handle_event(event)
			self.address_box.handle_event(event)

	def _update_display(self):
		background = pg.image.load('assets/Agar_Menu.png')
		self.window.blit(background, (0,0))
		self.play_button.draw(self.window)
		self.name_box.draw(self.window)
		self.address_box.draw(self.window)
		_text = MENU_FONT_3.render(self.menu_message, True, RED)
		self.window.blit(_text, (512 - _text.get_width()//2 ,280))
		pg.display.update()


class PlayButton:
	"""dd"""
	def __init__(self, center_x, top_y, width, height):
		self.x = center_x
		self.text_surface = MENU_FONT_1.render("START GAME", True, DARK_GRAY)
		self.rect = pg.Rect((center_x - width//2, top_y, width, height))
		self.clicked = False
		self.hovered = False

	def handle_event(self, event):
		if event.type == pg.MOUSEBUTTONDOWN:
			if self.rect.collidepoint(event.pos):
				self.clicked = True
		elif event.type == pg.MOUSEMOTION:
			self.hovered = self.rect.collidepoint(event.pos)

	def draw(self, window):
		color = LIGHT_GREEN if self.hovered else LIGHT_GRAY
		pg.draw.rect(window, color, self.rect, 0)  # Fill color
		pg.draw.rect(window, DARK_GRAY, self.rect, 2)  # Frame color
		text_width = self.text_surface.get_width()
		text_height = self.text_surface.get_height()
		text_x = self.x - text_width//2
		text_y = self.rect.y + self.rect.height//2 - text_height//2
		window.blit(self.text_surface, (text_x, text_y))


class InputField:
	def __init__(self, center_x, top_y, width, title_text, \
				default_text = "", max_len = 20):
		self.text = default_text
		self.title_surface = MENU_FONT_1.render(title_text, True, DARK_GRAY)
		self.text_surface = MENU_FONT_2.render(default_text, True, DARK_GRAY)
		height = self.text_surface.get_height()
		self.rect = pg.Rect((center_x - width//2, top_y, width, height+5))
		self.selected = False
		self.max_length = max_len

	def handle_event(self, event):
		if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
			self.selected = self.rect.collidepoint(event.pos)
		elif self.selected and event.type == pg.KEYDOWN:
			if event.key == pg.K_BACKSPACE:
				self.text = self.text[:-1]
			elif event.key == pg.K_DELETE:
				self.text = ""
			elif len(self.text) < self.max_length:
				self.text = self.text + event.unicode
		input_text = self.text + '|' if self.selected else self.text
		self.text_surface = MENU_FONT_2.render(input_text, True, DARK_GRAY)

	def draw(self, window):
		title_y = self.rect.y - self.title_surface.get_height() - 4
		window.blit(self.title_surface, (self.rect.x, title_y))
		window.blit(self.text_surface, (self.rect.x + 4, self.rect.y + 4))
		pg.draw.rect(window, DARK_GRAY, self.rect, 2)


class ClientGame:
	def __init__(self, client):
		self.window = None
		self.client = client
		self.player_id, self.player = client.get_player_info()
		self.players, self.orbs = {self.player_id : self.player}, {}
		past_tracker = Tracker('past player position', BLUE)
		server_tracker = Tracker('server player position', RED)
		self.trackers = {'past' : past_tracker, 'server' : server_tracker}
		self.end_state = ''
		self.run = True

		self.display_game((1366,768))

	def display_game(self, size):
		os.environ["SDL_VIDEO_CENTERED"] = '1'
		self.window = pg.display.set_mode(size, pg.HWSURFACE)
		self.window.fill(WHITE)
		pg.display.set_caption("Agar NetCode Visualization Tool")

	def stop(self):
		self.run = False
		self.client.disconnect()

	def is_running(self):
		return self.run

	def get_end_state(self):
		return self.end_state

	def main_loop(self, time_delta):
		"""td"""
		self._handle_key_presses()
		if self.client.is_synced():
			for player in self.players.values():
				player.move(time_delta)

		if self.client.needs_transmit():
			self._update_player_inputs()
			self.client.sync_state(time_delta, self.players, \
					self.orbs, self.trackers)

		if not self.client.is_connected():
			self.end_game_state = self.client.get_end_state()
			self.stop()
		self._update_display(time_delta)

		for event in pg.event.get():
			self._handle_event(event)

	def _handle_event(self, event):
		if event.type == pg.QUIT:
			self.stop()
		elif event.type == pg.KEYDOWN:
			if event.key == pg.K_ESCAPE:
				self.stop()
			elif event.key == pg.K_1:
				self.display_game((1024,720))
			elif event.key == pg.K_2:
				self.display_game((1366,768))
			elif event.key == pg.K_3:
				self.display_game((1920,1080))
		elif event.type == pg.MOUSEBUTTONDOWN:
			if event.button == 1:
				self.trackers['past'].active = \
						not self.trackers['past'].active
			if event.button == 3:
				self.trackers['server'].active = \
						not self.trackers['server'].active

	def _handle_key_presses(self):
		keys = pg.key.get_pressed()
		if keys[pg.K_e]:
			self.client.increase_ping()
		elif keys[pg.K_w]:
			self.client.decrease_ping()
		elif keys[pg.K_d]:
			self.client.increase_packet_loss()
		elif keys[pg.K_s]:
			self.client.decrease_packet_loss()
		elif keys[pg.K_c]:
			self.client.increase_lag_spike()
		elif keys[pg.K_x]:
			self.client.decrease_lag_spike()

	def _update_player_inputs(self):
		window_width, window_height = self.window.get_size()
		raw_x, raw_y = pg.mouse.get_pos()
		key_presses = pg.key.get_pressed()
		mouse_x = int((raw_x - window_width/2)/self.player.scale)
		mouse_y = int((raw_y - window_height/2)/self.player.scale)
		self.player.inputs.x, self.player.inputs.y = mouse_x, mouse_y
		self.player.inputs.JUMP = bool(key_presses[pg.K_SPACE])

	def _update_display(self, time_delta):
		"""Draws each frame at regular intervals"""
		# Erase the scoreboard + statistics areas
		pg.draw.rect(self.window, WHITE, pg.Rect(self.window.get_width() - 220,0,300,330))
		pg.draw.rect(self.window, WHITE, pg.Rect(0,0,350,300))

		# Erase - then draw each player/orb/tracker
		sort_players = sorted(self.players.values(), key=lambda x: x.radius)
		for orb in self.orbs.values(): orb.erase()
		for player in sort_players: player.erase()
		for tracker in self.trackers.values(): tracker.erase()

		for orb in self.orbs.values(): orb.draw(self.window, self.player)
		for player in sort_players: player.draw(self.window, self.player)
		for tracker in self.trackers.values(): tracker.draw(self.window, self.player)

		self._draw_scoreboard(sort_players)
		self._draw_statistics(time_delta)
		pg.display.update()

	def _draw_scoreboard(self, sort_players):
		title = SCORE_FONT.render("Scoreboard", 1, BLACK)
		sx, sy = self.window.get_width() - 220, 25
		self.window.blit(title, (sx, sy))

		top_players = sort_players[-5:]
		for i, player in enumerate(reversed(top_players)):
			text = SCORE_FONT_2.render(str(i+1) + ". " + player.name, 1, BLACK)
			self.window.blit(text, (sx, sy + (i+1)*30))

		title = SCORE_FONT.render("Trackers:", 1, BLACK)
		self.window.blit(title, (sx, 220))

		for i, tracker in enumerate(self.trackers.values()):
			if not tracker.active: continue
			text = SCORE_FONT_2.render(tracker.title, 1, tracker.color)
			self.window.blit(text, (sx+5, 250+i*30))

	def _draw_statistics(self, time_delta):
		# Draws the score and connection statistics
		dx, dy, texts = 10, 15, []
		ping, bw, packet_loss_rate, lag_spike_duration = \
			self.client.get_connection_statistics()
		texts.append(SCORE_FONT.render("Score: " \
					+ str(int(self.player.radius) - START_RADIUS), 1, BLACK))
		texts.append(SCORE_FONT.render("FPS: " \
					+ str(int(1/(time_delta+0.001))), 1, BLACK))
		texts.append(SCORE_FONT.render("Bandwidth: " \
					+ str(int(bw/100)/10) + " KB/S", 1, BLACK))
		texts.append(SCORE_FONT.render("[W / E] Ping: " \
					+ str(int(ping*1000)) + " ms", 1, BLACK))
		texts.append(SCORE_FONT.render("[S / D] Packet loss rate: " \
					+ str(int(packet_loss_rate)) + " %", 1, BLACK))
		texts.append(SCORE_FONT.render("[X / C] Lag Spike Duration: " \
					+ str(round(10*lag_spike_duration)/10) + " s", 1, BLACK))
		for i, text in enumerate(texts): 
			self.window.blit(text, (dx, dy + i*40))