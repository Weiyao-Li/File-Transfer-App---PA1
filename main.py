import sys
import socket
from threading import Thread
import time
from typing import Dict, List, Tuple, Union
import signal
import ipaddress
import argparse

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
        signal.signal(signal.SIGINT, self.sigint_handler)

    def sigint_handler(self, signum, frame):
        self.handle_disconnect(silent=True)
    def handle_disconnect(self, silent: bool = False):
        if not silent:
            message = f"DISCONNECT {self.name}"
            self.udp_socket.sendto(message.encode(), (self.server_ip, self.server_port))

        self.udp_socket.close()
        self.tcp_socket.close()
        sys.exit(0)

    def handle_input(self):
        while True:
            try:
                command = input("Enter command (table/help/disconnect): ").strip().lower()

                if command == "table":
                    self.print_client_table()
                elif command == "help":
                    print("Available commands:")
                    print("  table      - print the client table")
                    print("  help       - show this help message")
                    print("  disconnect - disconnect and notify the server")
                elif command == "disconnect":
                    self.handle_disconnect(silent=False)
                    break
                else:
                    print("Unknown command. Type 'help' for available commands.")
            except KeyboardInterrupt:
                self.handle_disconnect(silent=False)
                break



    def run(self):
        while True:
            try:
                # Check for incoming table updates from the server
                data, addr = self.udp_socket.recvfrom(1024)
                message = data.decode().split(" ", 1)
                if message[0] == "UPDATE":
                    old_table = self.client_table.copy()
                    self.update_client_table(message[1])
                    if old_table != self.client_table:
                        print("\n>>> [Client table updated.]", end="", flush=True)
                        print("\nEnter command (table/help/quit): ", end="", flush=True)
            except OSError:
                break




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
            elif message[0] == "ACK":
                pass  # Do nothing, just acknowledge the receipt of the update

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
            self.broadcast_table()

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
            self.broadcast_table()

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

    def broadcast_table(self):
        table_data = self.serialize_table()
        for name, info in self.client_table.items():
            if info['online']:
                addr = (info['ip'], info['udp_port'])
                self.udp_socket.sendto(f"UPDATE {table_data}".encode(), addr)

    def run(self):
        print(f"Server started on port {self.port}. Waiting for incoming messages...")
        self.listen_udp()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="File Transfer App")
    parser.add_argument("-s", "--server", type=int, help="Start a server at the specified port")
    parser.add_argument("-c", "--client", nargs=5, help="Start a client with: name, server IP, server port, udp port, tcp port")

    args = parser.parse_args()

    if args.server:
        server = FileAppServer(args.server)
        server.run()
    elif args.client:
        name, server_ip, server_port, udp_port, tcp_port = args.client
        client = FileAppClient(name, server_ip, int(server_port), int(udp_port), int(tcp_port))
        client.register()
        client_thread = Thread(target=client.run)
        client_thread.start()
        client.handle_input()
    else:
        print("Invalid usage. Use '-h' or '--help' for help.")
