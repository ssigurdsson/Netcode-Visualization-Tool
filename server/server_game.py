"""Provides a server game interface for handling of game logic."""

import collections
import math
import random
import pygame as pg
import source.config as cfg
from source.entities import Player, Orb
from source.animation import GameWindow
from server.server import Server


class CellContainer:
    """Provides a container that stores items in a cell grid.

    This type of container is useful for extracting neighboring items from
    the local environments of items without iterating through the entire
    collection of items. Note that each item may occupy several cells.

    Attributes:
        item_count: Tracks the number of items stored in the container.
    """
    def __init__(self, map_size):
        """Initializes the container with a map size defined by map_size.
        
        The cell grid expands to fill in the entire map.
        """
        self.cell_width, self.cell_height = cfg.MAP_CELL_SIZE
        self.item_count = 0
        self.cells = []
        map_width, map_height = map_size
        for _ in range(map_height//self.cell_height + 1):
            new_row = [set() for _ in range(map_width//self.cell_width + 1)]
            self.cells.append(new_row)

    def __iter__(self):
        for row in self.cells:
            for cell in row:
                yield from cell

    def find_cell(self, x, y):
        row, col = int(y/self.cell_height), int(x/self.cell_width)
        return (max(0, min(len(self.cells)-1, row)),
                max(0, min(len(self.cells[0])-1, col)))

    def add(self, item):
        top, left = item.y - item.radius, item.x - item.radius
        top_row, left_col = self.find_cell(left, top)
        bot, right = item.y + item.radius, item.x + item.radius
        bot_row, right_col = self.find_cell(right, bot)
        self.item_count += 1
        for row in range(top_row,bot_row+1):
            for col in range(left_col,right_col+1):
                cell = self.cells[row][col]
                cell.add(item)

    def remove(self, item):
        top, left = item.y - item.radius, item.x - item.radius
        top_row, left_col = self.find_cell(left, top)
        bot, right = item.y + item.radius, item.x + item.radius
        bot_row, right_col = self.find_cell(right, bot)
        self.item_count -= 1
        for row in range(top_row,bot_row+1):
            for col in range(left_col,right_col+1):
                cell = self.cells[row][col]
                cell.discard(item)

    def get_neighbours(self, item, x_range, y_range):
        neighbours = set()
        row, col = self.find_cell(item.x, item.y)
        delta_x = int(x_range/self.cell_width)*cfg.FOV_MARGIN
        delta_y = int(y_range/self.cell_height)*cfg.FOV_MARGIN
        top, left = item.y - y_range, item.x - x_range
        top_row, left_col = self.find_cell(left, top)
        bot, right = item.y + y_range, item.x + x_range
        bot_row, right_col = self.find_cell(right, bot)
        for row in range(top_row,bot_row+1):
            for col in range(left_col,right_col+1):
                neighbours |= self.cells[row][col]
        return neighbours


class ServerGame:
    """Handles all game logic on the server side.
    
    The main_loop function updates the entire game state for a given
    time interval, and updates the display. The game state is regularly
    communicated to clients through a Server instance, which handles all
    client interactions. The game state consists of a collection of
    players and orbs at different coordinates within a game map.
    """
    def __init__(self, player_limit, bot_count, target_orb_count, map_size):
        self.player_limit = player_limit
        self.target_orb_count = target_orb_count
        self.map_size = map_size
        self.bot_id = 0
        self.server = Server(map_size)
        self.id_to_player = {}
        self.leaders = []
        self.players = CellContainer(map_size)
        self.orbs = CellContainer(map_size)
        self.orb_id = 0
        self.server_observer = self._get_server_observer()
        self.window = GameWindow(self.server_observer, "NetBlob - Server", map_size)
        self.observers = collections.deque([self.server_observer])
        self._generate_bots(bot_count)
        self.run = False

    def _get_server_observer(self):
        """Hacky way to generalize observer views using the Player class"""
        observer = Player('', 0, self.map_size)
        observer.x, observer.y = self.map_size[0]//2, self.map_size[1]//2  # Centers the view
        observer.scale = self.map_size[0]/cfg.DEFAULT_WINDOW_SIZE[0]  # Sets the view scale
        return observer

    def _generate_bots(self, bot_count):
        while self.bot_id > -bot_count:
            self.bot_id -= 1
            bot = Player(
                cfg.BOT_NAMES[self.bot_id%len(cfg.BOT_NAMES)],
                self.bot_id, self.map_size)
            self._update_bot_inputs(bot)
            bot.radius = random.randint(cfg.START_RADIUS, cfg.MAX_RADIUS//3)
            bot.scale = math.pow(bot.radius/cfg.START_RADIUS, cfg.VIEW_GROWTH_RATE)
            self._add_player(bot)

    def _update_bot_inputs(self, bot):
        map_x, map_y = self.map_size
        bias_x = int(bot.x - map_x//2)
        bias_y = int(bot.y -  map_y//2)
        
        bot.inputs.x = random.randint(
            -map_x-bias_x, map_x-bias_x)
        bot.inputs.y = random.randint(
            -map_y-bias_y, map_y-bias_y)

    def _handle_bot_death(self, bot):
        self.bot_id -= 1
        bot.id = self.bot_id

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
        for player in self.id_to_player.values():
            self.players.remove(player)
            player.move(self.map_size, time_delta)
            self.players.add(player)

        self._handle_player_collisions()
        self._handle_orb_collisions()
        if self.server.needs_sync():
            self._sync_server_players()
            for player in self.id_to_player.values():
                if player.id < 0 and random.randrange(15) == 0:
                    self._update_bot_inputs(player)
        self._update_display(time_delta, self.id_to_player.values(), self.orbs)

        for event in pg.event.get():
            self._handle_event(event)

    def _handle_event(self, event):
        if event.type == pg.QUIT:
            self.stop()
        elif self.window and event.type == pg.KEYDOWN:
            if event.key == pg.K_1:
                self.window.set_size((1024,720))
                self.server_observer.scale = self.map_size[0]/1024
            elif event.key == pg.K_2:
                self.window.set_size((1366,768))
                self.server_observer.scale = self.map_size[0]/1366
            elif event.key == pg.K_3:
                self.window.set_size((1920,1080))
                self.server_observer.scale = self.map_size[0]/1920
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
        for player in self.id_to_player.values():
            neighbours = self.players.get_neighbours(
                player, player.radius, player.radius)
            for other_player in neighbours:
                if other_player == player: continue
                if player.radius >= other_player.radius: continue
                dist = player.find_distance(other_player)
                margin = player.radius*cfg.COLLISION_MARGIN
                if dist < other_player.radius - margin:
                    other_player.eat(player)
                    self._reset_player(player)
                    self.players.remove(player)
                    self._give_spawn_location(player)
                    self.players.add(player)
                    self.id_to_player.pop(player.id)
                    if player.id > 0:
                        self.server.sync_player_death(player)
                    else:
                        self._handle_bot_death(player)
                    self.id_to_player[player.id] = player
                    break

    def _reset_player(self, player):
        player.color_idx = random.randrange(
            len(cfg.PLAYER_PALETTE))
        player.radius = cfg.START_RADIUS
        player.scale = math.pow(
            player.radius/cfg.START_RADIUS,
            cfg.VIEW_GROWTH_RATE)

    def _handle_orb_collisions(self):
        for player in self.id_to_player.values():
            neighbours = self.orbs.get_neighbours(
                player, player.radius, player.radius)
            removed = []
            for orb in neighbours:
                dist = player.find_distance(orb)
                margin = orb.radius*cfg.COLLISION_MARGIN
                if dist < player.radius - margin:
                    player.eat(orb)
                    removed.append(orb)
            for orb in removed:
                self.orbs.remove(orb)
            if removed and player.id < 0:
                if random.randrange(3) == 0:
                    self._update_bot_inputs(player)
        self._replenish_orbs()

    def _replenish_orbs(self):
        """Replenishes the orb population up to the target number of orbs"""
        while self.orbs.item_count < self.target_orb_count:
            self.orb_id += 1
            new_orb = Orb(orb_id = self.orb_id)
            self._give_spawn_location(new_orb)
            self.orbs.add(new_orb)

    def _give_spawn_location(self, obj):
        """Yields a spawn location outside the body of any other player"""
        # Has the potential to freeze up
        field_width, field_height = self.map_size
        while True:
            obj.x, obj.y = random.randrange(field_width), random.randrange(field_height)
            row, col = self.players.find_cell(obj.x, obj.y)
            cell = self.players.cells[row][col]
            if all(player.find_distance(obj) > player.radius for player in cell):
                break

    def _get_item_views(self):
        player_views, orb_views = [], []
        for player in self.id_to_player.values():
            if player.id < 0: continue
            x_range = (player.scale*cfg.BASE_WIDTH/2)
            y_range = (player.scale*cfg.BASE_HEIGHT/2)
            player_neighbours = self.players.get_neighbours(
                player, x_range, y_range)
            orb_neighbours = self.orbs.get_neighbours(
                player, x_range, y_range)
            player_views.append((player.id, player_neighbours))
            orb_views.append((player.id, orb_neighbours))
        return player_views, orb_views

    def _add_player(self, new_player):
        self._give_spawn_location(new_player)
        self.id_to_player[new_player.id] = new_player
        self.players.add(new_player)
        self.observers.append(new_player)

    def _sync_server_players(self):
        """f"""
        player_views, orb_views = self._get_item_views()
        self.server.sync_state(self.leaders, player_views, orb_views)

        player_remove_queue = self.server.get_player_removals()
        while player_remove_queue:
            player_id = player_remove_queue.popleft()
            if player_id in self.id_to_player:
                self.observers.remove(self.id_to_player[player_id])
                self.players.remove(self.id_to_player[player_id])
                del self.id_to_player[player_id]
                self.server.drop_player_connection(
                    player_id, cfg.PLAYER_DISCONNECTED_MESSAGE)

        player_add_queue = self.server.get_player_additions()
        while player_add_queue:
            player_id, player_name = player_add_queue.popleft()
            if player_id in self.id_to_player:
                player = self.id_to_player[player_id]
                self.server.approve_player_connection(player_id, player)
            elif len(self.id_to_player) < self.player_limit:
                new_player = Player(player_name, player_id)
                self._add_player(new_player)
                self.server.approve_player_connection(player_id, new_player)
            else:
                self.server.drop_player_connection(
                    player_id, cfg.SERVER_FULL_MESSAGE)

        player_input_queue = self.server.get_player_inputs()
        while player_input_queue:
            player_id, player_inputs = player_input_queue.popleft()
            if player_id in self.id_to_player:
                self.id_to_player[player_id].inputs = player_inputs

    def _update_display(self, time_delta, players, orbs):
        """Draws each frame at regular intervals"""
        self.window.clear(time_delta)
        if self.window.observer != self.observers[0]:
            self.window.set_observer(self.observers[0])

        sort_players = sorted(players, key=lambda x: x.radius)
        # Draw each player/orb/tracker
        for orb in orbs:
            self.window.draw_orb(orb)
        for player in sort_players:
            self.window.draw_player(player)

        self._draw_scoreboard(sort_players)
        self._draw_statistics(time_delta)
        pg.display.flip()

    def _draw_scoreboard(self, sort_players):
        """d"""
        # Sets the text position within the window in pixels
        top_left_x, top_left_y, delta_y = self.window.width-205, 15, 30
        for i, text in enumerate(cfg.SCOREBOARD_TEXTS):
            self.window.draw_text(text, top_left_x + 5, top_left_y + 5 + delta_y*i)
        self.leaders = sort_players[-5:]
        for i, player in enumerate(reversed(self.leaders)):
            self.window.draw_text(player.scoreboard_surface, top_left_x + 30, 50 + delta_y*i)

    def _draw_statistics(self, time_delta):
        """d"""
        top_left_x, top_left_y, delta_y = 15, 15, 40
        for i, text in enumerate(cfg.SERVER_STATISTICS_TEXTS):
            self.window.draw_text(text, top_left_x + 5, top_left_y + 5 + delta_y*i)
        texts = []
        bandwidth, = self.server.get_connection_statistics()
        texts.append(str(len(self.id_to_player)))
        texts.append(str(int(1/(time_delta+0.001))))
        texts.append(str(int(bandwidth/100)/10) + " KB/S")
        # Sets the text position within the window in pixels
        for i, text in enumerate(texts):
            if i not in self.window.statistics_texts or self.window.statistics_texts[i][0] != text:
                surface = cfg.SCORE_FONT.render(text, 1, cfg.BLACK)
                self.window.statistics_texts[i] = (text, surface, top_left_x + 125, top_left_y + 5 + i*delta_y)
        for _, surface, pos_x, pos_y in self.window.statistics_texts.values():
            self.window.draw_text(surface, pos_x, pos_y)
