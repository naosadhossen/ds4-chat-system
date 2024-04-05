import tkinter
import tkinter as tk
import socket
import threading
from tkinter import messagebox
import ssl
from datetime import datetime

# Section for Global Parameters
client = None
HOST_ADDR = ""
HOST_PORT = ""
username = " "
user = " "

# Client GUI
window = tk.Tk()
window.title("Client")


def on_window_closing():
    if messagebox.askokcancel("Quit", "Do you really want to quit?"):
        if client:
            print("Disconnect")
            try:
                msg = "Exit-chat"
                client.send(msg.encode())
            except Exception as e:
                print(e)
            else:
                client.close()
        window.destroy()


window.protocol("WM_DELETE_WINDOW", on_window_closing)

# Frame for Server IP and Port Input
serverFrame = tk.Frame(window)
lblHostIP = tk.Label(serverFrame, text="Host IP:")
lblHostIP.pack(side=tk.LEFT)
hostIP = tk.Entry(serverFrame)
hostIP.pack(side=tk.LEFT)
lblHostPort = tk.Label(serverFrame, text="Port:")
lblHostPort.pack(side=tk.LEFT)
hostPort = tk.Entry(serverFrame)
hostPort.pack(side=tk.LEFT)
serverFrame.pack(side=tk.TOP)
# Frame for nickname and connect button
topFrame = tk.Frame(window)
lblName = tk.Label(topFrame, text="Nickname:")
lblName.pack(side=tk.LEFT)
userName = tk.Entry(topFrame)
userName.pack(side=tk.LEFT)
btnConnectDisconnect = tk.Button(topFrame, text="Connect", command=lambda: connect())
btnConnectDisconnect.pack(side=tk.LEFT)
topFrame.pack(side=tk.TOP)
# Frame for message display
messageDisplayFrame = tk.Frame(window)
lblBanner = tk.Label(messageDisplayFrame, text="Chat Message and Server Message")
scrollBar = tk.Scrollbar(messageDisplayFrame)
scrollBar.pack(side=tk.RIGHT, fill=tk.Y)
tkMessageDisplay = tk.Text(messageDisplayFrame, height=20, width=55)
tkMessageDisplay.pack(side=tk.LEFT, fill=tk.Y, padx=(5, 0))
tkMessageDisplay.tag_config("tag_your_message", foreground="green")
scrollBar.config(command=tkMessageDisplay.yview)
tkMessageDisplay.config(yscrollcommand=scrollBar.set, background="white", state="disabled")
messageDisplayFrame.pack(side=tk.TOP)
# Frame for message input
bottomInputFrame = tk.Frame(window)
lblInputBanner = tk.Label(bottomInputFrame, text="Type your message here")
tkServerMessage = tk.Text(bottomInputFrame, height=2, width=55)
tkServerMessage.pack(side=tk.LEFT, padx=(5, 13), pady=(5, 10))
tkServerMessage.config(highlightbackground="grey", state="disabled")
tkServerMessage.bind("<Return>", (lambda event: my_chat_message(tkServerMessage.get("1.0", tk.END))))
bottomInputFrame.pack(side=tk.BOTTOM)

# Section for Functions
# Connect to Chat Server
def connect():
    global user, HOST_PORT, HOST_ADDR, client
    # Validation placeholder for Chat Server Host IP, Port and Name
    if len(hostIP.get()) < 1 or len(hostPort.get()) < 1 or len(userName.get()) < 1:
        tk.messagebox.showerror(message="Please enter IP, Port and Name properly to join Chat")
    else:
        user = userName.get()
        HOST_ADDR = hostIP.get()
        HOST_PORT = int(hostPort.get())
        try:
            btnConnectDisconnect.config(text="Connect", command=lambda: connect(), state=tk.DISABLED)
            userName.config(state=tk.DISABLED)
            hostIP.config(state=tk.DISABLED)
            hostPort.config(state=tk.DISABLED)
            btnConnectDisconnect.config(state=tk.DISABLED)
            tkServerMessage.config(state=tk.NORMAL)
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Connection encryption
            ssl_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
            ssl_context.check_hostname = False  # Disable hostname verification
            ssl_context.verify_mode = ssl.CERT_NONE  # Disable certificate validation
            client = ssl_context.wrap_socket(client, server_hostname=HOST_ADDR)
            client.connect((HOST_ADDR, HOST_PORT))
            # btnConnectDisconnect.config(text="Disconnect", command=lambda: disconnect(), state=tk.NORMAL)
            client.send(user.encode())  # Send client name  to server after connecting
            # start a thread to keep receiving message from server
            thread_handle_server_message = threading.Thread(target=handle_server_message, args=(client, "m"))
            thread_handle_server_message.start()
        except Exception as e:
            userName.config(state=tk.NORMAL)
            btnConnectDisconnect.config(state=tk.NORMAL)
            tkServerMessage.config(state=tk.NORMAL)
            tk.messagebox.showerror(title="ERROR!!!", message="Cannot connect to host: " + HOST_ADDR
                                                              + " on port: " + str(HOST_PORT)
                                                              + " Server may be Unavailable. Try again later")
            btnConnectDisconnect.config(text="Connect", command=lambda: connect(), state=tk.NORMAL)
            return e

# Disconnect from Chat Server
def disconnect():
    print("Disconnect")
    try:
        msg = "Exit-chat"
        send_message_to_server(msg)
    except Exception as e:
        print(e)
    else:
        btnConnectDisconnect.config(text="Connect", command=lambda: connect(), state=tk.NORMAL)
        hostIP.config(state=tk.NORMAL)
        hostPort.config(state=tk.NORMAL)
        userName.config(state=tk.NORMAL)
        btnConnectDisconnect.config(text="Connect", command=lambda: connect(), state=tk.NORMAL)
        window.title("Client")

def handle_server_message(sck, m):
    global user
    while True:
        msg_from_server = sck.recv(4096)
        if not msg_from_server:
            tkMessageDisplay.config(state=tk.NORMAL)
            timestamp = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
            tkMessageDisplay.insert(tk.END, f"\n {timestamp} => Lost the connection to the server. Please try again later.")
            break
        message = msg_from_server.decode().strip()
        if message == "BYE!":
            tkMessageDisplay.config(state=tk.NORMAL)
            timestamp = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
            tkMessageDisplay.insert(tk.END, f"\n {timestamp} => " + message + " Server is shutting down. Please try again later.")
            btnConnectDisconnect.config(text="Connect", command=lambda: connect(), state=tk.NORMAL)
            hostIP.config(state=tk.NORMAL)
            hostPort.config(state=tk.NORMAL)
            break
        if message == "CLIENTSHUT!":
            tkMessageDisplay.config(state=tk.NORMAL)
            # Get timestamp
            timestamp = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
            tkMessageDisplay.insert(tk.END, f"\n {timestamp} => Connection to server is terminated.")
            btnConnectDisconnect.config(text="Connect", command=lambda: connect(), state=tk.NORMAL)
            hostIP.config(state=tk.NORMAL)
            hostPort.config(state=tk.NORMAL)
            break

        if message.startswith("##"):    # Welcome message
            print("Received welcome message")
            btnConnectDisconnect.config(text="Disconnect", command=lambda: disconnect(), state=tk.NORMAL)
            hostIP.config(state=tk.DISABLED)
            hostPort.config(state=tk.DISABLED)
            userName.config(state=tk.DISABLED)
            window.title("Client- " + user)

        if message.startswith("%%"):   # Join channel message
            channel_name = message.split(":", 1)[1]
            window.title("Client- " + user + "-" + channel_name)

        if message.startswith("&&"):    # Exit channel message
            window.title("Client- " + user)
        # display message from server in tkMessageDisplay
        texts = tkMessageDisplay.get("1.0", tk.END).strip()
        tkMessageDisplay.config(state=tk.NORMAL)
        if len(texts) < 1:
            tkMessageDisplay.insert(tk.END, message)
        else:
            tkMessageDisplay.insert(tk.END, "\n\n" + message)
        tkMessageDisplay.config(state=tk.DISABLED)
        tkMessageDisplay.see(tk.END)

    sck.close()
    window.title("Client")
    btnConnectDisconnect.config(text="Connect", command=lambda: connect(), state=tk.NORMAL)
    userName.config(state=tk.NORMAL)
    btnConnectDisconnect.config(state=tk.NORMAL)
    tkServerMessage.config(state=tk.DISABLED)
    # window.destroy()

def my_chat_message(msg):
    print("OK")
    msg = msg.replace('\n', '')
    texts = tkMessageDisplay.get("1.0", tk.END).strip()
    # enable the display area and insert the text and then disable.
    tkMessageDisplay.config(state=tk.NORMAL)
    if len(texts) < 1:
        tkMessageDisplay.insert(tk.END, "You->" + msg, "tag_your_message") # no line
    else:
        tkMessageDisplay.insert(tk.END, "\n\n" + "You->" + msg, "tag_your_message")

    tkMessageDisplay.config(state=tk.DISABLED)

    send_message_to_server(msg)

    tkMessageDisplay.see(tk.END)
    tkServerMessage.delete('1.0', tk.END)


def send_message_to_server(msg):
    client_msg = str(msg)
    client.send(client_msg.encode())
    print("Sending message")

# Main
window.mainloop()

