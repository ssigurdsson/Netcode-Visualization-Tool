#!/usr/bin/python
"""docstring"""
import sys
import time
import pygame as pg
from client.client_game import ClientMenu, ClientGame
import source.config as cfg


def run_menu():
    """Main Menu Loop"""
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
    """Main Game Loop"""
    game = ClientGame(game_client)
    clock = pg.time.Clock()
    while game.is_running():
    #for _ in range(5000):
        time_delta = clock.tick_busy_loop()/1000
        game.main_loop(time_delta)
    #print(game.timers)
    #[1.4070353507995605, 4.403137445449829, 3.314452886581421, 2.2681710720062256, 3.3067705631256104, 5.698442697525024]
    #[1.2187628746032715, 3.5726335048675537, 3.3383915424346924, 0.522784948348999, 2.639863967895508, 5.75450587272644]
    #[1.4178800582885742, 4.343447685241699, 2.5109705924987793, 3.8210244178771973, 3.1112260818481445, 5.5579423904418945]

    #[1.369136095046997, 4.927754640579224, 3.6072134971618652, 2.555389881134033, 1.941401720046997, 5.358003616333008]
    #[1.1998579502105713, 3.918769121170044, 1.0185401439666748, 4.214473485946655, 1.9316558837890625, 5.435684680938721]
    #[1.0693368911743164, 4.285062074661255, 3.2444913387298584, 0.8165922164916992, 1.9057576656341553, 5.257915496826172]
    #[0.9642481803894043, 2.557734489440918, 1.4440932273864746, 1.4741902351379395, 1.8759758472442627, 5.460699558258057]
    #[1.131120204925537, 2.7621748447418213, 2.7215843200683594, 0.8973803520202637, 1.8948514461517334, 5.424713850021362]
    #[1.2025086879730225, 2.8159642219543457, 2.220928192138672, 1.297339677810669, 1.86061429977417, 5.467870712280273]
    #[1.2126319408416748, 2.956888198852539, 2.8280720710754395, 0.6049087047576904, 1.8532633781433105, 5.545086145401001]
    return game.get_end_state()


if __name__ == "__main__":
    run_menu()
    pg.quit()
    sys.exit()
