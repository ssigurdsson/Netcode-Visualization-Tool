"""docstring"""
import os
import pygame as pg
import netblob_client
from netblob_entities import Tracker
from netblob_config import *
import random
import time

class ClientMenu:
	"""d"""
	def __init__(self):
		os.environ["SDL_VIDEO_CENTERED"] = '1'
		self.window = self._get_window(MENU_WINDOW_SIZE)
		self.client = netblob_client.Client()

		self.run = True
		self.game_run_time = 1

		window_center_position = self.window.get_width()//2  # <- þetta er samt bara MENU_WINDOW_SIZE[0]//2 hér fyrir ofan
		self.name_box = InputField(window_center_position, 350, 320, \
				"Player Name:", max_len=MAX_NAME_LENGTH)
		self.address_box = InputField(window_center_position, 445, 320, \
				"Server IP Address:", DEFAULT_IP, 15)
		self.play_button = PlayButton(window_center_position, 515, 230, 50)

		self.menu_message = MENU_FONT_3.render('', True, RED)
		self.menu_message_position = (window_center_position, 285)

	def _get_window(self, window_size):
		window = pg.display.set_mode(window_size, pg.HWSURFACE)
		window.fill(WHITE)
		pg.display.set_caption("NetBlob - NetCode Visualization Tool")
		return window

	def collapse_menu(self):
		self.window = None
	
	def resume_menu(self, end_game_msg = ''):
		self.window = self._get_window(MENU_WINDOW_SIZE)
		self.menu_message = MENU_FONT_3.render(end_game_msg, True, RED)
		self.client = netblob_client.Client()

	def stop(self):
		self.collapse_menu()
		self.run = False

	def play_game(self):
		if self.play_button.clicked:
			self.play_button.clicked = False
			self._set_menu_message('Connecting...')
			self._update_display()
			self.client.connect(self.name_box.text, self.address_box.text)
			if self.client.is_connected(): return True
			self._set_menu_message('Error: Could not connect to server.')
		return False

	def _set_menu_message(self, message):
		self.menu_message = MENU_FONT_3.render(message, True, RED)

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
		background = pg.image.load('assets/menu_background.png')
		self.window.blit(background, (0,0))
		self.play_button.draw(self.window)
		self.name_box.draw(self.window)
		self.address_box.draw(self.window)
		menu_msg_width, menu_msg_height = self.menu_message.get_size()
		menu_msg_x = self.menu_message_position[0] - menu_msg_width//2
		menu_msg_y = self.menu_message_position[1] - menu_msg_height//2
		self.window.blit(self.menu_message, (menu_msg_x, menu_msg_y))
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
	"""dd"""
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
		window.blit(self.text_surface, (self.rect.x + 5, self.rect.y + 4))
		pg.draw.rect(window, DARK_GRAY, self.rect, 2)


class ClientGame:
	"""The Client Game is single threaded for improved performace"""
	def __init__(self, client):
		os.environ["SDL_VIDEO_CENTERED"] = '1'
		self.window = self._get_window(DEFAULT_WINDOW_SIZE)
		self.client = client
		self.player_id, self.player = client.get_player_info()
		self.players = {self.player_id : self.player}
		self.orbs = {}
		past_tracker = Tracker('past player position', BLUE)
		server_tracker = Tracker('server player position', RED)
		self.trackers = {'past' : past_tracker, 'server' : server_tracker}
		self.times = []

		self.end_game_state = ''
		self.run = True

	def _get_window(self, window_size):
		"""dd"""
		window = pg.display.set_mode(window_size, pg.HWSURFACE)
		window.fill(WHITE)
		pg.display.set_caption("Blob Game - NetCode Visualization Tool")
		return window

	def stop(self):
		self.run = False
		self.client.disconnect()

	def is_running(self):
		return self.run

	def get_end_state(self):
		return self.end_game_state

	def main_loop(self, time_delta):
		"""td"""
		self._handle_key_presses()
		self._update_player_inputs()
		for event in pg.event.get():
			self._handle_event(event)
		if not self.run: return

		if self.client.is_synced():
			for player in self.players.values():
				player.move(time_delta)

		if self.client.needs_sync():
			self.client.sync_state(time_delta, self.players, \
					self.orbs, self.trackers)

		if not self.client.is_connected():
			self.end_game_state = self.client.get_end_state()
			self.stop()
		self._update_display(time_delta)

	def _handle_event(self, event):
		"""dd"""
		if event.type == pg.QUIT:
			self.stop()
		elif event.type == pg.KEYDOWN:
			if event.key == pg.K_ESCAPE:
				self.stop()
			elif event.key == pg.K_1:
				self._get_window((1024,720))
			elif event.key == pg.K_2:
				self._get_window((1366,768))
			elif event.key == pg.K_3:
				self._get_window((1920,1080))
		elif event.type == pg.MOUSEBUTTONDOWN:
			if event.button == 1:
				self.trackers['past'].active = \
						not self.trackers['past'].active
			if event.button == 3:
				self.trackers['server'].active = \
						not self.trackers['server'].active

	def _handle_key_presses(self):
		"""dd"""
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
		"""dd"""
		window_width, window_height = self.window.get_size()
		raw_x, raw_y = pg.mouse.get_pos()
		mouse_x = (raw_x - window_width/2)/self.player.scale
		mouse_y = (raw_y - window_height/2)/self.player.scale
		self.player.inputs.x, self.player.inputs.y = mouse_x, mouse_y

	def _update_display(self, time_delta):
		"""dd"""
		# Erase the scoreboard + statistics areas
		pg.draw.rect(self.window, WHITE, \
				pg.Rect(self.window.get_width() - 220,0,300,330))
		pg.draw.rect(self.window, WHITE, pg.Rect(0,0,350,300))

		# Erase - then draw each player/orb/tracker
		sort_players = sorted(self.players.values(), key=lambda x: x.radius)
		for orb in self.orbs.values():
			orb.erase()
		for player in sort_players:
			player.erase()
		for tracker in self.trackers.values():
			tracker.erase()

		for orb in self.orbs.values():
			orb.draw(self.window, self.player)
		for player in sort_players:
			player.draw(self.window, self.player)
		for tracker in self.trackers.values():
			tracker.draw(self.window, self.player)

		self._draw_scoreboard(sort_players)
		self._draw_statistics(time_delta)
		pg.display.flip()

	def _draw_scoreboard(self, sort_players):
		"""dd"""
		# Sets the text position within the window in pixels
		top_left_x, top_left_y, delta_y = self.window.get_width()-205, 25, 30
		title = SCORE_FONT.render("Scoreboard", 1, BLACK)
		self.window.blit(title, (top_left_x, top_left_y))

		top_players = sort_players[-5:]
		for i, player in enumerate(reversed(top_players)):
			text = SCORE_FONT.render(str(i+1) + ". " + player.name, 1, BLACK)
			self.window.blit(text, (top_left_x, top_left_y + (i+1)*delta_y))

		title = SCORE_FONT.render("Trackers:", 1, BLACK)
		self.window.blit(title, (top_left_x, top_left_y+200))

		for i, tracker in enumerate(self.trackers.values()):
			if not tracker.active: continue
			text = SCORE_FONT_2.render(tracker.title, 1, tracker.color)
			self.window.blit(text, (top_left_x+5, top_left_y+230+i*delta_y))

	def _draw_statistics(self, time_delta):
		"""dd"""
		texts = []
		ping, bw, packet_loss_rate, lag_spike_duration = \
			self.client.get_connection_statistics()
		texts.append(SCORE_FONT.render("Score: " \
				+ str(int(self.player.radius)), 1, BLACK))
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
		# Sets the text position within the window in pixels
		top_left_x, top_left_y, delta_y = 10, 15, 40
		for i, text in enumerate(texts):
			self.window.blit(text, (top_left_x, top_left_y + i*delta_y))