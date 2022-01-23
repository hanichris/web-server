import sys
import selectors
import json
import io
import struct
from typing import Any



class Message:
    """
    This class provides a way of managing the state.
    """
    def __init__(self, selector, sock, addr) -> None:
        self.selector = selector
        self.sock = sock
        self.addr = addr
        self._recv_buffer = b""
        self._send_buffer = b""
        self._jsonheader_len = None
        self.jsonheader = None
        self.request = None
        self.response_created = False
    
    def _set_selector_events_mask(self, mode) -> None:
        if mode == 'r':
            events = selectors.EVENT_READ
        elif mode == 'w':
            events = selectors.EVENT_WRITE
        elif mode == 'rw':
            events = selectors.EVENT_READ | selectors.EVENT_WRITE
        else:
            raise ValueError(f'Invalid events mask mode {repr(mode)}.')
        self.selector.modify(self.sock, events, data=self)

    def _read(self) -> None:
        """
        Reads data from the socket and stores it in a receive buffer.
        """
        try:
            data = self.sock.recv(4096)
        except BlockingIOError:
            pass
        else:
            if data:
                self._recv_buffer += data
            else:
                raise RuntimeError("Peer closed")

    def _write(self) -> None:
        if self._send_buffer:
            print(f"Sending {repr(self._send_buffer)} to {self.addr}")
            try:
                sent = self.sock.send(self._send_buffer)
            except BlockingIOError:
                pass
            else:
                self._send_buffer = self._send_buffer[sent:]
                if sent and not self._send_buffer:
                    self.close()

    def _json_encode(self, obj, encoding) -> bytes:
        return json.dumps(obj, ensure_ascii=False).encode(encoding)

    def _json_decode(self, json_bytes, encoding) -> object:
        tiow = io.TextIOWrapper(
            io.BytesIO(json_bytes), encoding=encoding, newline=''
        )
        obj = json.load(tiow)
        tiow.close()
        return obj

    def _create_message(
        self, *, content_bytes, content_type, content_encoding
    ) -> bytes:
        """
        Builds the message to be sent component-wise. Includes the 
        fixed-length header, variable-length JSON header and the contents
        of the message itself.
        """
        header = {
            'byteorder': sys.byteorder,
            'content-encoding': content_encoding,
            'content-length': len(content_bytes), 
            'content-type': content_type,
        }
        header_bytes = self._json_encode(header, 'utf-8')
        message_hdr = struct.pack('>H',len(header_bytes))
        message = message_hdr + header_bytes + content_bytes
        return message

    def _create_response_html_content(self) -> object:
        """
        Creates a HTML response based on either GEt or POST requests.
        """
        action = self.request.get('action')
        if action == 'GET':
            try:
                query = self.request.get('value')
                with open(query, encoding='utf-8') as f:
                    html_content = f.read()
                content = 'HTTP/1.0 200 OK' + html_content
            except FileNotFoundError:
                content = 'HTTP/1.0 404 NOT FOUND\n\nFILE NOT FOUND'
        elif action == 'POST':
            content = 'HTTP/1.0 200 OK'
        content_encoding = 'utf-8'
        response = {
            'content_bytes': self._json_encode(content, content_encoding),
            'content_type': 'text/html',
            'content_encoding': content_encoding,
        }
        return response

    def process_events(self, mask) -> None:
        if mask & selectors.EVENT_READ:
            self.read()
        if mask & selectors.EVENT_WRITE:
            self.write()

    def read(self) -> None:
        """
        Reads in data from the socket and calls the appropriate methods
        to process it depending on some state checks.
        """
        self._read()

        if self._jsonheader_len is None:
            self.process_protoheader()
        if self._jsonheader_len is not None:
            if self.jsonheader is None:
                self.process_header()
        if self.jsonheader:
            if self.request is None:
                self.process_request()

    def write(self) -> None:
        """
        Writes the response data to a send buffer if a request has been
        made.
        """
        if self.request:
            if not self.response_created:
                self.create_response()
        
        self._write()

    def close(self) -> None:
        print(f"Closing connection to {self.addr}")
        try:
            self.selector.unregister(self.sock)
        except Exception as e:
            print(f"error: selector.unregister() exception for {self.addr}: {repr(e)}")
        try:
            self.sock.close()
        except OSError as e:
            print(f"error: socket.close() exception for {self.addr}: {repr(e)}")
        finally:
            self.sock = None

    def process_protoheader(self) -> None:
        print('Processing protoheader...\n')
        hdrlen = 2
        if len(self._recv_buffer) >= hdrlen:
            self._jsonheader_len = struct.unpack(
                '>H', self._recv_buffer[:hdrlen]
            )[0]
            self._recv_buffer = self._recv_buffer[hdrlen:]

    def process_header(self) -> None:
        print('Processing header...\n')
        hdrlen = self._jsonheader_len
        if len(self._recv_buffer) >= hdrlen:
            self.jsonheader = self._json_decode(
                self._recv_buffer[:hdrlen], 'utf-8'
            )
            self._recv_buffer = self._recv_buffer[hdrlen:]
            for reqhdr in (
                'byteorder',
                'content-length',
                'content-type',
                'content-encoding',
            ):
                if reqhdr not in self.jsonheader:
                    raise ValueError(f'Missing required header "{reqhdr}".')

    def process_request(self):
        print('Processing request...\n')
        content_len = self.jsonheader['content-length']
        if not len(self._recv_buffer) >= content_len:
            return

        data = self._recv_buffer[:content_len]
        self._recv_buffer = self._recv_buffer[content_len:]
        if self.jsonheader['content-type'] == 'text/html':
            encoding = self.jsonheader['content-encoding']
            self.request = self._json_decode(data, encoding)
            print(f'Received request {repr(self.request)} from {self.addr}')
        else:
            self.request = data
            print(f"Received {self.jsonheader['content-type']} request from {self.addr}")
        self._set_selector_events_mask("w")
        
    def create_response(self):
        print('Generating response...\n')
        if self.jsonheader['content-type'] == 'text/html':
            response = self._create_response_html_content()
        message = self._create_message(**response)
        self.response_created = True
        self._send_buffer += message
    