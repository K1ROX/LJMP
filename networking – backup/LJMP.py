"""a multiplayer client using tkinter for the GUI that launches the multiplayer.py script passing adress of chosen server and player name as arguments
the multiplayer.py script will then connect to the server and start the game
there will be 2 main panels: local and internet
the local panel will have a button to start a local game and a button to connect to the chosen local server
basically we will copy samp style multiplayer menu but in tkinter and with the option to connect to local servers as well as internet servers
"""

from tkinter import *
from tkinter import messagebox
from tkinter import ttk
import tkinter as tk
from pathlib import Path
import subprocess
import threading
import socket
import json

current_directory = Path(__file__).parent

CLIENT_FILE_PATH = current_directory / "client.py"

window = Tk()

screen_width = window.winfo_screenwidth()
screen_height = window.winfo_screenheight()

WIDTH, HEIGHT = 1000, 720

x = (screen_width // 2) - (WIDTH // 2)
y = (screen_height // 2) - (HEIGHT // 2)

window.title("LJMP Client 0.1")
window.geometry(f'{WIDTH}x{HEIGHT}+{x}+{y}')
window.configure(bg="#d1d1d1")


username_label = Label(window, text="Username:", bg="#d1d1d1", font=("Arial", 14))
username_label.place(x=400, y=10)

username_input = Entry(window, font=("Arial", 14))
username_input.place(x=400, y=40)

username_input.insert(0, "calc0r")

username = username_input.get()


server_info = Label(window, text="Name:           |Gamemode:     |Players:   |Ip:             ", font=("Consolas", 16), bg="#dedede")
server_info.place(x=30,y=80)



listbox = Listbox(window, selectmode=tk.SINGLE, width=60, height=20, # <- SINGLE важливо
                  font=("Consolas", 16))  
listbox.place(x=30,y=110)

servers = []

class Server:
    def __init__(self, dict):
        self.__dict__.update(dict)
        servers.append(self)
    def __str__(self):
        # 16|14|11|16
        text = ""
        text += self.Name + "               "
        text = text[:16]
        text += "|"

        text += self.Gamemode + "               "
        text = text[:16+1+14]
        text += "|"

        text += self.Players + "/" + self.MaxPlayers + "               "
        text = text[:16+1+14+1+11]
        text += "|"

        text += self.Ip + "                "
        text = text[:16+1+14+1+11+1+16]
        return text


def update_servers():
    UDP_PORT = 5667
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    sock.sendto(json.dumps({"type": "get_server_info"}).encode(), ('<broadcast>', UDP_PORT))
    sock.settimeout(1)

    servers.clear()

    try:
        while True:
            data, addr = sock.recvfrom(1024)
            data = json.loads(data.decode())
            print(data)
            Server(data)
    except socket.timeout:
        pass


    listbox.delete(0, tk.END)
    for server in servers:
        listbox.insert(tk.END, str(server))
    
    window.after(20000, update_servers) # every 20 seconds auto update

update_servers()





def connect(*args): # *args щоб не було TypeError: connect() takes 0 positional arguments but 1 was given
    username = username_input.get()
    if not username:
        # pop a message box saying that the username is required
        messagebox.showerror("Error", "Username is required")
        return

    ip_adress = servers[listbox.curselection()[0]].Ip
    print(f"{ip_adress=}")

    if not ip_adress:
        ip_adress = adress_input.get()
        if not ip_adress:
            messagebox.showerror("Error", "IP address is required")
            return
        direct_connect_window.destroy()

    # launch the client.py script passing the username and ip adress as arguments
    # pop errors in a messagebox
    result = subprocess.run(
        ["python", CLIENT_FILE_PATH, username, ip_adress],
        check=False,                    # <--- Змінили на False
        capture_output=True,
        text=True,
        timeout=30
    )

    error_text = (result.stderr).strip()
    if error_text:
        messagebox.showerror("Error:", error_text)
    
def connect_via_Threading(*args):
    threading.Thread(target=connect).start()

listbox.bind("<Double-Button-1>", connect_via_Threading)



connect_btn = Button(window, text="Connect", font=("Arial", 14), command=connect_via_Threading)
connect_btn.place(x=400, y=650)



def direct_connect():
    global direct_connect_window, adress_input
    # pop a new window to enter the server address
    direct_connect_window = Toplevel(window)
    direct_connect_window.configure(bg="#d1d1d1")

    x = (screen_width // 2) - (400 // 2)
    y = (screen_height // 2) - (200 // 2)

    direct_connect_window.geometry(f"400x200+{x}+{y}")

    adress_label = Label(direct_connect_window, text="Server Address:", bg="#d1d1d1", font=("Arial", 14))
    adress_label.place(x=10, y=10)

    adress_input = Entry(direct_connect_window, font=("Arial", 14))
    adress_input.place(x=10, y=40)

    adress_input.insert(0, "127.0.0.1:5667")

    connect_direct_btn = Button(direct_connect_window, text="Connect", font=("Arial", 14), command=connect_via_Threading)
    connect_direct_btn.place(x=150, y=150)

direct_connect_btn = Button(window, text="Direct Connect", font=("Arial", 14), command=direct_connect)
direct_connect_btn.place(x=200, y=30)


update_servers_btn = Button(window, text="Update", font=("Arial", 14), command=update_servers)
update_servers_btn.place(x=800, y=30)

window.mainloop()