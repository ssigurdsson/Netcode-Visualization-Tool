"""Provides a Server interface for communication with clients."""

import collections
import pickle
import time
import socket
import sys
import threading
import pygame as pg
import source.config as cfg
from source.entities import UserInputs
import source.network


class Server:
    """Handles communication with an arbitrary number of Netblob clients.
    
    Communication takes place over UDP socket. Incoming messages are decoded
    and relayed to the ServerGame instance to which the server belongs.
    Outgoing messages are received from the same ServerGame instance which
    calls function sync_state whenever updates are to be transmitted to
    clients.
    """
    def __init__(self, map_size):
        """Initializes the server with a map size defined by map_size"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_socket.bind(("", cfg.NETWORK_PORT))
        self.server_socket.settimeout(5)

        self.run = False
        self.map_size = map_size
        self.threads = []
        self.server_time = time.time()
        self.packet_id, self.player_id = 0, 0
        self.player_input_queue = collections.deque([], 4096)
        self.player_add_queue = collections.deque([], 4096)
        self.player_remove_queue = collections.deque([], 4096)
        self.ack_transmission_queue = collections.deque([], 4096)
        self.ack_reception_queue = collections.deque([], 4096)

        self.id_map = {}
        self.addr_to_id = {}
        self.connected_addresses = set()
        self.last_sync_time = self.server_time

        self.data_load = 0
        self.connection_statistics = [0]
        self.last_probe_time = self.server_time

    def start(self):
        if not self.run:
            self.run = True
            thread_1 = threading.Thread(target=self._handle_acknowledgements)
            thread_2 = threading.Thread(target=self._retrieve_messages)
            self.threads.extend([thread_1, thread_2])
            for thread in self.threads:
                thread.start()
            local_addr = socket.gethostbyname(socket.gethostname())
            print("[SERVER] Server Started with local address:", local_addr)
            print("[SERVER] For players to connect by public IP, port",
                "forwarding may be necessary on port:", str(cfg.NETWORK_PORT))

    def stop(self):
        self.run = False
        for t in self.threads: t.join()
        self.server_socket.close()

    def get_player_additions(self):
        return self.player_add_queue

    def get_player_removals(self):
        return self.player_remove_queue

    def get_player_inputs(self):
        return self.player_input_queue

    def approve_player_connection(self, player_id, player):
        if player_id not in self.id_map: return
        player_addr = self.id_map[player_id][0]
        encoded_player = source.network.encode_player(player)
        message = (player_id, encoded_player, self.map_size)
        self._connect_player(message, player_addr)

    def drop_player_connection(self, player_id, message):
        if player_id not in self.id_map: return
        player_addr = self.id_map[player_id][0]
        if player_addr in self.addr_to_id:
            del self.addr_to_id[player_addr]
        self.connected_addresses.discard(player_addr)
        del self.id_map[player_id]
        self._disconnect_player(message, player_addr)

    def needs_sync(self):
        self.server_time = time.time()
        time_passed = self.server_time - self.last_sync_time
        return time_passed > cfg.SERVER_SYNC_INTERVAL

    def sync_state(
        self, leaders, player_views, orb_views):
        """Transmit data, then add or removes players"""
        self.last_sync_time = self.server_time = time.time()
        self._transmit_orbs(orb_views)
        self._transmit_players(leaders, player_views)
        self._update_connection_statistics()

    def sync_player_death(self, player):
        player_info = self.id_map[player.id]
        player_addr, _, player_time, player_ping = player_info
        self.id_map.pop(player.id)
        self.player_id += 1
        player.id = self.player_id
        self.addr_to_id[player_addr] = player.id
        self.id_map[player.id] = player_info
        self.packet_id += 1
        update = (player.id, player_addr, self.packet_id,
                self.server_time, cfg.DEATH_CODE, player.id)
        self.ack_transmission_queue.append(update)
        message = (self.packet_id, player.id)
        self._send_message(cfg.DEATH_CODE, message, player_addr)

    def get_connection_statistics(self):
        return self.connection_statistics

    def _update_connection_statistics(self):
        if self.server_time - self.last_probe_time > cfg.STATS_PROBE_INTERVAL:
            bw = self.data_load/(self.server_time - self.last_probe_time)
            self.data_load = 0
            self.connection_statistics[0] = bw
            self.last_probe_time = self.server_time

    def _transmit_players(self, leaders, player_views):
        for player_id, player_view in player_views:
            player_list, leader_list = [], []
            for player in player_view:
                player_list.append(source.network.encode_player(player))
            for player in leaders:
                leader_list.append(player.name)
            transmit = (leader_list, player_list, self.server_time)

            player_addr, _, player_time, player_ping = self.id_map[player_id]
            if self.server_time - player_time >= cfg.TIMEOUT_LIMIT:
                self._remove_player(player_id)
            else:
                if self.server_time - player_time >= cfg.PLAYER_INTERRUPT_LIMIT:
                    default_inputs = source.network.encode_inputs(UserInputs())
                    self._update_commands(default_inputs, player_addr)
            message = (transmit, player_ping)
            self._send_message(cfg.UPD_PLAYERS_CODE, message, player_addr)

    def _transmit_orbs(self, orb_views):
        for player_id, new_orb_view in orb_views:
            player_addr, curr_orb_view, _, _ = self.id_map[player_id]
            orb_additions, orb_removals = [], []
            for orb in new_orb_view ^ curr_orb_view:
                if orb in new_orb_view:
                    orb_additions.append(source.network.encode_orb(orb))
                else:
                    orb_removals.append(source.network.encode_orb(orb))
            self.id_map[player_id][1] = new_orb_view
            if orb_additions or orb_removals:
                orb_updates = (orb_additions, orb_removals)
                self.packet_id += 1
                update = (player_id, player_addr, self.packet_id,
                    self.server_time, cfg.UPD_ORBS_CODE, orb_updates)
                self.ack_transmission_queue.append(update)
                message = (self.packet_id, orb_updates)
                self._send_message(cfg.UPD_ORBS_CODE, message, player_addr)

    def _send_message(self, code, message, addr):
        data = pickle.dumps((code, message))
        self.data_load += sys.getsizeof(data)+28
        self.server_socket.sendto(data, addr)

    def _handle_acknowledgements(self):
        """d"""
        unacked_packets = {}
        while self.run:
            while self.ack_reception_queue:
                packet_id, player_addr = self.ack_reception_queue.popleft()
                if packet_id in unacked_packets:
                    if unacked_packets[packet_id][1] == player_addr:
                        del unacked_packets[packet_id]

            for packet_id, packet_info in list(unacked_packets.items()):
                player_id, player_addr, code, updates, \
                        past_server_time = packet_info
                if self.server_time - past_server_time > cfg.TIMEOUT_LIMIT or \
                        player_addr not in self.connected_addresses:
                    self._remove_player(player_id)
                    del unacked_packets[packet_id]
                else:
                    message = (packet_id, updates)
                    self._send_message(code, message, player_addr)

            while self.ack_transmission_queue:
                player_id, player_addr, packet_id, server_time, \
                    code, updates = self.ack_transmission_queue.popleft()
                unacked_packets[packet_id] = \
                        (player_id, player_addr, code, updates, server_time)

            time.sleep(cfg.ACK_INTERVAL)


    def _retrieve_messages(self):
        while self.run:
            try:
                data, addr = self.server_socket.recvfrom(2048)
                self.data_load += sys.getsizeof(data)+28
                code, data = pickle.loads(data)

                if code == cfg.CONNECT_CODE:
                    self._add_new_player(data, addr)
                elif code == cfg.INPUTS_CODE:
                    self._update_commands(data, addr)
                elif code == cfg.ACK_CODE:
                    self._update_acks(data, addr)
                elif code == cfg.PING_CODE:
                    self._update_ping(data, addr)
                elif code == cfg.DISCONNECT_CODE:
                    self._remove_player(data)

            except Exception:
                pass

    def _add_new_player(self, player_name, player_addr):
        player_name = source.network.decode_name(player_name)
        if player_addr not in self.connected_addresses:
            self.connected_addresses.add(player_addr)
            self.player_id += 1
            self.addr_to_id[player_addr] = self.player_id
            # Player info includes Ip address, orb_view, heartbeat, ping
            player_info = [player_addr, set(), self.server_time, 0]
            self.id_map[self.player_id] = player_info
            update = (self.player_id, player_name)
        else:
            update = (self.addr_to_id[player_addr], player_name)
        self.player_add_queue.append(update)

    def _update_commands(self, player_inputs, player_addr):
        player_inputs = source.network.decode_inputs(player_inputs)
        if player_addr in self.addr_to_id:
            player_id = self.addr_to_id[player_addr]
            update = (player_id, player_inputs)
            self.player_input_queue.append(update)
        else:
            self._disconnect_player(cfg.NOT_CONNECTED_MESSAGE, player_addr)

    def _update_ping(self, prev_server_pulse, player_addr):
        if player_addr in self.addr_to_id:
            player_id = self.addr_to_id[player_addr]
            # Only keep most recent round-trip-time
            if prev_server_pulse > self.id_map[player_id][2]:
                self.id_map[player_id][2] = prev_server_pulse
                self.id_map[player_id][3] = time.time() - prev_server_pulse
        else:
            self._disconnect_player(cfg.NOT_CONNECTED_MESSAGE, player_addr)

    def _update_acks(self, packet_id, player_addr):
        self.ack_reception_queue.append((packet_id, player_addr))

    def _remove_player(self, player_id):
        self.player_remove_queue.append(player_id)

    def _connect_player(self, player_update, player_addr):
        self._send_message(cfg.CONNECT_CODE, player_update, player_addr)

    def _disconnect_player(self, message, player_addr):
        self._send_message(cfg.DISCONNECT_CODE, message, player_addr)
