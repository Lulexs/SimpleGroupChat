import threading
import time
import sys
import socket
import selectors
import cli_sock_wrapper


LOCK = threading.Lock()  # lock to avoid mixing messages while printing
sel = selectors.DefaultSelector()
messages_to_send = []
recv_messages = []
print_next_more = True

if len(sys.argv) != 3:
    print(f"Usage: {sys.argv[0]} <host> <port>")
    sys.exit(1)

def print_message(message):
    """ print the received message line by line above the input line"""
    with LOCK:
        for line in str.splitlines(message):
            print(
                "\u001B[s"             # Save current cursor position
                "\u001B[A"             # Move cursor up one line
                "\u001B[999D"          # Move cursor to beginning of line
                "\u001B[S"             # Scroll up/pan window down 1 line
                "\u001B[L",            # Insert new line
                 end="")     
            print(line, end="")        # Print message line
            print("\u001B[u", end="")  # Move back to the former cursor position
        print("", end="", flush=True)  # Flush message

def receive():
    while True:
        time.sleep(2)
        if recv_messages:
            message = recv_messages.pop(0)
            print_message(message)
            
            
def write():
    while True:
        x = input('>(You) ')
        messages_to_send.append(x)


def start_connection(host, port):
    addr = (host, port)
    print(f"Starting connection to {addr}")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setblocking(False)
    sock.connect_ex(addr)
    events = selectors.EVENT_READ | selectors.EVENT_WRITE
    sock_wrapper = cli_sock_wrapper.SockWrapper(sel, sock, addr)
    sel.register(sock, events, data=sock_wrapper)


host, port = sys.argv[1], int(sys.argv[2])
start_connection(host, port)


for i in range(30):
    print(">")
print("To set username type '!username! <username>'")
receive_thread = threading.Thread(target=receive)
receive_thread.daemon = True
receive_thread.start()
write_thread = threading.Thread(target=write)
write_thread.daemon = True
write_thread.start()

try:
    while True:
        events = sel.select(timeout=None)
        for key, mask in events:
            sock_wrapper = key.data
            if mask & selectors.EVENT_READ:
                recv_message = sock_wrapper.process_read()
                if recv_message != None:
                    recv_messages.append(recv_message)
            if mask & selectors.EVENT_WRITE and messages_to_send:
                sock_wrapper.process_write(messages_to_send.pop(0))
except KeyboardInterrupt:
    print("Caught keyboard interrupt, exiting")
finally:
    sel.close()
