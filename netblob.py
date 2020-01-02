#!/usr/bin/python
"""This file launches an instance of the client game."""

import sys
import pygame as pg
from client.client_game import ClientMenu, ClientGame
import source.config as cfg


def run_menu():
    """Runs the client main menu."""
    game_menu = ClientMenu()
    clock = pg.time.Clock()
    while game_menu.is_running():
        clock.tick(cfg.MENU_REFRESH_RATE)

        if game_menu.play_game():
            game_client = game_menu.get_client()
            game_menu.collapse_menu()
            end_game_state = run_game(game_client)
            game_menu.resume_menu(end_game_state)

        game_menu.main_loop()

def run_game(game_client):
    """Runs the client game.

    Args:
        game_client: An instance of the client game.
    Returns:
        game.get_end_state(): A string representing the reason the game ended.
    """
    game = ClientGame(game_client)
    clock = pg.time.Clock()
    while game.is_running():
        time_delta = clock.tick_busy_loop(cfg.CLIENT_GAME_REFRESH_RATE)/1000
        game.main_loop(time_delta)
    return game.get_end_state()


if __name__ == "__main__":
    run_menu()
    pg.quit()
    sys.exit()
