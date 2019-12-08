"""docstring"""
import sys
import pygame as pg
import netblob_client_game
from netblob_config import *


def run_menu():
    """Main Menu Loop"""
    game_menu = netblob_client_game.ClientMenu()
    clock = pg.time.Clock()
    while game_menu.is_running():
        clock.tick(MENU_REFRESH_RATE)

        if game_menu.play_game():
            client = game_menu.get_client()
            game_menu.collapse_menu()
            end_game_state = run_game(client)
            game_menu.resume_menu(end_game_state)

        game_menu.main_loop()

def run_game(client):
    """Main Game Loop"""
    game = netblob_client_game.ClientGame(client)
    clock = pg.time.Clock()
    while game.is_running():
        time_delta = clock.tick_busy_loop()/1000
        game.main_loop(time_delta)
    return game.get_end_state()

if __name__ == '__main__':
    run_menu()
    pg.quit()
    sys.exit()