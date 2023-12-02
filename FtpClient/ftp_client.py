import socket
import os
import json
import optparse


class FtpClient(object):
    def __init__(self):
        self.user = None
        parser = optparse.OptionParser()
        parser.add_option("-s", "--server", dest="server", help="ftp server ip address")
        parser.add_option("-P", "--port", type="int", dest="port", help="ftp server port")
        parser.add_option("-u", "--username", dest="username", help="username")
        parser.add_option("-p", "--password", dest="password", help="password")
        self.options, self.args = parser.parse_args()
        self.verify_args(self.options, self.args)
        self.make_connection()

    def make_connection(self):
        self.sock = socket.socket()
        self.sock.connect((self.options.server, self.options.port))

    def verify_args(self, options, args):
        if options.username is not None and options.password is not None:
            pass
        elif options.username is None and options.password is None:
            pass
        else:
            exit("Err: username and password must be provide together!")

        if options.server and options.port:
            if options.port > 0 and options.port < 65535:
                return True
            else:
                exit("Err: server port must in 0-65535")
        else:
            exit("Error: must supply ftp server address and port, use -h to help")

    def authenticate(self):
        if self.options.username:
            print(self.options.username, self.options.password)
            return self.get_auth_result(self.options.username, self.options.password)
        else:
            retry_count = 0
            while retry_count < 3:
                username = input("username:").strip()
                password = input("password").strip()
                if self.get_auth_result(username, password):
                    return True
                else:
                    retry_count += 1

    def get_auth_result(self, username, password):
        date = {
            "action": "auth",
            "username": username,
            "password": password
        }
        self.sock.send(json.dumps(date).encode())
        response = self.get_response()

        if response.get('status_code') == 254:
            print("passed authentication")
            self.user = username
            return True
        else:
            print(response.get('status_msg'))

    def get_response(self):
        data = self.sock.recv(1024)
        data = json.loads(data.decode())
        return data

    def interactive(self):
        if self.authenticate():
            print("start interactive with user...")
            self.terminal_display = "[%s]$:" % self.user
            while True:
                choice = input(self.terminal_display).strip()
                if len(choice) == 0: continue
                cmd_list = choice.split()
                if hasattr(self, "_%s" % cmd_list[0]):
                    func = getattr(self, "_%s" % cmd_list[0])
                    func(cmd_list)
                else:
                    print("Invalid cmd, type help to get available command")

    def __md5_required(self, cmd_list):
        if "--md5" in cmd_list:
            return True

    def _help(self):
        supported_actions = '''
        get filename    # download file from ftp server
        put filename    # upload file from ftp server
        ls              # list file in the current dir on ftp server
        pwd             # print work dir on ftp server
        cd path         # change directory
        '''
        print(supported_actions)

    def show_progress(self, total):
        received_size = 0
        current_percent = 0
        while received_size < total:
            if int((received_size / total) * 100) > current_percent:
                print("#", end='', flush=True)
                current_percent = int((received_size / total) * 100)
            new_size = yield
            received_size += new_size
