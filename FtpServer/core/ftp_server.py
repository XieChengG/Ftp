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
    251: 'Invalid cmd',
    252: 'Invalid auth data',
    253: 'Wrong username or password',
    254: 'Passed authentication',
    256: "File doesn't exist on server",
    257: "ready to send file",
    258: "md5 verification"
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

    def _put(self, *args, **kwargs):
        pass

    def _listdir(self, *args, **kwargs):
        res = self.run_cmd("ls -lsh %s" % self.current_dir)
        self.send_response(200, data=res)

    def run_cmd(self, cmd):
        cmd_res = subprocess.getstatusoutput(cmd)
        return cmd_res

    def _change_dir(self, *args, **kwargs):
        if args[0]:
            dest_path = "%s/%s" % (self.current_dir, args[0]['path'])
        else:
            dest_path = self.home_dir
        real_path = os.path.realpath(dest_path)
        if real_path.startswith(self.home_dir):
            if os.path.isdir(real_path):
                self.current_dir = real_path
                current_relative_dir = self.get_relative_path(self.current_dir)
                self.send_response(260, {'current_path': current_relative_dir})
            else:
                self.send_response(259)
        else:
            print("denied to access path", real_path)
            current_relative_dir = self.get_relative_path(self.current_dir)
            self.send_response(260, {'current_path': current_relative_dir})

    def get_relative_path(self, abs_path):
        relative_path = re.sub("^%s" % settings.BASE_DIR, "", abs_path)
        return relative_path

    def _pwd(self, *args, **kwargs):
        current_relative_dir = self.get_relative_path(self.current_dir)
        self.send_response(200, data=current_relative_dir)

    def _get(self, *args, **kwargs):
        data = args[0]
        if data.get('filename') is None:
            self.send_response(255)
        file_abs_path = "%s/%s" % (self.current_dir, data.get('filename'))
        print("file abs path", file_abs_path)

        if os.path.isfile(file_abs_path):
            file_obj = open(file_abs_path, 'rb')
            file_size = os.path.getsize(file_abs_path)
            self.send_response(257, data={'file_size': file_size})
            self.request.recv(1)

            if data.get('md5'):
                md5_obj = hashlib.md5()
                for line in file_obj:
                    self.request.send(line)
                    md5_obj.update(line)
                else:
                    file_obj.close()
                    md5_val = md5_obj.hexdigest()
                    self.send_response(258, data={'md5': md5_val})
                    print("send file done...")
            else:
                for line in file_obj:
                    self.request.send(line)
                else:
                    file_obj.close()
                    print("send file done...")
        else:
            self.send_response(256)


if __name__ == "__main__":
    HOST, PORT = "localhost", 9999
