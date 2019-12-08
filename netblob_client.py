"""docstring"""
import sys
import socket
import pickle
from netblob_entities import Player
import netblob_network
from netblob_config import *
import time
import bisect
import random
import collections


class Client:
    """Class to connect, send, and recieve information from the server"""
    def __init__(self):
        self.server_address = ('0.0.0.0', NETWORK_PORT)
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.client_socket.bind(('0.0.0.0', 0))
        self.client_socket.settimeout(0)

        self.connected = False
        self.synced = False
        self.server_players_queue = collections.deque([], 256)
        self.server_orbs_queue = collections.deque([], 256)
        self.death_queue = collections.deque([], 256)
        self.send_queue = collections.deque([], 256)
        self.past_players_queue = collections.deque([], 1024)
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
        self.heartbeat = float('-Inf')

        self.server_players = {}
        self.past_players = {}
        self.player = Player('')
        self.player_id = 0
        self.end_game_state = ''

    def connect(self, player_name, server_ip):
        """Connects to the server"""
        if not self.connected:
            self.player = Player(player_name)
            self.server_address = (server_ip, NETWORK_PORT)
            for _ in range(CONNECTION_ATTEMPTS):  # Ætti ég bara að hard-kóða tölur sem eru bara notaðar á einum stað?
                self._add_message(CONNECT_CODE, \
                        netblob_network.encode_player(self.player))
                self._send_messages()
                time.sleep(CONNECTION_INTERVAL)
                self._retrieve_messages()
                if self.connected: break

    def disconnect(self):
        """Disconnects from the server"""
        self.connected = False
        self.synced = False
        self.added_ping = 0
        for _ in range(3):
            self._add_message(DISCONNECT_CODE, self.player_id)
            self._send_messages()
        self.client_socket.close()

    def get_player_info(self):
        return self.player_id, self.player

    def is_connected(self):
        return self.connected

    def is_synced(self):
        return self.synced

    def get_end_state(self):
        return self.end_game_state

    def get_connection_statistics(self):
        return self.connection_statistics

    def _update_connection_statistics(self, curr_time):
        if curr_time - self.last_probe_time > STATS_PROBE_INTERVAL:
            bandwidth = self.data_load/(curr_time - self.last_probe_time)
            self.connection_statistics = (self.latency, bandwidth, \
                    self.packet_loss_rate, self.lag_spike_duration)
            self.data_load = 0
            self.last_probe_time = curr_time

    def increase_ping(self):
        self.added_ping = min(0.7, self.added_ping + 0.0003)

    def decrease_ping(self):
        self.added_ping = max(0, self.added_ping - 0.0003)

    def increase_packet_loss(self):
        self.packet_loss_rate = min(100, self.packet_loss_rate + 0.03)

    def decrease_packet_loss(self):
        self.packet_loss_rate = max(0, self.packet_loss_rate - 0.03)

    def increase_lag_spike(self):
        self.lag_spike_duration = min(5, self.lag_spike_duration + 0.002)

    def decrease_lag_spike(self):
        self.lag_spike_duration = max(0, self.lag_spike_duration - 0.002)

    def needs_sync(self):
        time_passed = time.time() - self.last_sync_time
        return time_passed > CLIENT_SYNC_INTERVAL

    def sync_state(self, time_delta, players, orbs, trackers):
        """Sends key presses to the server"""
        self._retrieve_messages()
        curr_time = time.time()
        while self.server_players_queue:
            received_time = self.server_players_queue[0][0]
            if received_time > curr_time: break
            _, round_trip_time, server_pulse, new_players = \
                    self.server_players_queue.popleft()
            self._apply_players_update(server_pulse, new_players)
            new_server_time = curr_time - round_trip_time
            self.server_time = max(self.server_time, new_server_time)
            self.latency = curr_time - self.server_time
            self._add_message(PING_CODE, server_pulse)

        effective_server_time = self.server_time - SERVER_SYNC_INTERVAL/2
        while self.past_players_queue:
            past_time = self.past_players_queue[0][0]
            if past_time > effective_server_time: break
            _, self.past_players = self.past_players_queue.popleft()

        for player_id, player in self.server_players.items():
            if player_id not in players:
                players[player_id] = player
        for player_id in list(players):
            if player_id not in self.server_players:
                del players[player_id]

        self._acknowledge_updates(curr_time, orbs)
        self._verify_connection(curr_time, players)
        if self.synced:
            message = netblob_network.encode_inputs(self.player.inputs)
            self._add_message(INPUTS_CODE, message)
            self._sync_player_positions(time_delta, players)
            self._update_trackers(trackers)

        self._send_messages()
        self.last_sync_time = curr_time
        self._update_connection_statistics(curr_time)

        curr_players = {}
        for player_id, player in players.items():
            curr_players[player_id] = (player.x, player.y, player.radius)
        self.past_players_queue.append((curr_time, curr_players))

    def _update_trackers(self, trackers):
        """dd"""
        if self.player_id in self.server_players and 'server' in trackers:
            tracker = trackers['server']
            server_player = self.server_players[self.player_id]
            tracker.x, tracker.y = server_player.x, server_player.y
            tracker.radius = server_player.radius

        if self.player_id in self.past_players and 'past' in trackers:
            tracker = trackers['past']
            past_x, past_y, past_radius = self.past_players[self.player_id]
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
        gravity = 4*time_delta
        for player_id, player in players.items():
            player.radius = self.server_players[player_id].radius
            if player_id != self.player_id: 
                player.inputs = self.server_players[player_id].inputs

            if player_id not in self.past_players: continue
            past_x, past_y, _ = self.past_players[player_id]
            player.x += gravity*(self.server_players[player_id].x - past_x)
            player.y += gravity*(self.server_players[player_id].y - past_y)

    def _acknowledge_updates(self, curr_time, orbs):
        """"""
        while self.packets_queue:
            past_time = self.packets_queue[0][0]
            if curr_time - past_time < TIMEOUT_LIMIT: break
            _, packet_id = self.packets_queue.popleft()
            self.acked_packets.discard(packet_id)

        while self.death_queue:
            received_time = self.death_queue[0][0]
            if received_time > curr_time: break
            _, packet_id, server_pulse, new_players = \
                    self.death_queue.popleft()
            self._apply_players_update(server_pulse, new_players)
            print('did')
            self._reset_player()
            self._ack_update(curr_time, packet_id)

        received_orb_updates = []
        while self.server_orbs_queue:
            received_time = self.server_orbs_queue[0][0]
            if received_time > curr_time: break
            _, packet_id, updates = self.server_orbs_queue.popleft()
            received_orb_updates.append((packet_id, updates))
        received_orb_updates.sort()

        for packet_id, (additions, removals) in received_orb_updates:
            if packet_id in self.acked_packets:
                self._add_message(ACK_CODE, packet_id)
                continue
            if all(orb in orbs for orb in removals) \
                    and all(orb not in orbs for orb in additions):
                for orb in additions:
                    orbs[orb] = orb
                for orb in removals:
                    orbs[orb].erase()
                    del orbs[orb]
                self._ack_update(curr_time, packet_id)

    def _apply_players_update(self, server_pulse, new_players):
        if server_pulse > self.heartbeat:
            self.heartbeat = server_pulse
            self.server_players = new_players

    def _ack_update(self, curr_time, packet_id):
        self._add_message(ACK_CODE, packet_id)
        self.packets_queue.append((curr_time, packet_id))
        self.acked_packets.add(packet_id)

    def _verify_connection(self, curr_time, players):
        """Determines if the connection with the server is alive"""
        if self.player_id not in self.server_players:
            self.connected = False
        elif curr_time - self.server_time > TIMEOUT_LIMIT:
            self.connected = False
        if not self.connected:
            self.end_game_state = "Error: Server Connection Interrupted"
            return

        synchronized = curr_time - self.server_time < PLAYER_INTERRUPT_LIMIT
        if not self.synced and synchronized:
            self._reset_player()
        self.synced = synchronized

    def _reset_player(self):
        self.player.x = self.server_players[self.player_id].x
        self.player.y = self.server_players[self.player_id].y
        self.player.color_idx = self.server_players[self.player_id].color_idx
        self.past_players = {}
        self.past_players_queue.clear()

    def _simulate_connection_instability(self):
        """Simulates packet loss and lag spikes"""
        if int(time.time())%LAG_SPIKE_INTERVAL < self.lag_spike_duration:
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
                data, addr = self.client_socket.recvfrom(4096)
                self._simulate_connection_instability()
                self.data_load += sys.getsizeof(data)+28
                code, data = pickle.loads(data)
                reception_time = time.time() + self.added_ping/2

                if code == CONNECT_CODE:
                    self._accept_connection(data)
                elif code == UPD_PLAYERS_CODE:
                    self._update_players(data, reception_time)
                elif code == UPD_ORBS_CODE:
                    self._update_orbs(data, reception_time)
                elif code == DEATH_CODE:
                    self._handle_death(data, reception_time)
                elif code == DISCONNECT_CODE:
                    self._accept_disconnection(addr)

            except Exception as exc:
                if str(exc).startswith('[WinError 10035]'): break  #Timed out
                print("[CLIENT] Data reception failed for reasons:", exc)

    def _accept_connection(self, data):
        if not self.connected:
            self.player_id = data
            self.connected = True

    def _update_players(self, data, curr_time):
        (received_players, server_pulse), round_trip_time = data
        new_players = {}
        for player_id, player in received_players:
            new_players[player_id] = netblob_network.decode_player(player)
        update = (curr_time, round_trip_time, server_pulse, new_players)
        self.server_players_queue.append(update)

    def _update_orbs(self, data, curr_time):
        packet_id, updates = data
        if packet_id in self.acked_packets:
            self._add_message(ACK_CODE, packet_id)
            return
        orb_additions = [netblob_network.decode_orb(orb) for orb in updates[0]]
        orb_removals = [netblob_network.decode_orb(orb) for orb in updates[1]]
        orb_updates = (orb_additions, orb_removals)
        self.server_orbs_queue.append((curr_time, packet_id, orb_updates))

    def _handle_death(self, data, curr_time):
        packet_id, (received_players, server_pulse) = data
        new_players = {}
        for player_id, player in received_players:
            new_players[player_id] = netblob_network.decode_player(player)
        update = (curr_time, packet_id, server_pulse, new_players)
        self.death_queue.append(update)

    def _accept_disconnection(self, end_game_state):
        self.end_game_state = end_game_state
        self.connected = False