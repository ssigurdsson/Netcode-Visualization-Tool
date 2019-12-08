"""Provides encoding and decoding functions for objects
transmitted over the network.

"""
from netblob_config import *
from netblob_entities import Player, Orb, UserInputs


def encode_inputs(inputs):
    return (int(inputs.x), int(inputs.y))

def decode_inputs(encoded_inputs):
    mouse_x, mouse_y = encoded_inputs
    assert(isinstance(mouse_x,int) and isinstance(mouse_y,int))
    return UserInputs((mouse_x, mouse_y))

def encode_player(player):
    return (player.name, int(player.x), int(player.y), player.color_idx, \
            int(player.radius), encode_inputs(player.inputs))
    
def decode_player(encoded_player):
    name, x, y, color_idx, radius, inputs = encoded_player
    assert(isinstance(name, str) and len(name) <= MAX_NAME_LENGTH)
    assert(isinstance(x, int) and isinstance(y, int))
    assert(0 <= x < WIDTH and 0 <= y < HEIGHT)
    assert(isinstance(color_idx, int))
    assert(0 <= color_idx < len(PLAYER_PALETTE))
    assert(isinstance(radius, int))
    assert(START_RADIUS <= radius < HEIGHT//2)
    decoded_player = Player(name, (x,y), radius)
    decoded_player.inputs = decode_inputs(inputs)
    decoded_player.color_idx = color_idx
    return decoded_player

def encode_orb(orb):
    return (orb.x, orb.y)

def decode_orb(encoded_orb):
    x, y = encoded_orb
    assert(isinstance(x, int) and isinstance(y, int))
    assert(0 <= x < WIDTH and 0 <= y < HEIGHT)
    return Orb((x,y))