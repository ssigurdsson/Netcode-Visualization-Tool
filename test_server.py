"""Provides some rudementary testing functions for the server game logic.

Additionally, allows for execution time profiling and exploration of server
game logic scaling with respect to orb density, player count, and map size.
"""

import random
import time
import math
import matplotlib.pyplot as pyplot
import multiprocessing as mp
import pickle
import socket
import sys
import pygame as pg
import source.config as cfg
import source.entities
import source.network
import source.animation
import client.client_game
import server.server_game


def simulate_game(game, cycle_count, player_count):
    """Simulates an instance of the server game for cycle_count cycles.

    The number of simulated players is defined by player_count.

    Args:
        cycle_count: An integer representing the nr of cycles to run.
        player_count: An integer representing the nr of players to simulate.

    Returns:
        A float value representing the execution time of the function.
    """
    timers = [0]*5
    new_players = []
    for i in range(player_count):
        new_player = source.entities.Player(str(i), i)
        new_player.inputs.x = random.randrange(-cfg.MAX_RADIUS,cfg.MAX_RADIUS)
        new_player.inputs.y = random.randrange(-cfg.MAX_RADIUS,cfg.MAX_RADIUS)
        new_players.append(new_player)
    add_players(game, new_players)
    game._replenish_orbs()
    game._sync_server_players()
    for player in game.id_to_player.values():
        player.radius = random.randrange(cfg.START_RADIUS, 800)
    game._sync_server_players()

    count = 0
    start_time = time.time()
    clock = pg.time.Clock()
    for _ in range(cycle_count):
        time_delta = clock.tick()/1000
        for player in game.id_to_player.values():
            game.players.remove(player)
            player.move(game.map_size, time_delta)
            game.players.add(player)

        game._handle_player_collisions()
        game._handle_orb_collisions()

        #if game.server.needs_sync():
        game._sync_server_players()

        # Remove this line to simulated performance w/o displaying the game.
        game._update_display(time_delta, game.id_to_player.values(), game.orbs)

        count += 1
        if count == 300:
            for player in game.id_to_player.values():
                player.inputs.x = random.randrange(-cfg.MAX_RADIUS,cfg.MAX_RADIUS)
                player.inputs.y = random.randrange(-cfg.MAX_RADIUS,cfg.MAX_RADIUS)

        # In order to detect faulty collisions, player growth must be disabled
        #verify_player_collisions(game)
        #verify_orb_collisions(game)

        for event in pg.event.get():
            game._handle_event(event)
        if not game.is_running(): break

    game.stop()
    #print(timers)
    return time.time() - start_time

def verify_player_collisions(game):
    if game.players.item_count != len(game.id_to_player):
        print('too few players')
    for player in game.players:
        for other_player in game.players:
            if other_player == player: continue
            if player.radius >= other_player.radius: continue
            dist = player.find_distance(other_player)
            margin = player.radius*cfg.COLLISION_MARGIN
            if dist < other_player.radius - margin:
                print('player collision fault')

def verify_orb_collisions(game):
    if game.orbs.item_count != game.target_orb_count:
        print('too few orbs')
    for player in game.players:
        for orb in game.orbs:
            dist = player.find_distance(orb)
            margin = orb.radius*cfg.COLLISION_MARGIN
            if dist < player.radius - margin:
                print('orb collision fault')

def add_players(game, players):
    """Connects every simulated player to the server under the same address."""
    local_address = (socket.gethostbyname(socket.gethostname()), 11332)
    game.server.addr_to_id[local_address] = game.server.player_id
    game.server.connected_addresses.add(local_address)
    for player in players:
        game.server.player_id += 1
        player_info = [local_address, set(), float('Inf'), 0]
        game.server.id_map[game.server.player_id] = player_info
        player_update = (game.server.player_id, player.name)
        game.server.player_add_queue.append(player_update)
        input_update = (game.server.player_id, player.inputs)
        game.server.player_input_queue.append(input_update)

def dummy_client():
    """Creates a dummy client for basic input/output.

    All messages from the server sent to the simulated players are
    routed to this client. Any and all updates received are acknowledged.
    This allows the simulated players to stay connected to the server, and
    approximates the load of handling acknowledgements server side.
    """
    local_address = (socket.gethostbyname(socket.gethostname()), 11332)
    dummy_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    dummy_socket.bind(local_address)
    local_ip = socket.gethostbyname(socket.gethostname())
    server_address = (local_ip, cfg.NETWORK_PORT)
    while True:
        try:
            data, addr = dummy_socket.recvfrom(12096)
            code, data = pickle.loads(data)
            if code in (cfg.UPD_ORBS_CODE, cfg.DEATH_CODE):
                packet_id, update = data
                message = pickle.dumps((cfg.ACK_CODE, packet_id))
                dummy_socket.sendto(message, server_address)
        except: pass

def main():
    """Initializes a server game instance for simulation purposes."""
    mp.set_start_method("spawn")
    process = mp.Process(target=dummy_client).start()
    time.sleep(0.5)

    run_times = []
    averaging_cycle_count = 1000
    orb_density = 50
    factors = [1,40,80,120]#,160,200,240,280,320,360,400]
    factors = [int(math.sqrt(f)) for f in factors]
    for factor in factors:
        field_size = (factor*cfg.BASE_WIDTH, factor*cfg.BASE_HEIGHT)
        orb_count = orb_density*factor*factor
        game = server.server_game.ServerGame(400, 0, orb_count, field_size)
        game.start()
        run_time = simulate_game(game, averaging_cycle_count, factor*factor)
        run_times.append(run_time)
    pyplot.scatter([f*f for f in factors], [r for r in run_times])
    #print([f*f for f in factors], [r for r in run_times])
    pyplot.title("Simulation of 1000 server loops")
    pyplot.xlabel("#Units")
    pyplot.ylabel("Run Time (seconds)")
    pyplot.show()


if __name__ == '__main__':
    main()
    pg.quit()
    sys.exit()
