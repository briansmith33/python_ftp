from dotenv import dotenv_values
from threading import Thread
import sqlite3
import socket
import os


config = dotenv_values('.env')


class FTPServer:
    def __init__(self,
                 host=config['FTP_HOST'],
                 port=21,
                 root='./shared',
                 allows_anonymous=True,
                 buffer_size=1024):
        self.host = host
        self.port = port
        self.addr = (host, port)
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.root = root
        self.cwd = root
        self.allows_anonymous = allows_anonymous
        self.buffer_size = buffer_size

    def get_username(self, conn):
        while True:
            username = conn.recv(self.buffer_size).decode().strip()
            if username.upper().startswith('USER'):
                username = username[len('USER '):]
                print(username)

                if username == 'anonymous' and self.allows_anonymous:
                    conn.send(b'331 Guest login ok, leave password blank.\r\n')
                    break
                else:
                    db = sqlite3.connect("ftp.db")
                    cursor = db.cursor()
                    cursor.execute(f"SELECT * FROM users WHERE username=?", username)
                    user = cursor.fetchone()
                    db.close()
                    if user:
                        conn.send(b'331 User name ok, need password.\r\n')
                        break
            conn.send(b'430 Invalid username\r\n')

        return username

    def authenticate(self, conn, user):
        while True:
            password = conn.recv(self.buffer_size).decode().strip()
            if password.upper().startswith('PASS'):
                password = password[len('PASS '):]
                if password == 'QUIT':
                    return False
                if user == 'anonymous':
                    conn.send(b'230 Anonymous login ok, access restrictions apply\r\n')
                    return True
                else:
                    db = sqlite3.connect("ftp.db")
                    cursor = db.cursor()
                    cursor.execute(f"SELECT * FROM users WHERE username=?", user)
                    user = cursor.fetchone()
                    db.close()
                    if user['password'] == password:
                        conn.send(b'230 User logged in\r\n')
                        return True
            conn.send(b'430 Invalid password\r\n')

    def accept_connection(self, conn, addr):
        conn.send(b'Connected to '+self.host.encode()+b'\r\n')
        conn.send(b'220 Nexus FTP Server\r\n')
        conn.send(b'530 Please login with USER and PASS\r\n')
        username = self.get_username(conn)
        if self.authenticate(conn, username):
            while True:
                command = conn.recv(self.buffer_size).decode().strip()
                if command.upper().startswith('QUIT'):
                    conn.send(b'231 User logged out, service terminated')
                    break

                if command.upper().startswith('LIST'):
                    directory = self.root+'/'+command[len('LIST '):]
                    conn.send(b'200 PORT OK\r\n')
                    conn.send(b'125 Data connection already open, starting transfer\r\n')
                    if os.path.exists(directory):
                        if directory.lower().startswith('c:'):
                            if self.root.startswith('.'):
                                full_path = os.getcwd()+self.root[1:]
                            else:
                                full_path = self.root
                            if full_path in directory:
                                conn.send('\n'.join(os.listdir(directory)).encode())
                            else:
                                conn.send(b'550 No such file or directory\r\n')
                    else:
                        conn.send(b'550 No such file or directory\r\n')
                    conn.send(b'226 Transfer complete\r\n')

                if command.upper().startswith('PWD'):
                    conn.send(b'200 '+self.cwd.encode()+b'\r\n')

        conn.close()

    def run(self):
        self.server.bind(self.addr)
        self.server.listen(2)
        while True:
            try:
                conn, addr = self.server.accept()
                Thread(target=self.accept_connection, args=(conn, addr)).start()
            except KeyboardInterrupt:
                break


if __name__ == '__main__':
    server = FTPServer()
    server.run()
