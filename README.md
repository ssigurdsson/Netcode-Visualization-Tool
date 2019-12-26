# Netblob

Netblob, a networkcode visualization tool, is originally based on a online game [Agar.io](https://agar.io). The tool consists both server and client side. The former handles all incoming connections and manages the game. The latter deals with the game play. 

Data analysis about this project is also conducted. The results are shown in the file [data_analysis.pdf](data_analysis.pdf).

### Prerequisites

* Python 3.x
* Pygame

### How to run

 First, you need to set up server. After server is running, we can then add client(s).

```
python netblob.py
```


```
python client_game.py
```

### How to play


In the main menu, the user can mannualy input a player name and server IP (local or public).

In the server view, the user can see information about number of active players, frames per second of the server view, and the total server bandwidth being used.

In the client side, the user can play with **mouse movement, mouse left/right clicks, W/E, S/D, X/C keys** on the keyboard. 
* Mouse movement controls the direction of the user's orbit.
* Mouse left click shows the past player position, which tracks the players local position back in time (substract the pingh from the local time to estimate server time).
* Mouse right click shows the server player position, which tracks the position of the player according to the last game state received from the server in real time.
* W/E keys changes the ping.
* S/D keys changes the package loss rate.
* X/C keys changes the lag spike duration.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
