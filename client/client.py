"""docstring"""
import socket
import pickle
import time
import random
import math
import collections
import sys
import pygame as pg
import source.config as cfg
import source.network


class Client:
    """Class to connect, send, and recieve information from the server"""
    def __init__(self):
        self.server_address = ("0.0.0.0", cfg.NETWORK_PORT)
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.client_socket.bind(('0.0.0.0', 0))
        self.client_socket.settimeout(0)

        self.connected = False
        self.synced = False
        self.server_players_queue = collections.deque([], 256)
        self.server_orbs_queue = collections.deque([], 256)
        self.death_queue = collections.deque([], 256)
        self.send_queue = collections.deque([], 256)
        self.past_player_queue = collections.deque([], 1024)
        self.packets_queue = collections.deque([], 1024)
        self.acked_packets = set()

        self.data_load = 0
        self.added_ping = 0
        self.packet_loss_rate = 0
        self.lag_spike_duration = 0
        self.latency = 0
        self.connection_quality = (0,0,0,0)  # Compiles data_load, added_ping, packet_loss_rate, and lag_spike_duration into a tuple
        self.last_probe_time = time.time()
        self.last_sync_time = time.time()
        self.server_time = time.time()
        self.heartbeat = 0

        self.map_size = (0,0)
        self.leaders = []
        self.server_players = {}
        self.past_player = None
        self.player_id = 0
        self.end_game_state = ''


    def connect(self, player_name, server_ip):
        """Connects to the server"""
        if not self.connected:
            self.server_address = (server_ip, cfg.NETWORK_PORT)
            for _ in range(cfg.CONNECTION_ATTEMPTS):
                self._add_message(cfg.CONNECT_CODE, player_name)
                self._send_messages()
                time.sleep(cfg.CONNECTION_ATTEMPT_INTERVAL)
                self._retrieve_messages()
                if self.connected: break

    def disconnect(self):
        """Disconnects from the server"""
        self.connected = False
        self.synced = False
        self.added_ping = 0
        for _ in range(3):
            self._add_message(cfg.DISCONNECT_CODE, self.player_id)
        self._send_messages()
        self.client_socket.close()

    def is_connected(self):
        return self.connected

    def is_synced(self):
        return self.synced

    def get_players(self):
        return self.server_players, self.server_players[self.player_id]

    def get_end_state(self):
        return self.end_game_state

    def get_connection_statistics(self):
        return self.connection_quality

    def _update_connection_statistics(self, curr_time):
        time_elapsed = curr_time - self.last_probe_time
        if time_elapsed > cfg.STATS_PROBE_INTERVAL:
            # cfg.STATS_PROBE_INTERVAL must be > 0 to ensure time_elapsed > 0
            bandwidth = self.data_load/time_elapsed
            self.connection_quality = (self.latency, bandwidth,
                    self.packet_loss_rate, self.lag_spike_duration)
            self.data_load = 0
            self.last_probe_time = curr_time

    def increase_ping(self, time_delta):
        self.added_ping = min(0.7, self.added_ping + time_delta/8)

    def decrease_ping(self, time_delta):
        self.added_ping = max(0, self.added_ping - time_delta/8)

    def increase_packet_loss(self, time_delta):
        self.packet_loss_rate = min(100, self.packet_loss_rate + 8*time_delta)

    def decrease_packet_loss(self, time_delta):
        self.packet_loss_rate = max(0, self.packet_loss_rate - 8*time_delta)

    def increase_lag_spike(self, time_delta):
        self.lag_spike_duration = min(5, self.lag_spike_duration + time_delta)

    def decrease_lag_spike(self, time_delta):
        self.lag_spike_duration = max(0, self.lag_spike_duration - time_delta)

    def needs_sync(self):
        time_passed = time.time() - self.last_sync_time
        return time_passed > cfg.CLIENT_SYNC_INTERVAL

    def sync_state(self, time_delta, players, orbs, trackers):
        """Sends key presses to the server"""
        self._retrieve_messages()
        self.last_sync_time = curr_time = time.time()
        while self.server_players_queue:
            received_time = self.server_players_queue[0][0]
            if received_time > curr_time: break
            update = self.server_players_queue.popleft()
            _, round_trip_time, server_pulse, player_update = update
            if server_pulse <= self.heartbeat: continue
            self.heartbeat = server_pulse
            self.leaders, new_players = player_update
            self._apply_player_update(players, new_players)
            new_server_time = curr_time - round_trip_time
            self.server_time = max(self.server_time, new_server_time)
            self.latency = curr_time - self.server_time
            self._add_message(cfg.PING_CODE, server_pulse)

        effective_server_time = self.server_time - cfg.SERVER_SYNC_INTERVAL/2
        while self.past_player_queue:
            past_time = self.past_player_queue[0][0]
            if past_time > effective_server_time: break
            _, self.past_player = self.past_player_queue.popleft()

        self._acknowledge_updates(curr_time, players, orbs)
        self._verify_connection(curr_time, players)
        if self.synced:
            player = players[self.player_id]
            curr_player_info = (player.x, player.y, player.radius)
            self.past_player_queue.append((curr_time, curr_player_info))
            message = source.network.encode_inputs(player.inputs)
            self._add_message(cfg.INPUTS_CODE, message)
            self._sync_player_positions(time_delta, players)
            self._update_trackers(trackers)

        self._send_messages()
        self._update_connection_statistics(curr_time)

    def _update_trackers(self, trackers):
        """dd"""
        if self.player_id in self.server_players and 'server' in trackers:
            tracker = trackers['server']
            server_player = self.server_players[self.player_id]
            tracker.x, tracker.y = server_player.x, server_player.y
            tracker.radius = server_player.radius

        if self.past_player and 'past' in trackers:
            tracker = trackers['past']
            past_x, past_y, past_radius = self.past_player
            tracker.x, tracker.y = past_x, past_y
            tracker.radius = past_radius
        elif 'past' in trackers:
            trackers['past'].radius = 0

    def _sync_player_positions(self, time_delta, players):
        """Adjusts for discrepancies between local and server positions.

        Prevents butterfly effect.
        params: 
        """
        # Adjust gravity to control how quickly to correct for errors
        gravity = cfg.GRAVITY_FACTOR*time_delta
        for player_id, player in players.items():
            if player_id not in self.server_players: continue
            if player_id != self.player_id:
                player.inputs = self.server_players[player_id].inputs
            if player.radius != self.server_players[player_id].radius:
                player.radius = self.server_players[player_id].radius
                player.scale = math.pow(player.radius/cfg.START_RADIUS, cfg.VIEW_GROWTH_RATE)

            if player_id == self.player_id and self.past_player:
                past_x, past_y, _ = self.past_player
                player.x += gravity*(self.server_players[player_id].x - past_x)
                player.y += gravity*(self.server_players[player_id].y - past_y)
            else:
                player.x += gravity*(self.server_players[player_id].x - player.x)
                player.y += gravity*(self.server_players[player_id].y - player.y)

    def _acknowledge_updates(self, curr_time, players, orbs):
        """"""
        while self.packets_queue:
            past_time = self.packets_queue[0][0]
            if curr_time - past_time < cfg.TIMEOUT_LIMIT: break
            _, packet_id = self.packets_queue.popleft()
            self.acked_packets.discard(packet_id)

        while self.death_queue:
            received_time = self.death_queue[0][0]
            if received_time > curr_time: break
            _, packet_id, player_update = self.death_queue.popleft()
            self._add_message(cfg.ACK_CODE, packet_id)
            if packet_id in self.acked_packets: continue
            self.player_id = player_update
            self.synced = False
            self._ack_update(curr_time, packet_id)

        received_orb_updates = []
        while self.server_orbs_queue:
            received_time = self.server_orbs_queue[0][0]
            if received_time > curr_time: break
            _, packet_id, updates = self.server_orbs_queue.popleft()
            received_orb_updates.append((packet_id, updates))
        received_orb_updates.sort(key=lambda x: x[0])

        for packet_id, (additions, removals) in received_orb_updates:
            if packet_id in self.acked_packets:
                self._add_message(cfg.ACK_CODE, packet_id)
                continue
            if all(orb.id in orbs for orb in removals):
                if all(orb.id not in orbs for orb in additions):
                    for orb in additions:
                        orbs[orb.id] = orb
                    for orb in removals:
                        orbs.pop(orb.id)
                    self._add_message(cfg.ACK_CODE, packet_id)
                    self._ack_update(curr_time, packet_id)

    def _ack_update(self, curr_time, packet_id):
        self.packets_queue.append((curr_time, packet_id))
        self.acked_packets.add(packet_id)

    def _verify_connection(self, curr_time, players):
        """Determines if the connection with the server is alive"""
        if curr_time - self.server_time > cfg.TIMEOUT_LIMIT:
            self.connected = False
            self.end_game_state = "Error: Server Connection Interrupted"
            return
        server_delay = curr_time - self.server_time
        synchronized = True
        if (server_delay > cfg.PLAYER_INTERRUPT_LIMIT
            or self.player_id not in self.server_players):
            synchronized = False
        if not self.synced and synchronized:
            self._reset_players(players)
        self.synced = synchronized

    def _apply_player_update(self, players, new_players):
        self.server_players = {p.id : p for p in new_players}
        for player_id, player in self.server_players.items():
            if player_id not in players:
                players[player_id] = player
        for player_id in list(players):
            if player_id == self.player_id: continue
            if player_id not in self.server_players:
                players.pop(player_id)

    def _reset_players(self, players):
        for player_id, player in players.items():
            if player_id not in self.server_players: continue
            player.x = self.server_players[player_id].x
            player.y = self.server_players[player_id].y
            player.color_idx = self.server_players[player_id].color_idx
        self.past_player = None
        self.past_player_queue.clear()

    def _simulate_connection_instability(self):
        """Simulates packet loss and lag spikes"""
        if int(time.time())%cfg.LAG_SPIKE_INTERVAL < self.lag_spike_duration:
            raise Exception("Lag Spike.")
        if random.randrange(100) < self.packet_loss_rate:
            raise Exception("Packet Loss.")

    def _add_message(self, code, message):
        self.send_queue.append((time.time(), (code, message)))

    def _send_messages(self):
        """Sends messages to the server from the message queue"""
        curr_time = time.time()
        while self.send_queue:
            send_time = self.send_queue[0][0]
            if curr_time - send_time < self.added_ping/2: break
            try:
                _, data = self.send_queue.popleft()
                self._simulate_connection_instability()
                data = pickle.dumps(data)
                self.data_load += sys.getsizeof(data)+28
                self.client_socket.sendto(data, self.server_address)
            except Exception as exc:
                print("[CLIENT] Data transmission failed for reasons:", exc)

    def _retrieve_messages(self):
        """Retrieves and processes messages from the server"""
        while True:
            try:
                data, addr = self.client_socket.recvfrom(16384)
                self._simulate_connection_instability()
                self.data_load += sys.getsizeof(data)+28
                code, data = pickle.loads(data)
                reception_time = time.time() + self.added_ping/2

                if code == cfg.CONNECT_CODE:
                    self._accept_connection(data)
                elif code == cfg.UPD_PLAYERS_CODE:
                    self._update_players(data, reception_time)
                elif code == cfg.UPD_ORBS_CODE:
                    self._update_orbs(data, reception_time)
                elif code == cfg.DEATH_CODE:
                    self._handle_death(data, reception_time)
                elif code == cfg.DISCONNECT_CODE:
                    self._accept_disconnection(addr)

            except socket.error:
                break
            except Exception as exc:
                print("[CLIENT] Data reception failed for reasons:", exc)

    def _accept_connection(self, data):
        if not self.connected:
            self.player_id, player, self.map_size = data
            player = source.network.decode_player(player)
            self.server_players[self.player_id] = player
            self.connected = True

    def _update_players(self, data, curr_time):
        (leaders, received_players, server_pulse), round_trip_time = data
        new_players, new_leaders = [], []
        for player in received_players:
            new_players.append(source.network.decode_player(player))
        for player in leaders:
            new_leaders.append(source.network.decode_name(player))
        player_update = (new_leaders, new_players)
        update = (curr_time, round_trip_time, server_pulse, player_update)
        self.server_players_queue.append(update)

    def _update_orbs(self, data, curr_time):
        packet_id, updates = data
        orb_additions = [source.network.decode_orb(orb) for orb in updates[0]]
        orb_removals = [source.network.decode_orb(orb) for orb in updates[1]]
        orb_updates = (orb_additions, orb_removals)
        update = (curr_time, packet_id, orb_updates)
        self.server_orbs_queue.append(update)

    def _handle_death(self, data, curr_time):
        packet_id, player_update = data
        update = (curr_time, packet_id, player_update)
        self.death_queue.append(update)

    def _accept_disconnection(self, end_game_state):
        self.end_game_state = end_game_state
        self.connected = False