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
        self.window = None
        self.display_window()
        self.server = udp_server.Server()
        self.players = {}
        self.orbs = []
        self.player_deaths = []
        self.server_observer = self._get_server_observer()
        self.observers = collections.deque([self.server_observer])
        self.run = False

    def _get_server_observer(self):
        """Hacky way to generalize observer views using the Player class"""
        observer = Player('')
        observer.x, observer.y = WIDTH//2, HEIGHT//2
        observer.scale = WIDTH/DEFAULT_WINDOW_SIZE[0]
        return observer

    def display_window(self, window_size = DEFAULT_WINDOW_SIZE):
        self.window = pg.display.set_mode(window_size, pg.HWSURFACE)
        pg.display.set_caption("Blob Game NetCode Visualization Tool")

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
        self._player_collisions()
        self._ball_collisions()
        if self.server.needs_sync():
            self._replenish_orbs()
            orb_contexts = self._update_local_orbs()
            self._sync_server_players(orb_contexts)
        self._update_display(time_delta)

        for event in pg.event.get():
            self._handle_event(event)

    def _handle_event(self, event):
        if event.type == pg.QUIT:
            self.stop()
        elif self.window and event.type == pg.KEYDOWN:
            if event.key == pg.K_1:
                self.display_window((1024,720))
                self.server_observer.scale = WIDTH/1024
            elif event.key == pg.K_2:
                self.display_window((1366,768))
                self.server_observer.scale = WIDTH/1366
            elif event.key == pg.K_3:
                self.display_window((1920,1080))
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

    def _player_collisions(self):
        """Checks for player collisions and handles those collision"""
        for player_id_1, player_1 in self.players.items():
            for player_id_2, player_2 in self.players.items():
                if player_1.radius <= player_2.radius: continue
                dist = self._find_distance(player_1, player_2)
                if dist < player_1.radius - player_2.radius*COLLISION_MARGIN:
                    player_1.eat(player_2)
                    new_player_2 = Player(player_2.name)
                    self._get_spawn_location(new_player_2)
                    self.player_deaths.append(player_id_2)
                    self.players[player_id_2] = new_player_2
                    self.observers[self.observers.index(player_2)] = new_player_2

    def _ball_collisions(self):
        """Finds and consumes the orbs that collided with players"""
        player_list = list(self.players.values())
        player_list.sort(key=lambda x: x.x - x.radius)
        orb_idx, removed = 0, set()
        for player in player_list:
            while orb_idx < len(self.orbs):
                orb = self.orbs[orb_idx]
                if player.x - player.radius > orb.x + orb.radius:
                    orb_idx += 1
                else: break

            for i in range(orb_idx, len(self.orbs)):
                if orb.x - orb.radius > player.x + player.radius: break
                orb = self.orbs[i]
                dist = self._find_distance(player, orb)
                if dist <= player.radius - orb.radius*COLLISION_MARGIN:
                    if i not in removed:
                        new_area = player.radius**2 + (orb.radius/2)**2
                        player.radius = math.sqrt(new_area)
                    removed.add(i)

        if not removed: return
        left_idx = 0
        for i, orb in enumerate(self.orbs):
            if i in removed: continue
            self.orbs[left_idx], self.orbs[i] = \
                        self.orbs[i], self.orbs[left_idx]
            left_idx += 1
        for _ in range(len(removed)): self.orbs.pop()

    def _replenish_orbs(self):
        """Replenishes the orb population up to the target number of orbs"""
        orb_set = set(self.orbs)
        while len(self.orbs) < TARGET_ORB_NUMBER:
            new_orb = Orb()
            self._get_spawn_location(new_orb)
            if new_orb not in orb_set:
                self.orbs.append(new_orb)
                orb_set.add(new_orb)
        self.orbs.sort(key=lambda x: x.x - x.radius)

    def _get_spawn_location(self, obj):
        """Yields a spawn location outside the body of any other players."""
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

        player_update_queue = self.server.get_player_updates()
        while player_update_queue:
            add, data = player_update_queue.popleft()
            if add:
                player_id, new_player = data
                self._get_spawn_location(new_player)
                self.players[player_id] = new_player
                self.observers.append(new_player)
            else:
                player_id = data
                if player_id in self.players:
                    self.observers.remove(self.players[player_id])
                    self.server.drop_player(player_id)
                    del self.players[player_id]

        player_input_queue = self.server.get_player_inputs()
        while player_input_queue:
            player_id, player_inputs = player_input_queue.popleft()
            if player_id in self.players:
                self.players[player_id].inputs = player_inputs

    def _update_local_orbs(self):
        orb_contexts, player_list = [], []
        for player_id, player in self.players.items():
            player_list.append((self._find_range(player), player_id, player))
        player_list.sort(key=lambda x: x[2].x - x[0][0])

        orb_idx = 0
        for (x_range,y_range), player_id, player in player_list:
            while orb_idx < len(self.orbs):
                if self.orbs[orb_idx].x < player.x - x_range: 
                    orb_idx += 1
                else: break

            orb_context = set()
            for orb in self.orbs[orb_idx:]:
                if orb.x > player.x + x_range: break
                if abs(player.y - orb.y) <= y_range:
                    orb_context.add(orb)
            orb_contexts.append((player_id, orb_context))
        return orb_contexts

    def _find_range(self, player):
        x_range = (player.scale*BASE_WIDTH/2)*FOV_MARGIN
        y_range = (player.scale*BASE_HEIGHT/2)*FOV_MARGIN
        return x_range, y_range

    def _update_display(self, time_delta):
        """Draws each frame at regular intervals"""
        self.window.fill(WHITE)

        # Draw each player/orb/tracker
        sort_players = sorted(self.players.values(), key=lambda x: x.radius)
        for orb in self.orbs: orb.draw(self.window, self.observers[0])
        for player in sort_players: player.draw(self.window, self.observers[0])

        self._draw_scoreboard(sort_players)
        self._draw_statistics(time_delta)
        pg.display.update()

    def _draw_scoreboard(self, sort_players):
        title = SCORE_FONT.render("Scoreboard", 1, BLACK)
        sx, sy = self.window.get_width() - 180, 25
        self.window.blit(title, (sx, sy))

        top_players = sort_players[-5:]
        for i, player in enumerate(reversed(top_players)):
            text = SCORE_FONT.render(str(i+1) + ". " + player.name, 1, BLACK)
            self.window.blit(text, (sx, sy + (i+1)*30))

    def _draw_statistics(self, time_delta):
        # Draws the score and connection statistics
        dx, dy, texts = 10, 15, []
        bw = self.server.get_connection_statistics()
        texts.append(SCORE_FONT.render("Number of players: " \
                    + str(len(self.players)), 1, BLACK))
        texts.append(SCORE_FONT.render("FPS: " \
                    + str(int(1/(time_delta+0.001))), 1, BLACK))
        texts.append(SCORE_FONT.render("Bandwidth: " \
                    + str(int(bw/100)/10) + " KB/S", 1, BLACK))
        for i, text in enumerate(texts): 
            self.window.blit(text, (dx, dy + i*40))