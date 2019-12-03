"""docstring"""
import sys
import pygame as pg
import client_game
import time
clock = pg.time.Clock()

def run_menu():
    """Main Menu Loop."""
    game_menu = client_game.ClientMenu()
    while game_menu.is_running():
        clock.tick(30)

        if game_menu.play_game():
            client = game_menu.get_client()
            game_menu.collapse_window()
            end_game_state = run_game(client)
            game_menu.display_window(end_game_state)

        game_menu.main_loop()

def run_game(client):
    """Main Game Loop."""
    game = client_game.ClientGame(client)
    while game.is_running():
        time_delta = clock.tick_busy_loop()/1000
        game.main_loop(time_delta)
    return game.get_end_state()

if __name__ == '__main__':
    run_menu()
    pg.quit()
    sys.exit()