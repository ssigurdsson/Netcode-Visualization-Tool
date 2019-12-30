"""Provides encoding and decoding functions for objects
transmitted over the network.

"""
import source.config as cfg
from source.entities import Player, Orb, UserInputs


def decode_name(player_name):
    assert(isinstance(player_name, str))
    assert(len(player_name) <= cfg.MAX_NAME_LENGTH)
    return player_name

def encode_inputs(inputs):
    return (inputs.x, inputs.y)

def decode_inputs(encoded_inputs):
    mouse_x, mouse_y = encoded_inputs
    assert(isinstance(mouse_x,int) and isinstance(mouse_y,int))
    return UserInputs((mouse_x, mouse_y))

def encode_player(player):
    return (player.name, player.id, player.field_size,
            int(player.x), int(player.y), player.color_idx,
            int(player.radius), encode_inputs(player.inputs))

def decode_player(player):
    name, player_id, field_size, x, y, color_idx, radius, inputs = player
    field_width, field_height = field_size
    assert(isinstance(player_id, int))
    assert(isinstance(field_width, int) and field_width > 0)
    assert(isinstance(field_height, int) and field_height > 0)
    assert(isinstance(name, str))
    assert(isinstance(x, int) and isinstance(y, int))
    assert(0 <= x < field_width and 0 <= y < field_height)
    assert(isinstance(color_idx, int))
    assert(0 <= color_idx < len(cfg.PLAYER_PALETTE))
    assert(isinstance(radius, int) and cfg.START_RADIUS <= radius <= cfg.MAX_RADIUS)
    decoded_player = Player(name, player_id, field_size, (x,y), radius)
    decoded_player.inputs = decode_inputs(inputs)
    decoded_player.color_idx = color_idx
    return decoded_player

def encode_orb(orb):
    return (orb.x, orb.y, orb.id)

def decode_orb(encoded_orb):
    x, y, orb_id = encoded_orb
    assert(isinstance(x, int) and isinstance(y, int) and isinstance(orb_id, int))
    assert(x >= 0 and y >= 0 and orb_id >= 0)
    return Orb((x,y), orb_id)