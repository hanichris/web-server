# Web Server
## Overview
This project serves as an implementation of a simple HTTP web server built using Python that can listen on a configurable TCP port and serve static HTML pages.
The server supports only the GET and POST subset of HTTP requests as well as Byteorder, Content-Encoding, Content-Type and Content-Length headers.
Using HTTP as the base protocol, the server was extended to implement HTTPS as a security measure.
The server supports multiple connections at a time and remains online after serving a client its request.

The server was built using the socket and ssl modules provided in the Python packages.

The libclient.py and libserver.py provide an abstraction to facilitate building the message that is sent between the client and server.

## Run
To start the server and listen on the loopback interface on port 65432, run the following command in a terminal
```bash
python3 app-server.py 127.0.0.1 65432
```
To simulate a client making a GET request to the server for the index.html file, run the following command in a terminal
```bash
python3 app-client.py 127.0.0.1 65432 GET index.html
```
The format employed is captured below.
```bash
Usage: python3 app-client.py <host> <port> <action> <value>
```

## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.


## License
[MIT](https://choosealicense.com/licenses/mit/)
