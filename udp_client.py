"""docstring"""
import socket
import pickle
from core_game import Network, UserInputs, Player, Orb
from config import *
import time
import threading
import bisect
import random
import collections
import sys


class Client(Network):
    """Class to connect, send, and recieve information from the server"""
    def __init__(self):
        self.server_address = ('0.0.0.0', NETWORK_PORT)
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        #self.client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.client_socket.settimeout(0)
        self.client_socket.bind(('0.0.0.0', 0))

        self._last_transmit_time = time.time()
        self.server_time = time.time()
        self.connected = False
        self.synced = False

        self.added_ping = 0
        self.packet_loss_rate = 0
        self.lag_spike_duration = 0
        self.data_load = 0
        self.connection_quality = (0,0,0,0)
        self.latency = 0
        self.last_probe_time = time.time()

        self.server_players_queue = collections.deque([], 256)
        self.server_orbs_queue = collections.deque([], 256)
        self.death_queue = collections.deque([], 256)
        self.past_players_queue = collections.deque([], 256)
        self.send_queue = collections.deque([], 256)
        self.packets_queue = collections.deque([], 1024)
        self.acked_packets = set()

        self.server_players = {}
        self.past_players = {}
        self.player = Player('')
        self.player_id = 0

    def connect(self, player_name, server_ip):
        """Connects to the server"""
        if not self.connected:
            self.player = Player(player_name)
            self.server_address = (server_ip, NETWORK_PORT)
            for _ in range(CONNECTION_ATTEMPTS):
                self._send_messages(CONNECT_CODE, self.encode_player(self.player))
                time.sleep(CONNECTION_INTERVAL)
                self._retrieve_messages()
                if self.connected: break

    def get_player_info(self):
        return self.player_id, self.player

    def disconnect(self):
        """Disconnects from the server"""
        self.connected = False
        self.synced = False
        self.added_ping = 0
        for _ in range(3): self._send_messages(DISCONNECT_CODE, self.player_id)

    def is_connected(self):
        return self.connected

    def is_synced(self):
        return self.synced

    def get_connection_quality(self):
        return self.connection_quality

    def _update_connection_qualty(self, curr_time):
        self.latency = min(self.latency, curr_time - self.server_time)
        if curr_time - self.last_probe_time > 10*CLIENT_TRANSMIT_INTERVAL:
            bandwidth = self.data_load/(curr_time - self.last_probe_time)
            self.connection_quality = (self.latency, bandwidth, \
                    self.packet_loss_rate, self.lag_spike_duration)
            self.data_load = 0
            self.latency = 1
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

    def needs_transmit(self):
        return time.time() - self._last_transmit_time > CLIENT_TRANSMIT_INTERVAL

    def sync_state(self, players, orbs, trackers):
        """Sends key presses to the server"""
        self._retrieve_messages()
        self._send_messages()
        curr_time, curr_players = time.time(), {}
        while self.server_players_queue:
            received_time = self.server_players_queue[0][0]
            if received_time >= curr_time: break
            _, rtt, server_pulse, self.server_players = self.server_players_queue.popleft()
            self.server_time = max(self.server_time, curr_time - rtt)
            self._send_messages(PING_CODE, server_pulse)

        effective_server_time = self.server_time - SERVER_TRANSMIT_INTERVAL/2
        while self.past_players_queue:
            past_time = self.past_players_queue[0][0]
            if past_time > effective_server_time: break
            self.past_players = self.past_players_queue.popleft()[1]

        for player_id, player in self.server_players.items():
            if player_id not in players: players[player_id] = player

        for player_id in list(players):
            if player_id not in self.server_players:
                del players[player_id]

        self._ack_updates(curr_time, orbs)
        self._verify_connection(curr_time, players)
        if self.synced:
            encoded_inputs = self.encode_inputs(players[self.player_id].inputs)
            self._send_messages(KEY_PRESSES_CODE, encoded_inputs)
            self._sync_player_positions(players)
            self._update_trackers(trackers)

        self._last_transmit_time = curr_time
        self._update_connection_qualty(curr_time)
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
            past_player = self.past_players[self.player_id]
            tracker.x, tracker.y = past_player[0], past_player[1]
            tracker.radius = past_player[2]
        elif 'past' in trackers:
            trackers['past'].radius = 0

    def _sync_player_positions(self, players):
        """Adjusts for discrepancies between local and server positions. Prevents butterfly effect."""
        for player_id, player in players.items():
            if player_id in self.past_players:
                player.x += 0.01*(self.server_players[player_id].x - self.past_players[player_id][0])
                player.y += 0.01*(self.server_players[player_id].y - self.past_players[player_id][1])

            player.radius = self.server_players[player_id].radius
            if player_id != self.player_id: 
                player.inputs = self.server_players[player_id].inputs

    def _ack_updates(self, curr_time, orbs):
        # Process orb updates from the server
        while self.packets_queue and self.packets_queue[0][0] <= curr_time - TIMEOUT_LIMIT:
            self.acked_packets.discard(self.packets_queue.popleft()[1])

        while self.death_queue:
            received_time = self.death_queue[0][0]
            if received_time >= curr_time: break
            _, packet_id, new_players = self.death_queue.popleft()
            self.server_players = new_players
            self.synced = False
            self._send_messages(ACK_CODE, packet_id)
            self.packets_queue.append((curr_time, packet_id))
            self.acked_packets.add(packet_id)

        received_orbs = []
        while self.server_orbs_queue and self.server_orbs_queue[0][0] <= curr_time:
            received_orbs.append(self.server_orbs_queue.popleft())
        received_orbs.sort(key=lambda x: x[1])

        for _, packet_id, updates in received_orbs:
            for add, orb in updates:
                if (add and orb in orbs) or (not add and orb not in orbs):
                    continue
            if packet_id in self.acked_packets: continue
            for add, orb in updates:
                if add: orbs[orb] = orb
                elif orb in orbs:
                    orbs[orb].erase()
                    del orbs[orb]
            self._send_messages(ACK_CODE, packet_id)
            self.packets_queue.append((curr_time, packet_id))
            self.acked_packets.add(packet_id)

    def _verify_connection(self, curr_time, players):
        # Determines if the connection with the server is alive
        if self.player_id not in self.server_players:
            self.connected = False
            return

        self.connected = curr_time - self.server_time < TIMEOUT_LIMIT
        synchronized = curr_time - self.server_time < PLAYER_INTERRUPT_LIMIT

        if not self.synced and synchronized:
            self.player.x = self.server_players[self.player_id].x
            self.player.y = self.server_players[self.player_id].y
            self.player.color_idx = self.server_players[self.player_id].color_idx
            self.past_players = {}
            self.past_players_queue.clear()
            self.server_time = curr_time
        self.synced = synchronized

    def _simulate_connection_instability(self):
        """Simulates packet loss and lag spikes"""
        if int(time.time())%LAG_SPIKE_INTERVAL < self.lag_spike_duration:
            raise Exception("Lag Spike.")
        if random.randrange(100) < self.packet_loss_rate:
            raise Exception("Packet Loss.")

    def _send_messages(self, code = -1, message = ''):
        """Sends messages to the server from the message queue"""
        curr_time = time.time()
        if code != -1: self.send_queue.append((curr_time, (code, message)))
        while self.send_queue and curr_time - self.send_queue[0][0] >= self.added_ping/2:
            try:
                input_time, data = self.send_queue.popleft()
                self._simulate_connection_instability()
                data = pickle.dumps(data)
                self.data_load += sys.getsizeof(data)+28
                self.client_socket.sendto(data, self.server_address)
            except Exception as exc:
                pass
                #print("[CLIENT] Outgoing data transmission failed for reasons:", exc)

    def _retrieve_messages(self):
        """Retrieves messages from the server and updates the server game state"""
        while True:
            try:
                data, addr = self.client_socket.recvfrom(4096)
                self._simulate_connection_instability()
                self.data_load += sys.getsizeof(data)+28
                code, data = pickle.loads(data)
                curr_time = time.time() + self.added_ping/2

                if code == CONNECT_CODE: self._accept_connection(data)
                elif code == UPDATE_PLAYERS_CODE: self._update_players(data, curr_time)
                elif code == UPDATE_ORBS_CODE: self._update_orbs(data, curr_time)
                elif code == PLAYER_DEATH_CODE: self._handle_death(data, curr_time)
                elif code == DISCONNECT_CODE: self._accept_disconnection(addr)

            except Exception as exc:
                if str(exc).startswith('[WinError 10035]'): break  # Buffer empty
                #print("[CLIENT] Incoming data reception failed for reasons:", exc)

    def _accept_connection(self, data):
        if not self.connected: 
            self.player_id = data
            self.connected = True

    def _update_players(self, data, curr_time):
        new_players, round_trip_time, server_pulse = data
        new_players = {player_id : self.decode_player(player) for player_id, player in new_players}
        self.server_players_queue.append((curr_time, round_trip_time, server_pulse, new_players))

    def _update_orbs(self, data, curr_time):
        packet_id, updates = data
        orb_updates = [(add, (self.decode_orb(orb))) for add, orb in updates]
        self.server_orbs_queue.append((curr_time, packet_id, orb_updates))

    def _handle_death(self, data, curr_time):
        packet_id, new_players = data
        new_players = {player_id : self.decode_player(player) for player_id, player in new_players}
        self.death_queue.append((curr_time, packet_id, new_players))

    def _accept_disconnection(self, address):
        if address == self.server_address:
            self.connected = False