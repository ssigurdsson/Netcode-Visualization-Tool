"""Creates an instance of the game on a local server."""
import os
import pygame as pg
import udp_server
from core_game import Player, Orb
from config import *
import time
import random
import math
import collections


class ServerGame:

    def __init__(self):
        os.environ["SDL_VIDEO_CENTERED"] = '1'
        self.window = self._get_window(DEFAULT_WINDOW_SIZE)
        self.server = udp_server.Server()
        self.players = {}
        self.orbs = []
        self.player_deaths = set()
        self.server_observer = self._get_server_observer()
        self.observers = collections.deque([self.server_observer])
        self.run = False

    def _get_server_observer(self):
        """Hacky way to generalize observer views using the Player class"""
        observer = Player('')
        observer.x, observer.y = WIDTH//2, HEIGHT//2  # Centers the view
        observer.scale = WIDTH/DEFAULT_WINDOW_SIZE[0]  # Expands the view
        return observer

    def _get_window(self, window_size):
        window = pg.display.set_mode(window_size, pg.HWSURFACE)
        pg.display.set_caption("Blob Game Server")
        return window

    def start(self):
        if not self.run:
            self.run = True
            self.server.start()

    def stop(self):
        self.run = False
        self.server.stop()

    def is_running(self):
        return self.run

    def main_loop(self, time_delta):
        """Main function that maintains and updates the game state"""
        for player in self.players.values(): player.move(time_delta)
        self._handle_player_collisions()
        self._handle_ball_collisions()
        if self.server.needs_sync():
            self._replenish_orbs()
            orb_contexts = self._get_orb_contexts()
            self._sync_server_players(orb_contexts)
        self._update_display(time_delta)

        for event in pg.event.get():
            self._handle_event(event)

    def _handle_event(self, event):
        if event.type == pg.QUIT:
            self.stop()
        elif self.window and event.type == pg.KEYDOWN:
            if event.key == pg.K_1:
                self.window = self._get_window((1024,720))
                self.server_observer.scale = WIDTH/1024
            elif event.key == pg.K_2:
                self.window = self._get_window((1366,768))
                self.server_observer.scale = WIDTH/1366
            elif event.key == pg.K_3:
                self.window = self._get_window((1920,1080))
                self.server_observer.scale = WIDTH/1920
        elif event.type == pg.MOUSEBUTTONDOWN:
            if event.button == 1:
                self._advance_observer()
            if event.button == 3:
                self._roll_back_observer()

    def _advance_observer(self):
        self.observers.append(self.observers.popleft())

    def _roll_back_observer(self):
        self.observers.appendleft(self.observers.pop())

    def _handle_player_collisions(self):
        """Checks for player collisions and handles those collision"""
        for player_id_1, player_1 in self.players.items():
            for player_id_2, player_2 in self.players.items():
                if player_1.radius <= player_2.radius: continue
                dist = self._find_distance(player_1, player_2)
                if dist < player_1.radius - player_2.radius*COLLISION_MARGIN:
                    player_1.eat(player_2)
                    new_player_2 = Player(player_2.name)
                    self._give_spawn_location(new_player_2)
                    self.player_deaths.add(player_id_2)
                    self.players[player_id_2] = new_player_2
                    obs_idx = self.observers.index(player_2)
                    self.observers[obs_idx] = new_player_2

    def _handle_ball_collisions(self):
        """Finds and consumes the orbs that collided with players"""
        player_list = list(self.players.values())
        player_list.sort(key=lambda x: x.x - x.radius)
        left_orb_idx, removed = 0, set()
        for player in player_list:
            while left_orb_idx < len(self.orbs):
                if self.orbs[left_orb_idx].x < player.x - player.radius:
                    left_orb_idx += 1
                else: break

            for i in range(left_orb_idx, len(self.orbs)):
                orb = self.orbs[i]
                if orb.x > player.x + player.radius: break
                dist = self._find_distance(player, orb)
                if dist <= player.radius - orb.radius*COLLISION_MARGIN:
                    if i not in removed: player.eat(orb)
                    removed.add(i)

        new_orbs = []
        for i, orb in enumerate(self.orbs):
            if i not in removed: new_orbs.append(orb)
        self.orbs = new_orbs

    def _replenish_orbs(self):
        """Replenishes the orb population up to the target number of orbs"""
        orb_set = set(self.orbs)
        while len(self.orbs) < TARGET_ORB_NUMBER:
            new_orb = Orb()
            self._give_spawn_location(new_orb)
            if new_orb not in orb_set:
                self.orbs.append(new_orb)
                orb_set.add(new_orb)
        self.orbs.sort(key=lambda x: x.x - x.radius)

    def _give_spawn_location(self, obj):
        """Yields a spawn location outside the body of any other player"""
        # Will this freeze up?
        while True:
            obj.x, obj.y = random.randrange(WIDTH), random.randrange(HEIGHT)
            for player in self.players.values():
                distance = self._find_distance(obj, player)
                if distance < player.radius + obj.radius: break
            else: break

    def _find_distance(self, obj1, obj2):
        dx, dy = (obj1.x-obj2.x), (obj1.y-obj2.y)
        return math.sqrt(dx*dx + dy*dy)

    def _sync_server_players(self, orb_contexts):
        """f"""
        self.server.sync_state(self.players, orb_contexts, self.player_deaths)
        self.player_deaths.clear()

        player_remove_queue = self.server.get_player_removals()
        while player_remove_queue:
            player_id = player_remove_queue.popleft()
            if player_id in self.players:
                self.observers.remove(self.players[player_id])
                self.server.drop_player(player_id)
                del self.players[player_id]

        player_add_queue = self.server.get_player_additions()
        while player_add_queue:
            player_id, new_player = player_add_queue.popleft()
            self._give_spawn_location(new_player)
            self.players[player_id] = new_player
            self.observers.append(new_player)

        player_input_queue = self.server.get_player_inputs()
        while player_input_queue:
            player_id, player_inputs = player_input_queue.popleft()
            if player_id in self.players:
                self.players[player_id].inputs = player_inputs

    def _get_orb_contexts(self):
        """d"""
        orb_contexts, player_list = [], []
        for player_id, player in self.players.items():
            x_range, y_range = self._get_player_view_range(player)
            player_list.append((x_range, y_range, player_id, player))
        player_list.sort(key=lambda x: x[3].x - x[0])

        left_orb_idx = 0
        for x_range, y_range, player_id, player in player_list:
            while left_orb_idx < len(self.orbs):
                if self.orbs[left_orb_idx].x < player.x - x_range:
                    left_orb_idx += 1
                else: break

            orb_context = set()
            for orb in self.orbs[left_orb_idx:]:
                if orb.x > player.x + x_range: break
                if abs(player.y - orb.y) <= y_range:
                    orb_context.add(orb)
            orb_contexts.append((player_id, orb_context))
        return orb_contexts

    def _get_player_view_range(self, player):
        x_range = (player.scale*BASE_WIDTH/2)*FOV_MARGIN
        y_range = (player.scale*BASE_HEIGHT/2)*FOV_MARGIN
        return x_range, y_range

    def _update_display(self, time_delta):
        """Draws each frame at regular intervals"""
        self.window.fill(WHITE)

        # Draw each player/orb/tracker
        sort_players = sorted(self.players.values(), key=lambda x: x.radius)
        for orb in self.orbs:
            orb.draw(self.window, self.observers[0])
        for player in sort_players:
            player.draw(self.window, self.observers[0])

        self._draw_scoreboard(sort_players)
        self._draw_statistics(time_delta)
        pg.display.update()

    def _draw_scoreboard(self, sort_players):
        """d"""
        # Sets the text position within the window in pixels
        top_left_x, top_left_y, delta_y = self.window.get_width()-180, 25, 30
        title = SCORE_FONT.render("Scoreboard", 1, BLACK)
        self.window.blit(title, (top_left_x, top_left_y))

        top_players = sort_players[-5:]
        for i, player in enumerate(reversed(top_players)):
            text = SCORE_FONT.render(str(i+1) + ". " + player.name, 1, BLACK)
            self.window.blit(text, (top_left_x, top_left_y + (i+1)*delta_y))

    def _draw_statistics(self, time_delta):
        """d"""
        texts = []
        bandwidth, = self.server.get_connection_statistics()
        texts.append(SCORE_FONT.render("Number of players: " \
                    + str(len(self.players)), 1, BLACK))
        texts.append(SCORE_FONT.render("FPS: " \
                    + str(int(1/(time_delta+0.001))), 1, BLACK))
        texts.append(SCORE_FONT.render("Bandwidth: " \
                    + str(int(bandwidth/100)/10) + " KB/S", 1, BLACK))
        # Sets the text position within the window in pixels
        top_left_x, top_left_y, delta_y = 10, 15, 40
        for i, text in enumerate(texts): 
            self.window.blit(text, (top_left_x, top_left_y + i*delta_y))