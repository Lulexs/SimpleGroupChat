
import json
import io
import struct

class SockWrapper:
    def __init__(self, selector, sock, addr):
        self.selector = selector
        self.sock = sock
        self.addr = addr

        self._recv_buffer = b""
        self._send_buffer = b""
        self._msg_length = None
        self._recv_message = None

    def process_read(self):
        self._read()

        if self._msg_length is None:
            self.process_msg_length()
        if self._msg_length:
            self.process_msg()
            return self._recv_message
    
    def _read(self):
        try:
            data = self.sock.recv(4096)
        except BlockingIOError:
            pass
        else:
            if data:
                self._recv_buffer += data
            else:
                raise RuntimeError(f"Server has crashed.")
    
    def process_msg(self):
        if len(self._recv_buffer) < self._msg_length:
            return
        data = self._recv_buffer[:self._msg_length]
        self._recv_buffer = self._recv_buffer[self._msg_length:]
        data = self._json_decode(data, "utf-8")
    
        self._recv_message = data
        self._msg_length = None

    def process_msg_length(self):
        hdrlen = 2
        if len(self._recv_buffer) >= hdrlen:
            self._msg_length = struct.unpack(">H", self._recv_buffer[:hdrlen])[0]
            self._recv_buffer = self._recv_buffer[hdrlen:]

    def process_write(self, input_data):
        encoded_data = self._json_encode(input_data, "utf-8")
        msg_length = struct.pack(">H", len(encoded_data))
        self._send_buffer = msg_length + encoded_data
        self.sock.sendall(self._send_buffer)

    def _json_encode(self, obj, encoding):
        return json.dumps(obj, ensure_ascii=False).encode(encoding)

    def _json_decode(self, json_bytes, encoding):
        tiow = io.TextIOWrapper(
            io.BytesIO(json_bytes), encoding=encoding, newline=""
        )
        obj = json.load(tiow)
        tiow.close()
        return obj