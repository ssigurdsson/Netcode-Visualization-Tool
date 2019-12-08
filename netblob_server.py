"""docstring"""
import sys
import socket
from netblob_entities import UserInputs
import netblob_network
from netblob_config import *
import threading
import pickle
import time
import collections


class Server:
	"""dd"""
	def __init__(self):
		self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.server_socket.bind(("", NETWORK_PORT))
		self.server_socket.settimeout(1)

		self.run = False
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
			for thread in self.threads: thread.start()
			local_addr = socket.gethostbyname(socket.gethostname())
			print("[SERVER] Server Started with local address:", local_addr)
			print("[SERVER] For players to connect by public IP, port " \
				+ "forwarding may be necessary on port:", str(NETWORK_PORT))

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

	def drop_player(self, player_id):
		if player_id in self.id_map:
			player_addr = self.id_map[player_id][0]
			if player_addr in self.addr_to_id:
				del self.addr_to_id[player_addr]
			self.connected_addresses.discard(player_addr)
			del self.id_map[player_id]

	def needs_sync(self):
		self.server_time = time.time()
		time_passed = self.server_time - self.last_sync_time
		return time_passed > SERVER_SYNC_INTERVAL

	def sync_state(self, players, orb_contexts, player_deaths):
		"""Transmit data, then add or removes players"""
		self._transmit_orbs(orb_contexts)
		self._transmit_players(players, player_deaths)
		self._update_connection_statistics()
		self.last_sync_time = self.server_time = time.time()
		return self.server_time

	def get_connection_statistics(self):
		return self.connection_statistics

	def _update_connection_statistics(self):
		if self.server_time - self.last_probe_time > STATS_PROBE_INTERVAL:
			bw = self.data_load/(self.server_time - self.last_probe_time)
			self.data_load = 0
			self.connection_statistics[0] = bw
			self.last_probe_time = self.server_time

	def _transmit_orbs(self, orb_contexts):
		for player_id, new_orb_context in orb_contexts:
			player_addr, curr_orb_context, _, _ = self.id_map[player_id]
			orb_additions, orb_removals = [], []
			for orb in new_orb_context:
				if orb not in curr_orb_context:
					curr_orb_context.add(orb)
					orb_additions.append(netblob_network.encode_orb(orb))
			for orb in list(curr_orb_context):
				if orb not in new_orb_context:
					curr_orb_context.discard(orb)
					orb_removals.append(netblob_network.encode_orb(orb))
			if orb_additions or orb_removals:
				orb_updates = (orb_additions,orb_removals)
				self.packet_id += 1
				update = (player_id, player_addr, self.packet_id, \
					self.server_time, UPD_ORBS_CODE, orb_updates)
				self.ack_transmission_queue.append(update)
				message = (self.packet_id, orb_updates)
				self._send_message(UPD_ORBS_CODE, message, player_addr)

	def _transmit_players(self, players, player_deaths):
		transmit = []
		for player_id, player in players.items():
			transmit.append((player_id, netblob_network.encode_player(player)))
		transmit = (transmit, self.server_time)

		for player_id, player in players.items():
			player_addr, _, player_time, player_ping = self.id_map[player_id]
			if self.server_time - player_time >= TIMEOUT_LIMIT:
				self._remove_player(player_id)
			else:
				if self.server_time - player_time >= PLAYER_INTERRUPT_LIMIT:
					default_inputs = netblob_network.encode_inputs(UserInputs())
					self._update_commands(default_inputs, player_addr)

				if player_id in player_deaths:
					self.packet_id += 1
					update = (player_id, player_addr, self.packet_id,\
							self.server_time, DEATH_CODE, transmit)
					self.ack_transmission_queue.append(update)
					message = (self.packet_id, transmit)
					self._send_message(DEATH_CODE, message, player_addr)
				else:
					message = (transmit, player_ping)
					self._send_message(UPD_PLAYERS_CODE, message, player_addr)

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
				if self.server_time - past_server_time > TIMEOUT_LIMIT or \
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

			time.sleep(ACK_INTERVAL)


	def _retrieve_messages(self):
		while self.run:
			try:
				data, addr = self.server_socket.recvfrom(2048)
				self.data_load += sys.getsizeof(data)+28
				code, data = pickle.loads(data)

				if code == CONNECT_CODE:
					self._add_new_player(data, addr)
				elif code == INPUTS_CODE:
					self._update_commands(data, addr)
				elif code == ACK_CODE:
					self._update_acks(data, addr)
				elif code == PING_CODE:
					self._update_ping(data, addr)
				elif code == DISCONNECT_CODE:
					self._remove_player(data)

			except Exception as exc:
				if str(exc).startswith('[WinError 10054]'): continue
				print("[SERVER] Data reception failed for reasons:", exc)

	def _add_new_player(self, player, player_addr):
		if len(self.connected_addresses) >= PLAYER_LIMIT:
			self._disconnect_player(SERVER_FULL_MSG, player_addr)
			return
		if player_addr not in self.connected_addresses:
			self.connected_addresses.add(player_addr)
			self.player_id += 1
			self.addr_to_id[player_addr] = self.player_id
			# Player info includes Ip address, orb_context, heartbeat, ping
			player_info = [player_addr, set(), self.server_time, 0]
			self.id_map[self.player_id] = player_info
			update = (self.player_id, netblob_network.decode_player(player))
			self.player_add_queue.append(update)
		player_id = self.addr_to_id[player_addr]
		self._send_message(CONNECT_CODE, player_id, player_addr)

	def _update_commands(self, player_inputs, player_addr):
		if player_addr in self.addr_to_id:
			player_id = self.addr_to_id[player_addr]
			update = (player_id, netblob_network.decode_inputs(player_inputs))
			self.player_input_queue.append(update)
		else:
			self._disconnect_player(DISCONNECTED_MSG, player_addr)

	def _update_ping(self, prev_server_pulse, player_addr):
		if player_addr in self.addr_to_id:
			player_id = self.addr_to_id[player_addr]
			# Only keep most recent round-trip-time
			if prev_server_pulse > self.id_map[player_id][2]:
				self.id_map[player_id][2] = prev_server_pulse
				self.id_map[player_id][3] = time.time() - prev_server_pulse
		else:
			self._disconnect_player(DISCONNECTED_MSG, player_addr)

	def _update_acks(self, packet_id, player_addr):
		self.ack_reception_queue.append((packet_id, player_addr))

	def _remove_player(self, player_id):
		self.player_remove_queue.append(player_id)

	def _disconnect_player(self, message, player_addr):
		self._send_message(DISCONNECT_CODE, message, player_addr)