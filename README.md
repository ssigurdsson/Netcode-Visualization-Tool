# Net-Blob: Netcode Visualization Tool

This project aims to provide insight into the networking of online multiplayer games, or "netcode" as it is broadly termed. An authoritative server-client model enables gameplay inspired by the online game [Agar.io](https://agar.io), which is accompanied by controls that allow the user to simulate poor network conditions. As the subject of this project would suggest, the client employs a number of commonly used techniques for reducing the negative impact of such poor conditions. These techniques are discussed in the about section below.

### Prerequisites

* Python 3.x
* Pygame

### Platforms

The game is developed and tested on Windows 10, although other Platforms should be supported.

### How to run

For installation of Pygame refer to [these instructions](https://www.pygame.org/wiki/GettingStarted). Generally, this will be a simple "pip install" instruction i.e.
```
pip intall Pygame
```
A local server may be started by running launch_server.py. This file specifies the size of the map, the orb density, and the number of bots running on the server.
```
python launch_server.py
```
Once the server is running, or one wishes to connect to a public server, the client game is launched by running netblob.py.
```
python netblob.py
```

### How to play
##### Client
The default IP address provided in the client menu is that of the user's own system (local address). Thus, if connecting to a server running on the same machine as the client, the default address should work. If connecting to a server running on a different machine, either the local or public IP address of that server will need to be provided at this stage, depending on whether it's running on the local network or not. Then, once the player's name is entered, the "Start Game" button will attempt to connect the player to the server.

![Game Menu](figures/client_menu.png)

The figure below provides a brief snapshot of the gameplay. Note that a "lag spike" duration of 1 second is enabled. This means that every 10 seconds, the connection to the server will drop for exactly 1 second, which is seen early on in the gameplay below. The scoreboard is displayed in the top-right corner, while the player's own score, frame rate, and connection statistics are displayed in the top-left corner.

![Client View](figures/client_view.png)

The client receives **input** from the player by mouse, as well as the keys  W/E, S/D, X/C, and the keys 1/2/3. 
* *Mouse position* - controls the character's movement.
* *Mouse left-click* - toggles the past player tracker.
* *Mouse right-click* - toggles the server player tracker.
* *W/E keys* - adjust the simulated round-trip-time (ping).
* *S/D keys* - adjust the simulated package loss rate.
* *X/C keys* - adjust the simulated "lag spike" duration.
* *1/2/3 keys* - adjust the window display size.


##### Server
On the server side, the scoreboard is again displayed in the top-right corner, while the number of players, game frame rate, and server data usage are displayed in the top-left corner. The server provides the option of generating autonomous bots that interact with real players. **The players' (and bots') views may be cycled through by clicking the left and right mouse buttons.** This is seen in the figure below, which presents a brief snapshot of the server view of an ongoing game.

![Server View](figures/server_view.png)


### About

This project aims to provide insight into the networking of online multiplayer games, or "netcode" as it is broadly termed. An authoritative server-client model is used to enable gameplay inspired by the online game [Agar.io](https://agar.io), which is accompanied by controls that allow the user to simulate poor network conditions. Note that all of the project code is original work.

The client employes a number of techniques to reduce the impact of poor network conditions. One such technique is termed "movement prediction". In order to provide players with responsive movement of their character under poor network conditions, each client simulates player movement locally, and then retroactively corrects for discrepancies with the authoritative server game state in order to prevent decoherence over time. This process is visualized by the in-game "Trackers", which display the player's last received position from the server, along with the player's local position in the past. The past position is chosen to correspond to the time difference between the server state and the local state i.e. the server-client rount-trip-time. In other words, the past position corresponds to the player's local position from exactly one round-trip-time ago. The difference in position of the two trackers is used to perform the corrections needed to prevent decoherence over time.

Another important factor is the load impacted on the client's connection by the frequent server updates. Clients may have limited connection speeds, and so it is important that updates be concisely communicated, while still preserving the integrity of the gameplay. To that end, visible player positions are communicated to clients on a best-effort-basis at high frequency, while updates relating to orbs are communicated more conservatively with each update being acknowledged. It is also important to allow for updates to be received and processed out of order to minimize the impact of what's known as "packet loss". Updates are thus communicated by User Datagram Protocol (UDP) sockets, to avoid the restrictions on packet order set by Transmission Control Protocol (TCP) sockets.

The above provides only a narrow view of the full scope of networking issues addressed. For a broad summary of conventional networking  problems and techniques used for online games see [this article](https://medium.com/@meseta/netcode-concepts-part-1-introduction-ec5763fe458c) or [this video](https://www.youtube.com/watch?v=vTH2ZPgYujQ). For implementation details of many of these techniques see the python files for the server + client code.

Lastly, in order to support large numbers of clients playing simultaneously in the same environment, it is important that the server-side game logic scale appropriately with player count and map size. On the client side, emphasis must be put on rendering the visuals of the game efficiently in order to support the high frame rate needed for a smooth playing experience. This is explored in the file labeled [REPORT.md](REPORT.md).

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
