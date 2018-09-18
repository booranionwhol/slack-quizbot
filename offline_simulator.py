import socket
import time
from threading import Thread


SOCKET_LISTEN_PORT = 1234


class FakeServer:
    """
    Junk class just to set the sc.server.connected property
    """

    def __init__(self):
        self.connected = False


class SocketServer:
    def __init__(self):
        """
        SlackClient sets a property available on object.server.connected
        We need to set this to True when our simulator is connected
        The main game loop waits for sc.server.connected to be True before starting the quiz.

        Create an instance inside this class called "server" just so we can set the nested property
        """

        self.server = FakeServer()
        self.SOCKET = None

    def api_call(self, *args, **kwargs):
        print('api_call: {} {}'.format(args,kwargs))

    def rtm_read(self):
        """
        Main game loop uses sc.rtm_read() to get messages from the WebSocket
        Normally multiple messages are in a list, so fake this. 
        If nothing has been sent over the socket, return an empty list
        """

        try:
            # The simulator client may not send anything. Return a blank list if so.
            self.socket_client.settimeout(0.0)
            data = self.socket_client.recv(2048)
            output = []
            for line in data.splitlines():
                string = bytes.decode(line)
                # Format of the message on the socket should be user:msg
                user, msg = string.split(':')
                slack_message = {
                    'type': 'message',
                    'text': msg,
                    'ts': time.time(),
                    'channel': 'C123456',
                    'user': user
                }
                output.append(slack_message)
        except:
            output = []
        return output

    def accept_socket_incoming(self, SOCKET):
        # accept() is blocking, and will wait for incoming connection.
        print('Fake slack server listening on port {}. Telnet and send messages..'.format(
            SOCKET_LISTEN_PORT))
        client, client_address = SOCKET.accept()
        client.send(b'Hello! Send messages with <userid>:<msg>\r\n')
        self.socket_client = client
        self.server.connected = True

    def rtm_connect(self, **kwargs):
        """ rtm_connect is invoked early in the SlackClient connection.
        To open a websocket and negioate a RTM session with Slack
        Don't do much in this simulation, but open a local socket"""

        SOCKET = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # SOCKET.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        SOCKET.bind(('0.0.0.0', SOCKET_LISTEN_PORT))
        SOCKET.listen(1)
        self.SOCKET = SOCKET
        self.accept_socket_incoming(SOCKET)
        return 'socket opened'
