import sys
import socket
import selectors
import ssl
import traceback

import libclient

sel = selectors.DefaultSelector()
context = ssl.create_default_context()

def create_request(action, value) -> dict:
    if action == 'GET':
        return dict(type='text/html',
        encoding = 'utf-8',
        content = dict(action=action, value=value))

    elif action == 'POST':
        return dict(type='text/html',
        encoding = 'utf-8',
        content = dict(action=action, value=value))

def start_connection(host, port, request) -> None:
    addr = (host, port)
    print(f'starting connection to {addr}')
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock = context.wrap_socket(sock, server_hostname=host)
    sock.setblocking(False)
    sock.connect_ex(addr)
    events = selectors.EVENT_READ | selectors.EVENT_WRITE
    message = libclient.Message2(sel, sock, addr, request)
    sel.register(sock, events, data=message)

if len(sys.argv) != 5:
    print(f'usage: {sys.argv[0]} <host> <port> <action> <value>')
    sys.exit(1)

host, port = sys.argv[1], int(sys.argv[2])
action, value = sys.argv[3], sys.argv[4]
request = create_request(action, value)
start_connection(host, port, request)

try:
    while True:
        events = sel.select(timeout=1)
        for key, mask in events:
            message = key.data
            try:
                message.process_events(mask)
            except Exception:
                print(
                    f"main error: exception for {message.addr}\n{traceback.format_exc()}"
                )
                message.close()
        if not sel.get_map():
            break
except KeyboardInterrupt:
    print('\nCaught keyboard interrupt, exiting')
finally:
    sel.close()