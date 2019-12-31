#!/usr/bin/python
"""docstring"""
import sys
import pygame as pg
import server.server_game
import source.config as cfg


def run_server_game(player_limit, bot_count, orb_count, field_size):
    """dd"""
    game = server.server_game.ServerGame(
        player_limit, bot_count, orb_count, field_size)
    game.start()
    clock = pg.time.Clock()
    while game.is_running():
        time_delta = clock.tick(cfg.SERVER_GAME_REFRESH_RATE)/1000
        game.main_loop(time_delta)
    print(game.timers)

if __name__ == '__main__':
    player_limit = 200
    orb_density = 80
    size_factor = 4
    bot_count = 8
    field_size = (size_factor*cfg.BASE_WIDTH, size_factor*cfg.BASE_HEIGHT)
    run_server_game(player_limit, bot_count, orb_density*(size_factor**2), field_size)
    pg.quit()
    sys.exit()
