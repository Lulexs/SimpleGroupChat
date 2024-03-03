import selectors
import json
import io
import struct
import collections


class SocketWrapper:
    def __init__(self, sel, conn, addr, other_sockets):
        self.sel = sel
        self.conn = conn
        self.addr = addr
        self.other_sockets = other_sockets
        self.name = self.addr

        self._recv_buffer = b""
        self._send_buffer = b""
        self._send_queue = collections.deque()
        self._msg_length = None

        self._msg_to_send = None

    def process_events(self, mask):
        if mask & selectors.EVENT_READ:
            self.read()
        if mask & selectors.EVENT_WRITE:
            self.write()

    def write(self):
        if self._msg_to_send:
            msg_bytes = self._json_encode(f">>{self.name}: {self._msg_to_send}", "utf-8")
            msg_to_send = struct.pack(">H", len(msg_bytes)) + msg_bytes
            for sock in self.other_sockets:
                if sock != self:
                    sock._send_queue.append(msg_to_send)
            self._msg_to_send = None
        elif self._send_queue:
            self._send_buffer += self._send_queue.popleft()
        self._write() 

    def _write(self):
        if self._send_buffer:
            try:
                sent = self.conn.send(self._send_buffer)
            except BlockingIOError:
                pass
            else:
                self._send_buffer = self._send_buffer[sent:]

    def read(self):
        self._read()

        if self._msg_length is None:
            self.process_msg_length()
        if self._msg_length:
            self.process_msg()
    
    def process_msg(self):
        if len(self._recv_buffer) < self._msg_length:
            return
        data = self._recv_buffer[:self._msg_length]
        self._recv_buffer = self._recv_buffer[self._msg_length:]
        data = self._json_decode(data, "utf-8")
        
        try_split = data.split()
        if len(try_split) == 2 and try_split[0] == "!username!":
            self.name = try_split[1]
            self._msg_length = None
        else:
            self._msg_to_send = data
            self._msg_length = None
        print(f"Received {data} from {self.addr}")

    def process_msg_length(self):
        hdrlen = 2
        if len(self._recv_buffer) >= hdrlen:
            self._msg_length = struct.unpack(">H", self._recv_buffer[:hdrlen])[0]
            self._recv_buffer = self._recv_buffer[hdrlen:]

    def _read(self):
        try:
            data = self.conn.recv(4096)
        except BlockingIOError:
            pass
        else:
            if data:
                self._recv_buffer += data
            else:
                raise RuntimeError(f"{self.addr} disconnected.")
    
    def close(self):
        print(f"Closing connection to {self.addr}")
        try:
            self.sel.unregister(self.conn)
        except Exception as e:
            print(f"Error: selector.unregister() exception for {self.addr}: {e!r}")

        try:
            self.conn.close()
        except OSError as e:
            print(f"Error: socket.close() exception for {self.addr}: {e!r}")
        finally:
            self.conn = None
    
    def _json_encode(self, obj, encoding):
        return json.dumps(obj, ensure_ascii=False).encode(encoding)

    def _json_decode(self, json_bytes, encoding):
        tiow = io.TextIOWrapper(
            io.BytesIO(json_bytes), encoding=encoding, newline=""
        )
        obj = json.load(tiow)
        tiow.close()
        return obj
        