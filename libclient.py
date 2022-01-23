from libserver import Message

class Message2(Message):
    def __init__(self, selector, sock, addr, request) -> None:
        super().__init__(selector, sock, addr)
        self.request = request
        self._request_queued = False
        self.response = None

    def _process_response_html_content(self):
        content = self.response
        # result = content.get('result')
        print(f'Got response: {repr(content)}')

    def _process_response_binary_content(self):
        content = self.response
        print(f"Got response: {repr(content)}")

    def _write(self) -> None:
        if self._send_buffer:
            print(f"Sending {repr(self._send_buffer)} to {self.addr}\n")
            try:
                sent = self.sock.send(self._send_buffer)
            except BlockingIOError:
                pass
            else:
                self._send_buffer = self._send_buffer[sent:]

    def read(self) -> None:
        super()._read()
        if self._jsonheader_len is None:
            super().process_protoheader()

        if self._jsonheader_len is not None:
            if self.jsonheader is None:
                super().process_header()

        if self.jsonheader:
            if self.response is None:
                self.process_response()

    def write(self) -> None:
        if not self._request_queued:
            self.queue_request()
        self._write()

        if self._request_queued:
            if not self._send_buffer:
                super()._set_selector_events_mask('r')

    def queue_request(self) -> None:
        print("Queuing request...\n")
        content = self.request['content']
        content_type = self.request['type']
        content_encoding = self.request['encoding']
        if content_type == 'text/html':
            req = {
                'content_bytes': super()._json_encode(content, content_encoding),
                'content_type': content_type,
                'content_encoding': content_encoding
            }

        else:
            req = {
                'content_bytes': content,
                'content_type': content_type,
                'content_encoding': content_encoding
            }
        message = super()._create_message(**req)
        self._send_buffer += message
        self._request_queued = True

    def process_response(self) -> None:
        print('Processing response...\n')
        content_len = self.jsonheader['content-length']
        if not len(self._recv_buffer) >= content_len:
            return
        data = self._recv_buffer[:content_len]
        self._recv_buffer = self._recv_buffer[content_len:]
        if self.jsonheader['content-type'] == 'text/html':
            encoding = self.jsonheader['content-encoding']
            self.response = super()._json_decode(data, encoding)
            print(f"Received response {repr(self.response)} from {self.addr}")
            self._process_response_html_content()

        else:
            self.response = data
            print(f"Received {self.jsonheader['content-type']} response from {self.addr}")
            self._process_response_binary_content()

        super().close()