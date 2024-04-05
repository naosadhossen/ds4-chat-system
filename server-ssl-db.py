import tkinter as tk
from tkinter import messagebox
import socket
import threading
import ssl
import psycopg2
from psycopg2 import Error


# Connect to DB
try:
    db_connection = psycopg2.connect(
        user="naosadhossen",
        password="",
        host="127.0.0.1",
        port="5432",
        database="postgres"

    )
except Error as e:
    print("Error occured during connecting to DB", e)

# Section for Global Parameters
server = None
HOST_ADDR = "127.0.0.1"
HOST_PORT = 8080
active_clients_connections = [] # list of active connections
active_clients_names = [] # list of active users
clients_to_connection_dict = {} # dictionary of a user to its socket connection string mapping
connection_to_client_dict = {} # dictionary of a socket connection string to its user
channels = [] # list of channels
channel_owner = {} # dictionary of channels and its owner
channel_users = [] # list of channels and its user's socket connection string
users_channels = {} # dictionary for user socket connection string to channel mapping


# Server Console
window = tk.Tk()
window.title("ChatServer")


# Top frame consisting of a toggle button to start stop the Chat Server
topControlFrame = tk.Frame(window)
btnStartStopServer = tk.Button(topControlFrame, text="Start Chat Server", command=lambda: start_server())
btnStartStopServer.pack(side=tk.LEFT)
topControlFrame.pack(side=tk.TOP, pady=(10, 0))
# Middle frame consisting of two labels for displaying the host and port info of the Chat Server
middleServerInfoFrame = tk.Frame(window)
lblHostIP = tk.Label(middleServerInfoFrame, text="Host:____")
lblHostIP.pack(side=tk.LEFT)
lblHostPort = tk.Label(middleServerInfoFrame, text="Port:____")
lblHostPort.pack(side=tk.LEFT)
middleServerInfoFrame.pack(side=tk.TOP, pady=(10, 0))
# Bottom frame displays the active clients in Chat Server
bottomActiveClientListFrame = tk.Frame(window)
lblLine = tk.Label(bottomActiveClientListFrame, text="List of Connected Clients")
scrollBar = tk.Scrollbar(bottomActiveClientListFrame)
scrollBar.pack(side=tk.RIGHT, fill=tk.Y)
tkDisplay = tk.Text(bottomActiveClientListFrame, height=15, width=30)
tkDisplay.pack(side=tk.LEFT, fill=tk.Y, padx=(10, 0))
scrollBar.config(command=tkDisplay.yview)
tkDisplay.config(yscrollcommand=scrollBar.set, background="white", state="disabled")
bottomActiveClientListFrame.pack(side=tk.BOTTOM, pady=(10, 10))


def on_window_closing():
    if messagebox.askokcancel("Quit", "Do you really want to quit?"):
        if server:
            print("Disconnect")
            try:
                for c in active_clients_connections:
                    server_msg = "BYE!"
                    c.send(server_msg.encode())
                    c.close()
            except Exception as error:
                print(error)
            else:
                server.close()
        window.destroy()


window.protocol("WM_DELETE_WINDOW", on_window_closing)

# Section for Functions

# Start Server Function
def start_server():
    global server, HOST_ADDR, HOST_PORT
    btnStartStopServer.config(state=tk.DISABLED)
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST_ADDR, HOST_PORT))
    server.listen()  # server is listening for client connection
    # Encrypt server connection
    ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_context.load_cert_chain(certfile="server.crt", keyfile="server.key")
    server = ssl_context.wrap_socket(server, server_side=True)
    print(server)
    lblHostIP["text"] = "Host: " + HOST_ADDR
    lblHostPort["text"] = "Port: " + str(HOST_PORT)
    btnStartStopServer.config(text="Stop Chat Server", command=lambda: stop_server(), state=tk.NORMAL)

    client_connect_threads = threading.Thread(target=handler_client_connection, args=(server, ""))
    client_connect_threads.start()
    update_console_display()

    # threading._start_new_thread(handler_client_connection, (server, ""))
    # cleanup database
    # clean_db()


# Stop Server Function
def stop_server():
    global server
    btnStartStopServer.config(state=tk.DISABLED)
    for c in active_clients_connections:
        server_msg = "BYE!"
        c.send(server_msg.encode())
        c.close()
    active_clients_connections.clear()
    active_clients_names.clear()
    clients_to_connection_dict.clear()
    connection_to_client_dict.clear()
    channels.clear()
    channel_owner.clear()
    channel_users.clear()
    users_channels.clear()
    server.close()
    # update active client names in bottomActiveClientListFrame
    update_console_display()
    btnStartStopServer.config(text="Start Chat Server", command=lambda: start_server(), state=tk.NORMAL)
    lblHostIP.config(text="Host:____")
    lblHostPort.config(text="Port:____")

# Handle Client Connection
def handler_client_connection(server, na):
    while True:
        client_connection, addr = server.accept()
        active_clients_connections.append(client_connection)
        print(client_connection)
        print(active_clients_connections)
        # Start a thread for this connection to handle client message
        thread_handler_client_message = threading.Thread(target=handler_client_message, args=(client_connection, addr))
        thread_handler_client_message.start()
        # threading._start_new_thread(handler_client_message, (client_connection, addr))

# Update active client list in bottomActiveClientListFrame
def update_console_display():
    tkDisplay.config(state=tk.NORMAL)
    tkDisplay.delete('1.0', tk.END)
    db_cursor_list_channel = db_connection.cursor()
    list_channel_query = "SELECT * FROM channels"
    db_cursor_list_channel.execute(list_channel_query)
    rows = db_cursor_list_channel.fetchall()
    active_channel = []
    for channel in rows:
        active_channel.append(channel[0])
    db_cursor_list_channel.close()
    tkDisplay.insert(tk.END, "\n List of Active Clients\n" + str(active_clients_names) +
                     "\n List of Active Channels\n" +
                     str(active_channel) + "\n")
    # for client in active_clients_names:
        # tkDisplay.insert(tk.END, "\n List of Active Clients\n" + client + "\n")
    # for channel in channels:
        # tkDisplay.insert(tk.END, "\n List of Active Channels\n" + channel + "\n")
    tkDisplay.config(state=tk.DISABLED)

def channel_exist(channel):
    db_cursor_channel = db_connection.cursor()
    db_query_channel_name = f"SELECT * FROM Channels where channel_name='{channel}'"
    db_cursor_channel.execute(db_query_channel_name)
    existing_channels = db_cursor_channel.fetchall()
    print(existing_channels)
    if db_cursor_channel.rowcount == 0:
        print("Channel does not exist in DB")
        return 0
    if db_cursor_channel.rowcount >= 1:
        print("Channel exist in DB")
        return 1

def create_channel(channel, owner):
    db_cursor_create_channel = db_connection.cursor()
    channel_exist_check = channel_exist(channel)
    if channel_exist_check == 1:
        print("Channel exist in DB")
        return 0
    if channel_exist_check == 0:
        print("Creating new channel in DB")
        db_create_channel = f"Insert into channels (channel_name, channel_owner) values ('{channel}', '{owner}')"
        try:
            db_cursor_create_channel.execute(db_create_channel)
            db_connection.commit()
            return 1
        except Error as create_channel_error:
            print(f"Error: {create_channel_error}")


def handler_client_message(client_connection, client_ip_addr):
    print("inside handler_client_message")
    global active_clients_names, clients_to_connection_dict, connection_to_client_dict, channel_owner, channel_users, users_channels
    client_name = client_connection.recv(4096).decode()  # fetch the client name from connection

    # Local record for client and socket mapping
    clients_to_connection_dict[client_name] = client_connection
    connection_to_client_dict[client_connection] = client_name
    print(clients_to_connection_dict)
    print(connection_to_client_dict)

    # DB record for client and socket mapping
    db_cursor_active_users = db_connection.cursor()
    query_active_chat_users = f"SELECT * FROM active_users WHERE user_name='{client_name}'"
    db_cursor_active_users.execute(query_active_chat_users)
    # rows = db_cursor_active_users.fetchall()
    if db_cursor_active_users.rowcount == 0:
        print("New user")
        query_create_new_user = f"INSERT into active_users (user_name) values ('{client_name}');"
        db_cursor_active_users.execute(query_create_new_user)
        db_connection.commit()
    else:
        print("Existing user")
    db_cursor_active_users.close()

    # Welcome Message: Get all channels from DB and send to this client in the Welcome Message
    active_clients_names.append(client_name)   # Local record of active clients
    db_cursor_list_channel = db_connection.cursor()
    list_channel_query = "SELECT * FROM channels"
    db_cursor_list_channel.execute(list_channel_query)
    rows = db_cursor_list_channel.fetchall()
    active_channel = []
    for channel in rows:
        active_channel.append(channel[0])
    db_cursor_list_channel.close()
    welcome_msg = (f"##:Welcome {client_name} to the chat room."
                   f"\n Here is the active channels: {active_channel}. "
                   f"\nJoin one of the channel by sending Join-channel channel name in one message"
                   f"\nCurrent active users list: {active_clients_names}")
    client_connection.send(welcome_msg.encode())

    print(active_clients_names)
    # update active client names in server in box bottomClientListFrame
    update_console_display()

    # Notifying all active clients about this new joiner
    for c in active_clients_connections:
        if c != client_connection:
            server_msg = str(client_name + " has joined")
            c.send(server_msg.encode())

    # wait for client message
    while True:
        data = client_connection.recv(4096).decode()
        # idx = get_client_index(clients, client_connection)
        # sending_client_name = clients_names[idx]
        if not data:

            break
        else:
            client_message = data.strip()
            header = client_message.split(" ", 1)[0]
            match header:
                case "Exit-chat":
                    server_msg = "CLIENTSHUT!"
                    client_connection.send(server_msg.encode())
                    break
                case "List-channel":
                    print("List Channel")
                    db_cursor_list_channel = db_connection.cursor()
                    list_channel_query = "SELECT * FROM channels"
                    db_cursor_list_channel.execute(list_channel_query)
                    rows = db_cursor_list_channel.fetchall()
                    active_channel = []
                    for channel in rows:
                        active_channel.append(channel[0])
                    client_connection.send(f"Here is the list of active channels: {active_channel}".encode())
                    db_cursor_list_channel.close()
                case "Join-channel":
                    print("Join Channel")
                    if client_message.startswith("Join-channel"):
                        print("Join Channel")
                        message_word = client_message.split(" ", 1)
                        if len(message_word) < 2:
                            client_connection.send("No Channel name specified. Please provide a Channel name.".encode())
                        else:
                            channel_name = client_message.split(" ", 1)[1]
                            channel_exist_check = channel_exist(channel_name)
                            if channel_exist_check == 0:
                                client_connection.send(f"Channel name {channel_name} not found in DB".encode())
                                # if channel_name not in channels:
                                # client_connection.send(f"Channel name {channel_name} not found".encode())
                            if channel_exist_check == 1:
                                print(f"{client_name} with {client_connection}-Joining Channel")
                                users_channels[client_connection] = channel_name
                                print(users_channels)
                                # print(channel_users)
                                client_connection.send(f"%%:You are in channel {channel_name}\n".encode())
                                for member_connection in users_channels:
                                    if users_channels[member_connection] == users_channels[client_connection]:
                                        member_connection.send(f"{client_name} has joined the channel.".encode())
                                    else:
                                        client_connection.send(
                                                f"Currently no users in the Channel {users_channels[client_connection]}"
                                                .encode())
                                    update_console_display()
                case "Create-channel":
                    print("Create Channel")
                    if client_message.startswith("Create-channel"):
                        print("Create Channel")
                        message_word = client_message.split(" ", 1)
                        if len(message_word) < 2:
                            client_connection.send("No Channel name specified. Please provide a Channel name.".encode())
                        else:
                            channel_name = client_message.split(" ", 1)[1]
                            new_channel = create_channel(channel_name, client_name)
                            if new_channel == 0:
                                client_connection.send(f"Channel {channel_name} already exists in DB".encode())
                            if new_channel == 1:
                                users_channels[client_connection] = channel_name
                                client_connection.send(f"%%:You are in DB channel {channel_name}".encode())
                                update_console_display()  # update channels in console display # Update the server console display
                                for c in active_clients_connections:  # inform all active users about the new channel
                                    server_msg = str(
                                        f"A new Channel was created with name {channel_name} by {client_name}, You are welcome to join, type Join-channel {channel_name}".encode())
                                    c.send(server_msg.encode())
                            else:
                                client_connection.send(f"Channel {channel_name} already exists".encode())
                case "Exit-channel":
                    print("Exit Channel")
                    print(channel_users)
                    current_channel = users_channels[client_connection]
                    for member in users_channels:
                        if users_channels[member] == users_channels[client_connection]:
                            announce_exit = f"\n{client_name} has left the channel {current_channel}"
                            member.send(announce_exit.encode())
                    del users_channels[client_connection]
                    print(users_channels)
                    client_connection.send(f"&&:You left channel {current_channel}".encode())
                    print("Public message")

                case _:
                    if header.startswith("@"):
                        print("@")
                        private_recipient, message = client_message.split(" ", 1)
                        private_recipient = private_recipient[1:]  # Remove the @ symbol and fetch private recipient
                        if private_recipient in active_clients_names:
                            private_recipient_connection = clients_to_connection_dict[private_recipient]
                            private_recipient_connection.send(f"{client_name} (private): {message}".encode())
                        else:
                            client_connection.send(f"{private_recipient} does not exist".encode())
                    else:
                        print("Public message")
                        current_member = 0
                        if client_connection in users_channels.keys():
                            myChannel=users_channels[client_connection]
                            print(myChannel)
                            number_of_members = 0
                            for channel in users_channels.values():
                                if channel == users_channels[client_connection]:
                                    number_of_members += 1
                            if number_of_members <= 1:
                                client_connection.send(f"Currently no users in the Channel)".encode())
                            else:
                                for member in users_channels.keys():
                                    print(users_channels.keys())
                                    publicMsg = str(client_name + "(to all)->" + data)
                                    if users_channels[member] == myChannel:
                                        current_member = current_member+1
                                        member.send(publicMsg.encode())

    # Remove the client and connection
    if client_name in active_clients_names:
        active_clients_names.remove(client_name)
    update_console_display()  # update client names and channels in console display
    print(active_clients_names)
    if client_connection in active_clients_connections:
        active_clients_connections.remove(client_connection)
    print(active_clients_connections)
    if client_name in clients_to_connection_dict.keys():
        del clients_to_connection_dict[client_name]
    print(clients_to_connection_dict)
    if client_connection in users_channels.keys():
        del users_channels[client_connection]
    client_connection.close()


# Main
window.mainloop()
