"""docstring"""
import sys
import socket
from core_game import Network, UserInputs, Player, Orb
from config import *
import threading
import pickle
import time
import random
import math
import collections


class Server(Network):
	
	def __init__(self):
		self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		#self.client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.SERVER_ADDR = ("", NETWORK_PORT)
		self.server_socket.settimeout(1)
		self.server_socket.bind(self.SERVER_ADDR)

		self.RUN_SERVER = False
		self.packet_id, self.player_id = 0, 0
		self.player_input_queue = collections.deque([],1024)
		self.player_update_queue = collections.deque([],1024)
		self.ack_update_queue = collections.deque([], 12800)
		self.ping_queue = collections.deque([], 12800)

		self.last_probe_time = time.time()
		self.data_load = 0
		self.connection_statistics = 0

		self.connected_addresses = set()
		self.id_map = {}
		self.addr_to_id = {}
		self.server_time = time.time()
		self.last_transmit_time = self.server_time

	def start(self):
		if not self.RUN_SERVER:
			self.RUN_SERVER = True
			threading.Thread(target=self._handle_acknowledgements).start()
			threading.Thread(target=self._handle_incoming_connections).start()
			local_address = socket.gethostbyname(socket.gethostname())
			print("[SERVER] Server Started with local address:", local_address)

	def stop(self):
		self.RUN_SERVER = False
		self.packet_id = 0

	def get_player_updates(self):
		return self.player_update_queue

	def get_player_inputs(self):
		return self.player_input_queue

	def drop_player(self, player_id):
		if player_id in self.id_map:
			player_addr = self.id_map[player_id][0]
			del self.id_map[player_id]
			del self.addr_to_id[player_addr]
			self.connected_addresses.discard(player_addr)

	def needs_sync(self):
		self.server_time = time.time()
		return self.server_time - self.last_transmit_time > SERVER_TRANSMIT_INTERVAL

	def sync_state(self, players, orb_contexts, player_deaths):
		"""Transmit data, then add or removes players"""
		for player_id, orb_context in orb_contexts:
			player_addr, _, curr_orb_context, _ = self.id_map[player_id]
			orb_update = []
			for orb in orb_context:
				if orb not in curr_orb_context:
					curr_orb_context.add(orb)
					orb_update.append( (True, self.encode_orb(orb)) )
			for orb in list(curr_orb_context):
				if orb not in orb_context:
					curr_orb_context.discard(orb)
					orb_update.append( (False, self.encode_orb(orb)) )

			if orb_update:
				self.packet_id += 1
				self.ack_update_queue.append((False, (player_addr, self.packet_id, self.server_time, UPDATE_ORBS_CODE, orb_update)))
				self._send_message((UPDATE_ORBS_CODE, (self.packet_id, orb_update)), player_addr)

		transmit = [(player_id, self.encode_player(player)) for player_id, player in players.items()]
		while player_deaths:
			player_id = player_deaths.pop()
			player_addr = self.id_map[player_id][0]
			self.packet_id += 1
			self.ack_update_queue.append((False, (player_addr, self.packet_id, self.server_time, PLAYER_DEATH_CODE, transmit)))
			self._send_message((PLAYER_DEATH_CODE, (self.packet_id, transmit)), player_addr)

		for player_id, player in players.items():
			player_addr, player_time, _, player_ping = self.id_map[player_id]
			if self.server_time - player_time >= TIMEOUT_LIMIT:
				pass
				try: 
					self._remove_player(player_id,player_addr)
					self.drop_player(player_id)
				except: pass
			else:
				if self.server_time - player_time >= PLAYER_INTERRUPT_LIMIT:
					default_inputs = self.encode_inputs(UserInputs())
					self._update_commands(default_inputs, player_addr)

				self._send_message((UPDATE_PLAYERS_CODE, (transmit, player_ping, self.server_time)), player_addr)
		self._update_connection_statistics()
		self.last_transmit_time = self.server_time = time.time()
		return self.server_time

	def get_connection_statistics(self):
		return self.connection_statistics

	def _update_connection_statistics(self):
		if self.server_time - self.last_probe_time > 10*CLIENT_TRANSMIT_INTERVAL:
			bandwidth = self.data_load/(self.server_time - self.last_probe_time)
			self.connection_statistics = bandwidth
			self.data_load = 0
			self.last_probe_time = self.server_time

	def _send_message(self, message, addr):
		data = pickle.dumps(message)
		self.data_load += sys.getsizeof(data)+28
		self.server_socket.sendto(data, addr)

	def _handle_acknowledgements(self):
		"""d"""
		unacked_packets = {}
		while self.RUN_SERVER:
			while self.ack_update_queue:
				ack, data = self.ack_update_queue.popleft()
				if ack:
					packet_id, player_addr = data
					if packet_id in unacked_packets and unacked_packets[packet_id][0] == player_addr:
						del unacked_packets[packet_id]
				else:
					player_addr, packet_id, server_time, code, updates = data
					unacked_packets[packet_id] = (player_addr, code, updates, server_time)

			for packet_id, (player_addr, code, updates, past_server_time) in list(unacked_packets.items()):
				if self.server_time - past_server_time > TIMEOUT_LIMIT or \
						player_addr not in self.connected_addresses:
					del unacked_packets[packet_id]
				else:
					self._send_message((code, (packet_id, updates)), player_addr)
			time.sleep(ACK_INTERVAL)


	def _handle_incoming_connections(self):
		while self.RUN_SERVER:
			try:
				data, addr = self.server_socket.recvfrom(1024)
				self.data_load += sys.getsizeof(data)+28
				code, data = pickle.loads(data)

				if code == CONNECT_CODE: self._add_new_player(data, addr)
				elif code == KEY_PRESSES_CODE: self._update_commands(data, addr)
				elif code == ACK_CODE: self._update_acks(data, addr)
				elif code == PING_CODE: self._update_ping(data, addr)
				elif code == DISCONNECT_CODE: self._remove_player(data, addr)

			except Exception as exc:
				if str(exc).startswith('[WinError 10054]'): continue  # Client dropped
				print("[SERVER] Incoming data reception failed for reasons:", exc)

	def _add_new_player(self, player, player_addr):
		if len(self.connected_addresses) >= PLAYER_LIMIT: 
			self._send_message((DISCONNECT_CODE, player_addr), player_addr)
		if player_addr not in self.connected_addresses:
			self.connected_addresses.add(player_addr)
			self.player_id += 1
			self.addr_to_id[player_addr] = self.player_id
			self.id_map[self.player_id] = [player_addr, self.server_time, set(), 0]
			self.player_update_queue.append( (True, (self.player_id, self.decode_player(player))) )
		player_id = self.addr_to_id[player_addr]
		self._send_message((CONNECT_CODE, player_id), player_addr)

	def _update_commands(self, player_inputs, player_addr):
		if player_addr in self.addr_to_id:
			player_id = self.addr_to_id[player_addr]
			self.player_input_queue.append((player_id, self.decode_inputs(player_inputs)))
		else:
			self._disconnect_player(player_addr)
	
	def _update_ping(self, server_pulse, player_addr):
		if player_addr in self.addr_to_id:
			player_id = self.addr_to_id[player_addr]
			if server_pulse > self.id_map[player_id][1]:
				self.id_map[player_id][1] = server_pulse
				self.id_map[player_id][3] = time.time() - server_pulse
		else:
			self._disconnect_player(player_addr)

	def _update_acks(self, packet_id, player_addr):
		self.ack_update_queue.append((True, (packet_id, player_addr)))

	def _remove_player(self, player_id, player_addr):
		if player_id == self.addr_to_id[player_addr]:
			self.player_update_queue.append((False, player_id))
			self._disconnect_player(player_addr)
			print('player disconnected')

	def _disconnect_player(self, player_addr):
		self._send_message((DISCONNECT_CODE, player_addr), player_addr)	