import sys
import socket
import threading
import time
from typing import Dict, List, Tuple, Union
import signal
import ipaddress

# this is client side

'''
UDP client process:
create socket(socket()) -> bind to port(bind()) -> send data(sendto()) -> receive reply(recvfrom()) -> client exit(close())
'''

class FileAppClient:
    def __init__(self, name, server_ip, server_port, client_udp_port, client_tcp_port):
        self.name = name
        self.server_ip = server_ip
        self.server_port = server_port
        self.client_udp_port = client_udp_port
        self.client_tcp_port = client_tcp_port

        # create UDP and TCP socket for client
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # bind socket(ip) to a port
        self.udp_socket.bind(('', client_udp_port))

        # create client local table
        self.client_table = {}

    def register(self):
        # create registration msg
        message = f"REGISTER {self.name} {socket.gethostbyname(socket.gethostname())} {self.client_udp_port} {self.client_tcp_port}"

        # encode the msg and send to server
        self.udp_socket.sendto(message.encode(), (self.server_ip, self.server_port))

        # deal with server response
        data, addr = self.udp_socket.recvfrom(1024)
        response = data.decode().split(" ", 1)

        if response[0] == "WELCOME":
            print(">>> [Welcome, You are registered.]")
            self.update_client_table(response[1])
        else:
            print(">>> [Error: Registration failed.]")
            sys.exit(1)

    def print_client_table(self):
        print("\nClient Table:")
        for name, info in self.client_table.items():
            print(f"{name}: {info}")
        print("\n")

    def update_client_table(self, table_data):
        # Deserialize the table_data and update self.client_table
        # After updating, send an ACK message to the server
        self.client_table = self.deserialize_table(table_data)
        self.udp_socket.sendto("ACK".encode(), (self.server_ip, self.server_port))
        print(">>> [Client table updated.]")

    def deserialize_table(self, table_data: str) -> Dict[str, Dict[str, Union[str, int, List[str], bool]]]:
        table = {}
        for row in table_data.strip().split('\n'):
            name, ip, udp_port, tcp_port, *files = row.split(' ')
            table[name] = {
                "ip": ip,
                "udp_port": int(udp_port),
                "tcp_port": int(tcp_port),
                "files": files,
                "online": self.client_table.get(name, {}).get("online", True)
            }
        return table

    def listen_for_disconnect(self):
        signal.signal(signal.SIGINT, self.handle_disconnect)

    def handle_disconnect(self, signum, frame):
        message = f"DISCONNECT {self.name}"
        self.udp_socket.sendto(message.encode(), (self.server_ip, self.server_port))
        self.udp_socket.close()
        self.tcp_socket.close()
        sys.exit(0)

    def run(self):
        while True:
            command = input("Enter command (table/help/quit): ").strip().lower()

            if command == "table":
                self.print_client_table()
            elif command == "help":
                print("Available commands:")
                print("  table - print the client table")
                print("  help  - show this help message")
                print("  quit  - disconnect and exit")
            elif command == "quit":
                self.handle_disconnect(None, None)
                break
            else:
                print("Unknown command. Type 'help' for available commands.")

# -----------------------
# this is server side

'''
UDP server process:
create socket(socket()) -> bind to port(bind()) -> receive data(recvfrom()) -> send reply(sendto()) -> server exit(close())
'''

class FileAppServer:
    def __init__(self, port):
        self.port = port
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.bind(('', port))

        # key: client names, values: client info (ip, udp_port, tcp_port...)
        self.client_table = {}

    # listening for incoming UDP msg
    def listen_udp(self):
        while True:
            data, addr = self.udp_socket.recvfrom(1024)
            message = data.decode().split(" ")
            if message[0] == "REGISTER":
                self.handle_registration(message[1:], addr)
                self.print_client_table()
            elif message[0] == "DISCONNECT":
                self.handle_disconnect(message[1:])
                self.print_client_table()

    def handle_registration(self, message, addr):
        name, ip, udp_port, tcp_port = message
        if name in self.client_table:
            self.udp_socket.sendto("ERROR".encode(), addr)
        else:
            self.client_table[name] = {
                "ip": ip,
                "udp_port": int(udp_port),
                "tcp_port": int(tcp_port),
                "files": [],
                "online": True
            }
            table_data = self.serialize_table()
            self.udp_socket.sendto(f"WELCOME {table_data}".encode(), addr)

    def serialize_table(self) -> str:
        rows = []
        for name, info in self.client_table.items():
            row = f"{name} {info['ip']} {info['udp_port']} {info['tcp_port']} {' '.join(info['files'])}"
            rows.append(row)
        return '\n'.join(rows)

    def handle_disconnect(self, message):
        name = message[0]
        if name in self.client_table:
            self.client_table[name]["online"] = False

    @staticmethod
    def is_valid_ip(ip: str) -> bool:
        try:
            ipaddress.IPv4Address(ip)
            return True
        except ipaddress.AddressValueError:
            return False

    @staticmethod
    def is_valid_port(port: int) -> bool:
        return 1024 <= port <= 65535

    def print_client_table(self):
        print("\nClient Table:")
        for name, info in self.client_table.items():
            print(f"{name}: {info}")
        print("\n")


if __name__ == "__main__":
    args = sys.argv
    if len(args) < 2:
        print("Usage: FileApp -c|-s ...")
        sys.exit(1)

    mode = args[1]
    if mode == "-s":
        if len(args) != 3:
            print("Usage: FileApp -s <port>")
            sys.exit(1)

        server_port = int(args[2])
        if not FileAppServer.is_valid_port(server_port):
            print("Invalid server port. Port must be in the range 1024-65535.")
            sys.exit(1)

        server = FileAppServer(server_port)
        print(f"Server started on port {server_port}. Waiting for incoming messages...")
        server.listen_udp()


    elif mode == "-c":

        if len(args) != 7:
            print("Usage: FileApp -c <name> <server-ip> <server-port> <client-udp-port> <client-tcp-port> [-t]")
            sys.exit(1)

        client_name, server_ip, server_port, client_udp_port, client_tcp_port = args[2:7]

        if not FileAppServer.is_valid_ip(server_ip):
            print("Invalid server IP address. Must be in decimal format.")
            sys.exit(1)

        server_port, client_udp_port, client_tcp_port = map(int, [server_port, client_udp_port, client_tcp_port])
        if not all(map(FileAppServer.is_valid_port, [server_port, client_udp_port, client_tcp_port])):
            print("Invalid port number(s). Port must be in the range 1024-65535.")
            sys.exit(1)

        client = FileAppClient(client_name, server_ip, server_port, client_udp_port, client_tcp_port)
        client.register()
        client.listen_for_disconnect()
        client.run()

    else:
        print("Invalid mode. Use -s for server or -c for client.")
        sys.exit(1)
