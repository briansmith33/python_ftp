from dotenv import dotenv_values
import socket
import time
import sys

config = dotenv_values('.env')


class FTPClient:
    def __init__(self,
                 host=config['FTP_HOST'],
                 port=21,
                 buffer_size=1024):
        self.host = host
        self.port = port
        self.addr = (host, port)
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.buffer_size = buffer_size

    def connect(self):
        self.client.connect(self.addr)
        greeting = ''
        done = False
        while not done:
            greeting += self.client.recv(self.buffer_size).decode()
            for line in greeting.splitlines():
                if line.startswith('530'):
                    done = True
                    break
        print(greeting)
        username = input(f'User ({self.host}:{self.port}): ')
        self.client.send(b'USER ' + username.encode())
        response = self.client.recv(self.buffer_size).decode().strip()
        print(response)
        if not response.startswith('331'):
            return False
        password = input('Password: ')
        self.client.send(b'PASS '+password.encode())
        response = self.client.recv(self.buffer_size).decode().strip()
        print(response)
        if not response.startswith('230'):
            return False
        return True

    def run(self):
        if self.connect():
            while True:
                command = input('ftp> ')
                if command.lower() == 'quit':
                    self.client.send(b'QUIT')
                    response = self.client.recv(self.buffer_size).decode().strip()
                    print(response)
                    break

                if command.startswith('ls '):
                    self.client.send(b'LIST '+command[len('ls '):].encode()+b'\r\n')
                    transferring = False
                    transfer_start = None
                    size_transferred = 0
                    while True:
                        response = self.client.recv(self.buffer_size).decode().strip()
                        print(response)

                        if response.startswith('125'):
                            transferring = True
                            transfer_start = time.time()
                        if response.startswith('226'):
                            print(str(size_transferred) + ' bytes received in ' + str(time.time() - transfer_start) + ' seconds')
                            break

                        if transferring:
                            size_transferred += sys.getsizeof(response)

                if command.startswith('pwd'):
                    self.client.send(b'PWD \r\n')
                    response = self.client.recv(self.buffer_size).decode().strip()
                    print(response)

        self.client.close()


if __name__ == "__main__":
    FTPClient().run()
