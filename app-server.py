import sys
import socket
import selectors
import ssl
import traceback

import libserver

sel = selectors.DefaultSelector()
# return a new context with the default security settings
context = ssl.create_default_context()

def accept_wrapper(sock):
    conn, addr = sock.accept() # Ready to read from the socket
    # Return an SSL socket
    conn = context.wrap_socket(conn, server_side=True)
    print(f"Accepted connection from {addr}")
    conn.setblocking(False)#Prevent putting server in hanging state
    message = libserver.Message(sel, conn, addr)
    sel.register(conn, selectors.EVENT_READ, data=message)

if len(sys.argv) != 3:
    print(f'Usage: {sys.argv[0]}, <host> <port>')
    sys.exit(1)

host, port = sys.argv[1], int(sys.argv[2])
lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# Avoid bind() exception: OSError: [Errno 48] Address already in use
lsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
lsock.bind((host, port))
lsock.listen()
print(f'Listening on ({host}, {port})')
lsock.setblocking(False)
sel.register(lsock, selectors.EVENT_READ, data=None)

# A rudimentary event loop
try:
    while True:
        events = sel.select(timeout=None)
        for key, mask in events:
            if key.data is None:
                accept_wrapper(key.fileobj)
            else:
                message = key.data
                try:
                    message.process_events(mask)
                except Exception:
                    print(
                        "main: error: exception for",
                        f"{message.addr}:\n{traceback.format_exc()}"
                    )
                    message.close()
except KeyboardInterrupt:
    print('\nCaught keyboard interrupt, exiting')
finally:
    sel.close()
