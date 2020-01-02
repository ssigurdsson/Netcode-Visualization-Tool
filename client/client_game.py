"""Provides a client menu and client game interface for handling of game logic."""

import os
import time
import socket
import pygame as pg
from source.animation import GameWindow
from client.client import Client
import source.config as cfg
from source.entities import Player, Tracker, UserInputs


class ClientMenu:
    """Provides an interactive menu for initializing the client game.

    The two text input fields allow the user to specify and player
    name and a server ip address. The pre-input default server ip
    address corresponds to the user's local network ip address.
    """
    def __init__(self):
        self.window = self._get_window(cfg.MENU_WINDOW_SIZE)
        self.client = Client()
        self.run = True

        # The below UI elements include some magic numbers that specify
        # layout positions etc. May revise this.
        window_center_position = self.window.get_width()//2
        self.play_button = PlayButton(window_center_position, 515, 230, 50)
        self.name_box = InputField(
            window_center_position, 350, 320, "Player Name:",
            max_len=cfg.MAX_NAME_LENGTH)

        try:
            local_addr = socket.gethostbyname(socket.gethostname())
        except:
            local_addr = ""
        self.address_box = InputField(
            window_center_position, 445, 320, "Server IP Address:",
            local_addr, 15)  # Supports only ipv4 addresses

        self.background = pg.image.load("assets/menu_background.png")
        self.menu_message = cfg.MENU_FONT_3.render('', True, cfg.RED)
        self.menu_message_position = (window_center_position, 285)

    def _get_window(self, window_size):
        window = pg.display.set_mode(window_size, pg.HWSURFACE)
        window.fill(cfg.WHITE)
        pg.display.set_caption("NetBlob - NetCode Visualization Tool")
        return window

    def collapse_menu(self):
        self.window = None

    def resume_menu(self, end_game_msg = ""):
        self.window = self._get_window(cfg.MENU_WINDOW_SIZE)
        self.menu_message = cfg.MENU_FONT_3.render(end_game_msg, True, cfg.RED)
        self.client = Client()

    def stop(self):
        self.collapse_menu()
        self.run = False

    def play_game(self):
        if self.play_button.clicked:
            self.play_button.clicked = False
            self._set_menu_message("Connecting...")
            self._update_display()
            self.client.connect(self.name_box.text, self.address_box.text)
            if self.client.is_connected(): return True
            self._set_menu_message("Error: Could not connect to server.")
        return False

    def _set_menu_message(self, message):
        self.menu_message = cfg.MENU_FONT_3.render(message, True, cfg.RED)

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
        self.window.blit(self.background, (0,0))
        self.play_button.draw(self.window)
        self.name_box.draw(self.window)
        self.address_box.draw(self.window)
        menu_msg_width, menu_msg_height = self.menu_message.get_size()
        menu_msg_x = self.menu_message_position[0] - menu_msg_width//2
        menu_msg_y = self.menu_message_position[1] - menu_msg_height//2
        self.window.blit(self.menu_message, (menu_msg_x, menu_msg_y))
        pg.display.update()


class PlayButton:
    """Provides an interactive play button box."""
    def __init__(self, center_x, top_y, width, height):
        self.x = center_x
        self.text_surface = cfg.MENU_FONT_1.render("START GAME", True, cfg.DARK_GRAY)
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
        color = cfg.LIGHT_GREEN if self.hovered else cfg.LIGHT_GRAY
        pg.draw.rect(window, color, self.rect, 0)  # Fill color
        pg.draw.rect(window, cfg.DARK_GRAY, self.rect, 2)  # Frame color
        text_width = self.text_surface.get_width()
        text_height = self.text_surface.get_height()
        text_x = self.x - text_width//2
        text_y = self.rect.y + self.rect.height//2 - text_height//2
        window.blit(self.text_surface, (text_x, text_y))


class InputField:
    """Provides an interactive text input box."""
    def __init__(self, center_x, top_y, width, title_text, \
                default_text = "", max_len = 20):
        self.text = default_text
        self.title_surface = cfg.MENU_FONT_1.render(title_text, True, cfg.DARK_GRAY)
        self.text_surface = cfg.MENU_FONT_2.render(default_text, True, cfg.DARK_GRAY)
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
        self.text_surface = cfg.MENU_FONT_2.render(input_text, True, cfg.DARK_GRAY)

    def draw(self, window):
        title_y = self.rect.y - self.title_surface.get_height() - 4
        window.blit(self.title_surface, (self.rect.x, title_y))
        window.blit(self.text_surface, (self.rect.x + 5, self.rect.y + 4))
        pg.draw.rect(window, cfg.DARK_GRAY, self.rect, 2)


class ClientGame:
    """Handles all game logic on the client side.

    The main_loop function updates the entire game state for a given
    time interval, and updates the display. The player inputs are regularly
    communicated to the server through a client instance, which handles all
    server interactions. The game state consists of a collection of
    players and orbs at different coordinates within a game map.
    """
    def __init__(self, client):
        self.client = client
        self.players, self.player = self.client.get_players()
        self.map_size = self.client.map_size
        self.window = GameWindow(
            self.player, "Netblob - Client", self.map_size)
        self.orbs = {}
        past_tracker = Tracker("past player position", cfg.BLUE)
        server_tracker = Tracker("server player position", cfg.RED)
        self.trackers = {"past" : past_tracker, "server" : server_tracker}
        self.end_game_state = ''
        self.run = True

    def stop(self):
        self.run = False
        self.client.disconnect()

    def is_running(self):
        return self.run

    def get_end_state(self):
        return self.end_game_state

    def main_loop(self, time_delta):
        """td"""
        if self.client.is_synced():
            self.player = self.players[self.client.player_id]
            for player in self.players.values():
                player.move(self.map_size, time_delta)

        if self.client.needs_sync():
            self.client.sync_state(time_delta, self.players,
                    self.orbs, self.trackers)

        if not self.client.is_connected():
            self.end_game_state = self.client.get_end_state()
            self.stop()

        self._handle_key_presses(time_delta)
        self._update_player_inputs()
        self._update_display(time_delta)
        
        for event in pg.event.get():
            self._handle_event(event)

    def _handle_event(self, event):
        """dd"""
        if event.type == pg.QUIT:
            self.stop()
        elif event.type == pg.KEYDOWN:
            if event.key == pg.K_ESCAPE:
                self.stop()
            elif event.key == pg.K_1:
                self.window.set_size((1024,720))
            elif event.key == pg.K_2:
                self.window.set_size((1366,768))
            elif event.key == pg.K_3:
                self.window.set_size((1920,1080))
        elif event.type == pg.MOUSEBUTTONDOWN:
            if event.button == 1:
                self.trackers["past"].active = \
                        not self.trackers["past"].active
            if event.button == 3:
                self.trackers["server"].active = \
                        not self.trackers["server"].active

    def _handle_key_presses(self, time_delta):
        """dd"""
        keys = pg.key.get_pressed()
        if keys[pg.K_e]:
            self.client.increase_ping(time_delta)
        elif keys[pg.K_w]:
            self.client.decrease_ping(time_delta)
        elif keys[pg.K_d]:
            self.client.increase_packet_loss(time_delta)
        elif keys[pg.K_s]:
            self.client.decrease_packet_loss(time_delta)
        elif keys[pg.K_c]:
            self.client.increase_lag_spike(time_delta)
        elif keys[pg.K_x]:
            self.client.decrease_lag_spike(time_delta)

    def _update_player_inputs(self):
        """dd"""
        raw_x, raw_y = pg.mouse.get_pos()
        mouse_x = int(raw_x - self.window.width/2)
        mouse_y = int(raw_y - self.window.height/2)
        self.player.inputs.x, self.player.inputs.y = mouse_x, mouse_y

    def _update_display(self, time_delta):
        """dd"""
        self.window.clear(time_delta)
        if self.window.observer != self.player:
            self.window.set_observer(self.player)

        # draw each player/orb/tracker
        sort_players = sorted(self.players.values(), key=lambda x: x.radius)
        for orb in self.orbs.values():
            self.window.draw_orb(orb)

        for player in sort_players:
            self.window.draw_player(player)
        for tracker in self.trackers.values():
            self.window.draw_tracker(tracker)

        self._draw_scoreboard(sort_players)
        self._draw_statistics(time_delta)
        pg.display.flip()

    def _draw_scoreboard(self, sort_players):
        """dd"""
        # Sets the text position within the window in pixels
        top_left_x, top_left_y, delta_y = self.window.width-235, 15, 30
        for i, text in enumerate(cfg.SCOREBOARD_TEXTS):
            self.window.draw_text(text, top_left_x + 5, top_left_y + 5 + delta_y*i)

        for i, player_name in enumerate(reversed(self.client.leaders)):
            if i not in self.window.scoreboard_texts or self.window.scoreboard_texts[i][0] != text:
                surface = cfg.SCORE_FONT.render(player_name, 1, cfg.BLACK)
                self.window.scoreboard_texts[i] = (text, surface, 210, top_left_y + 5 + delta_y*(i+1), True)
        for _, surface, pos_x, pos_y, x_offset in self.window.scoreboard_texts.values():
            self.window.draw_text(surface, pos_x, pos_y, x_offset)

        self.window.draw_text(cfg.TRACKER_TITLE, top_left_x, top_left_y+200)
        for i, tracker in enumerate(self.trackers.values()):
            if not tracker.active: continue
            self.window.draw_text(tracker.scoreboard_surface, top_left_x+5, top_left_y+230+i*delta_y)

    def _draw_statistics(self, time_delta):
        """dd"""
        top_left_x, top_left_y, delta_y = 10, 15, 40
        for i, text in enumerate(cfg.CLIENT_STATISTICS_TEXTS):
            self.window.draw_text(text, top_left_x + 5, top_left_y + 5 + delta_y*i)
        texts = []
        ping, bw, packet_loss_rate, lag_spike_duration = \
            self.client.get_connection_statistics()
        texts.append(str(int(self.player.radius)-cfg.START_RADIUS))
        texts.append(str(int(1/(time_delta+0.001))))
        texts.append(str(int(bw/100)/10) + " KB/S")
        texts.append(str(int(ping*1000)) + " ms")
        texts.append(str(int(packet_loss_rate)) + " %")
        texts.append(str(round(10*lag_spike_duration)/10) + " s")
        # Sets the text position within the window in pixels
        for i, text in enumerate(texts):
            if i == 1: continue
            if i not in self.window.statistics_texts or self.window.statistics_texts[i][0] != text:
                surface = cfg.SCORE_FONT.render(text, 1, cfg.BLACK)
                if i ==2:
                    surface2 = cfg.SCORE_FONT.render(texts[1], 1, cfg.BLACK)
                    self.window.statistics_texts[1] = (text, surface2, top_left_x + 135, top_left_y + 5 + delta_y)
                self.window.statistics_texts[i] = (text, surface, top_left_x + 135 + 115*(i>=3), top_left_y + 5 + i*delta_y)
        for _, surface, pos_x, pos_y in self.window.statistics_texts.values():
            self.window.draw_text(surface, pos_x, pos_y)
