#!/usr/bin/python
"""This file launches an instance of the server game.

The server player limit, orb density, map size, and bot count is
specified herein.
"""

import sys
import pygame as pg
from server.server_game import ServerGame
import source.config as cfg


def run_server_game(player_limit, bot_count, orb_count, field_size):
    """dd"""
    game = ServerGame(player_limit, bot_count, orb_count, field_size)
    game.start()
    clock = pg.time.Clock()
    while game.is_running():
        time_delta = clock.tick(cfg.SERVER_GAME_REFRESH_RATE)/1000
        game.main_loop(time_delta)


if __name__ == '__main__':
    player_limit = 100
    orb_density = 70
    size_factor = 4
    bot_count = 8
    field_size = (size_factor*cfg.BASE_WIDTH, size_factor*cfg.BASE_HEIGHT)
    run_server_game(player_limit, bot_count, orb_density*(size_factor**2), field_size)
    pg.quit()
    sys.exit()
