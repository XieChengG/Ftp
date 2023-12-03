import socketserver
import json
import hashlib
import subprocess
import os, re
import configparser
from FtpServer.conf import settings

STATUS_CODE = {
    200: 'Task finished',
    250: 'Invalid cmd format',
    251: 'Invalid cmd'
}


class FtpHandler(socketserver.BaseRequestHandler):
    def handle(self):
        while True:
            self.data = self.request.recv(1024).strip()
            print(self.client_address[0])
            print(self.data)
            if not self.data:
                print("client closed")
                break
            data = json.loads(self.data.decode())
            action = data.get('action')
            if action is not None:
                if hasattr(self, "_%s" % action):
                    func = getattr(self, "_%s" % action)
                    func(data)
                else:
                    print("Invalid cmd")
                    self.send_response(251)
            else:
                print("Invalid cmd format")
                self.send_response(250)

    def send_response(self, status_code, data=None):
        response = {
            'status_code': status_code,
            'status_msg': STATUS_CODE[status_code],
        }
        if data:
            response.update({'data': data})
        self.request.send(json.dumps(response).encode())

    def _auth(self, *args, **kwargs):
        data = args[0]
        if data.get('username') is None or data.get('password') is None:
            self.send_response(252)
        user = self.authenticate(data.get('username'), data.get('password'))
        if user is None:
            self.send_response(253)
        else:
            print("passed authentication", user)
            self.home_dir = "%s/home/%s" % (settings.BASE_DIR, data.get('username'))
            self.current_dir = self.home_dir
            self.send_response(254)

    def authenticate(self, username, password):
        config = configparser.ConfigParser()
        config.read(settings.ACCOUNT_FILE)
        if username in config.sections():
            _password = config[username]['Password']
            if _password == password:
                print("pass auth..", username)
                config[username]['Username'] = username
                return config[username]
