""""""
import pygame as pg
pg.font.init()

SCALE_FACTOR = 1
BASE_WIDTH, BASE_HEIGHT = SCALE_FACTOR*2560, SCALE_FACTOR*1440
WIDTH, HEIGHT = 4*BASE_WIDTH, 4*BASE_HEIGHT  # Defines the size of the playing field in units
DEFAULT_WINDOW_SIZE = (1366,768)
# CONSTANTS relating to the gameplay and UI.
BORDER_SIZE = 10
START_VELOCITY = SCALE_FACTOR*500  # Player velocity in Units per second
MIN_VELOCITY = SCALE_FACTOR*180
VEL_DROP_OFF = SCALE_FACTOR*1

NAME_FONT = pg.font.SysFont("gillsans", 20)
SCORE_FONT = pg.font.SysFont("gillsans", 23)
SCORE_FONT_2 = pg.font.SysFont("gillsans", 21)
TITLE_FONT = pg.font.SysFont("gillsans", 20)
MENU_FONT_1 = pg.font.SysFont("gillsans", 28)
MENU_FONT_2 = pg.font.SysFont("gillsans", 24)
MENU_FONT_3 = pg.font.SysFont("gillsans", 16)

WHITE = (250,250,250)
LIGHT_GRAY = (220,220,220)
GRAY = (80,80,80)
BLACK = (0,0,0)
RED = (250,0,0)
BLUE = (0,0,250)
LIGHT_GREEN = (80, 255, 80)
DARK_GRAY = (20, 20, 20)
ORB_PALETTE = [(255,0,0), (255, 128, 0), (128,255,0),
				(0,255,0), (0,255,128), (0, 128, 255),
				(0,0,255), (0,0,255), (128,0,255),
				(255,0,128)]
PLAYER_PALETTE = [(255,0,0), (255, 128, 0), (128,255,0),
				(0,255,0), (0,255,128), (0, 128, 255),
				(0,0,255), (0,0,255), (128,0,255),
				(255,0,128)]
BORDER_PALETTE = [(max(0,c1-10),max(0,c2-10),max(0,c3-10)) for c1,c2,c3 in PLAYER_PALETTE]
PAST_PLAYER_COLOR = (0,0,255)
SERVER_PLAYER_COLOR = (255,0,0)

MIN_ORB_RADIUS = SCALE_FACTOR*17  # Size of the orbs in units
MAX_ORB_RADIUS = SCALE_FACTOR*18
START_RADIUS = SCALE_FACTOR*50
ORB_VARIANCE = 3

ORB_REPLENISH_TIME = 1  # Interval between orb replenishments in seconds
ORB_REFRESH_INTERVAL = 1

SERVER_GAME_REFRESH_RATE = 50  # The number of times the game state refreshes per second on the server side
COLLISION_MARGIN = 0.5  # Smoothens collision checking
TARGET_ORB_NUMBER = 1250  # Target number of orbs in play
FOV_MARGIN = 1.5  # Margin

DEFAULT_IP = "192.168.1.158"
NETWORK_PORT = 5562

CONNECTION_INTERVAL = 1/5
CONNECTION_ATTEMPTS = 10
NOT_RESPONDING_TIME = 1
LAG_SPIKE_INTERVAL = 10
TRANSMIT_INTERVAL = 1/60
ACK_TIMEOUT = 1

TIMEOUT_LIMIT = 4  # Kick player if no heartbeat recieved for this interval (seconds)
PLAYER_INTERRUPT_LIMIT = 1  # Return the player commands to default if player ping spikes above this limit
SERVER_TRANSMIT_INTERVAL = 1/20
CLIENT_TRANSMIT_INTERVAL = 1/60
ACK_INTERVAL = 1/10
PLAYER_LIMIT = 100
CONNECTION_PROBE_INTERVAL = 0.2

CONNECT_CODE = 0
KEY_PRESSES_CODE = 1
UPDATE_PLAYERS_CODE = 2
UPDATE_ORBS_CODE = 3
ACK_CODE = 4
PING_CODE = 5
PLAYER_DEATH_CODE = 6
DISCONNECT_CODE = 7

NAME_MAX_LENGTH = 10