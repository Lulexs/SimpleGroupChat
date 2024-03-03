import sys
import socket
import selectors
import srv_sock_wrapper
import traceback

sel = selectors.DefaultSelector()

client_sockets = []

def accept_wrapper(sock):
    conn, addr = sock.accept()
    print(f"Accepted connection from {addr}")
    conn.setblocking(False)
    sock_wrapper = srv_sock_wrapper.SocketWrapper(sel, conn, addr, other_sockets=client_sockets)
    sel.register(conn, selectors.EVENT_READ | selectors.EVENT_WRITE, data=sock_wrapper)
    client_sockets.append(sock_wrapper)

if len(sys.argv) != 3:
    print(f"Usage: {sys.argv[0]} <host> <port>")
    sys.exit(1)

host, port = sys.argv[1], int(sys.argv[2])
lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
lsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
lsock.bind((host, port))
lsock.listen()
print(f"Listening on {host}:{port}")
lsock.setblocking(False)
sel.register(lsock, selectors.EVENT_READ, data=None)

try:
    while True:
        events = sel.select(timeout=None)
        for key, mask in events:
            if key.data is None:
                accept_wrapper(key.fileobj)
            else:
                sock_wrapper = key.data
                try:
                    sock_wrapper.process_events(mask)
                except Exception:
                    print(f"Main: Error: Exception for {sock_wrapper.addr}:\n{traceback.format_exc()}")
                    sock_wrapper.close()
except KeyboardInterrupt:
    print("Keyboard interrupt caught, exiting")
finally:
    sel.close()