"""Specifies constants and initializes various font elements."""

import math
import os
import sys
import pygame as pg
os.environ["SDL_VIDEO_CENTERED"] = '1'
pg.font.init()

NAME_FONT = pg.font.SysFont("gillsans", 20)
SCORE_FONT = pg.font.SysFont("gillsans", 23)
SCORE_FONT_2 = pg.font.SysFont("gillsans", 21)
TITLE_FONT = pg.font.SysFont("gillsans", 20)
MENU_FONT_1 = pg.font.SysFont("gillsans", 28)
MENU_FONT_2 = pg.font.SysFont("gillsans", 24)
MENU_FONT_3 = pg.font.SysFont("gillsans", 16)

# Color definitions
WHITE = (255,255,255)
LIGHT_GRAY = (220,220,220)
GRAY = (80,80,80)
BLACK = (0,0,0)
RED = (250,0,0)
BLUE = (0,0,250)
LIGHT_GREEN = (80, 255, 80)
DARK_GRAY = (20, 20, 20)
PAST_PLAYER_COLOR = (0,0,255)
SERVER_PLAYER_COLOR = (255,0,0)
ORB_PALETTE = [(255,0,0), (255, 0, 255), (128,255,0),
                (0,255,0), (0,255,128), (0, 128, 255),
                (0,0,255), (0,0,255), (128,0,255)]
PLAYER_PALETTE = [(255,64,128), (255, 128, 0), (128,255,0),
                  (0,255,128), (128, 128, 255), (128,255,255),
                  (255,128,255), (255,255,110), (255,128,255)
                 ]
BORDER_PALETTE = [(max(0,c1-10),max(0,c2-10),max(0,c3-10)) \
        for c1,c2,c3 in PLAYER_PALETTE]
MENU_WINDOW_SIZE = (1024,720)
DEFAULT_WINDOW_SIZE = (1366,768)

TEXT_SPACING = 30
SCOREBOARD_TEXTS = [SCORE_FONT.render("Scoreboard", 1, (0,0,0))]
for i in range(1,6):
    SCOREBOARD_TEXTS.append(SCORE_FONT.render(str(i) + ". ", 1, (0,0,0)))

texts = ["Players: ", "Frame Rate: ", "Data Usage: "]
SERVER_STATISTICS_TEXTS = []
for i, text in enumerate(texts):
    SERVER_STATISTICS_TEXTS.append(SCORE_FONT.render(text, 1, (0,0,0)))
texts = ["Player Score: ", "Frame Rate: ", "Data Usage: ", "[W / E] Round Trip Time: ", "[S / D]  Packet loss rate: ","[X / C]  Spike duration: "]
CLIENT_STATISTICS_TEXTS = []
for i, text in enumerate(texts):
    CLIENT_STATISTICS_TEXTS.append(SCORE_FONT.render(text, 1, (0,0,0)))

TRACKER_TITLE = SCORE_FONT.render("Trackers:", 1, (0,0,0))

# Game related constants
BASE_WIDTH, BASE_HEIGHT = 2560, 1440  # Defines the visible range for each player
VIEW_GROWTH_RATE = 0.30

MAX_NAME_LENGTH = 12
BORDER_SIZE = 10
BASE_VELOCITY = 500  # Player velocity in Units per second
VELOCITY_SLOW_FACTOR = 0.4

MIN_ORB_RADIUS = 18  # Size of the orbs in units
MAX_ORB_RADIUS = 20
EAT_VALUE_OFFSET = 10
MAP_CELL_SIZE = (600,600)
MASS_LOSS_RATE = 1/100000
START_RADIUS = 50
MAX_RADIUS = 1200
BOT_NAMES = ["Google", "Apple", "Facebook", "Amazon", "Microsoft", "Twitter", "Netflix", "Uber"]
BOT_INPUT_UPDATE_INTERVAL = 2

CLIENT_GAME_REFRESH_RATE = 0  # 0 means unlimited
MENU_REFRESH_RATE = 30
SERVER_GAME_REFRESH_RATE = 50

COLLISION_MARGIN = 0.6 # Smoothens collision checking
FOV_MARGIN = 1.1  # Margin
GRAVITY_FACTOR = 2
VIEW_SCALE_RATE = 1.6

# Networking related constants
STATS_PROBE_INTERVAL = 0.3
CONNECTION_ATTEMPT_INTERVAL = 1/5
CONNECTION_ATTEMPTS = 10
NOT_RESPONDING_TIME = 1
LAG_SPIKE_INTERVAL = 10
ACK_TIMEOUT = 1

TIMEOUT_LIMIT = 5  # Kick player if no heartbeat recieved for this interval (seconds)
PLAYER_INTERRUPT_LIMIT = 1  # Return the player commands to default if player ping spikes above this limit
SERVER_SYNC_INTERVAL = 1/20
CLIENT_SYNC_INTERVAL = 1/60
ACK_INTERVAL = 1/10
PLAYER_LIMIT = 100
CONNECTION_PROBE_INTERVAL = 0.2

CONNECT_CODE = 1
INPUTS_CODE = 2
UPD_PLAYERS_CODE = 3
UPD_ORBS_CODE = 4
ACK_CODE = 5
PING_CODE = 6
DEATH_CODE = 7
DISCONNECT_CODE = 8

PLAYER_DISCONNECTED_MESSAGE = "Player Disconnected."
NOT_CONNECTED_MESSAGE = "Server Connection Interrupted."
SERVER_FULL_MESSAGE = "Server is full. Try again later."

NETWORK_PORT = 5562
