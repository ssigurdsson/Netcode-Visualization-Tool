"""docstring"""
import sys
import pygame as pg
import netblob_server_game
from netblob_config import *


def run_server_game():
    """dd"""
    game = netblob_server_game.ServerGame()
    game.start()
    clock = pg.time.Clock()
    while game.is_running():
        time_delta = clock.tick(SERVER_GAME_REFRESH_RATE)/1000
        game.main_loop(time_delta)

if __name__ == '__main__':
    run_server_game()
    pg.quit()
    sys.exit()