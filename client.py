import socket
import time
import platform
import os
import pickle
import random
from _thread import *

class Client:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.upload_port_num = 65000 + random.randint(1, 500)
        self.connect_to_server()

    def connect_to_server(self):
        while True:
            self.s = socket.socket()
            self.s.connect((self.host, self.port))
            username = input("Username:")
            password = input("Password:")
            data = pickle.dumps([username,password])
            self.s.send(data)
            server_data = self.s.recv(1024)
            if(server_data.decode('utf-8')!="Failed."):
                self.username=username
                break
            else: self.s.close()
        data = pickle.dumps([self.username,self.upload_port_num])
        self.s.send(data)

    def get_user_input(self):
        user_input = input("> Enter ADD, GET, or EXIT:  ")
        if user_input == "EXIT":
            data = pickle.dumps("EXIT")
            self.s.send(data)
            self.s.close()
        elif user_input == "ADD":
            user_input_file_title = input("> Enter the File Title: ")
            data = pickle.dumps(self.p2s_add_message(user_input_file_title))
            self.s.send(data)
            server_data = self.s.recv(1024)
            print(server_data.decode('utf-8'))
            self.get_user_input()

        elif user_input == "GET":
            user_input_file_title = input("> Enter the File Title: ")
            data = pickle.dumps(self.p2s_lookup_message(user_input_file_title, "0"))
            self.s.send(data)
            server_data = pickle.loads(self.s.recv(1024))
            print("SERVER DATA:", server_data)
            if not server_data[0]:
                print(server_data[1])
            else:
                self.p2p_get_request((user_input_file_title), server_data[0]["Hostname"], server_data[0]["Port Number"])
            self.get_user_input()
        else:
            self.get_user_input()

    def transfer_file(self,conn,title):
        filename = f"{title}"
        m = filename.split()
        filename = "".join(m)
        if platform.system() == "Windows":
            filename = "local_storage\\" + filename
        else:
            filename = "local_storage/" + filename
        file = open(filename,"rb")
        data = file.read()
        conn.sendall(data)
        conn.send(b"<|:::|>")
        file.close()

#send file in here
    def p2p_listen_thread(self, str, i):
        upload_socket = socket.socket()
        host = socket.gethostname()
        upload_socket.bind((host, self.upload_port_num))
        upload_socket.listen(5)
        while True:
            c, addr = upload_socket.accept()
            data_p2p_undecode = c.recv(1024)
            data_p2p = data_p2p_undecode.decode('utf-8')
            indexP = data_p2p.index('H')
            indexL = data_p2p.index('L')
            file_name = data_p2p[indexL+2:indexP-1]
            print(file_name)
            print('Got connection from', addr)
            c.send(pickle.dumps(self.p2p_response_message(file_name)))
            self.transfer_file(c,file_name)
            c.close()

    def p2s_add_message(self, title):
        message = f"ADD File {title} HCMUT \n"\
                  f"Host: {self.host}\n"\
                  f"Port: {self.upload_port_num}\n"
        return [message, title,self.upload_port_num]

    def p2s_lookup_message(self, title, get_or_lookup):
        message = f"LOOKUP File {title} HCMUT_CN \n"\
                  f"Host: {self.host}\n"\
                  f"Port: {self.port}\n"
        return [message, title, get_or_lookup]


    #this is where client receive the files
    def p2p_get_request(self, title, peer_host, peer_upload_port):
        s = socket.socket()
        s.connect((peer_host, int(peer_upload_port)))
        data = self.p2p_request_message(title)
        s.send(bytes(data, 'utf-8'))
        data_rec = pickle.loads(s.recv(1024))
        print("File information:", str(data_rec))
        if(data_rec[1]=="200"):         #recieve the actual file
            current_path = os.getcwd()
            OS = platform.system()
            filename = f"{title}"
            if OS == "Windows":
                filename = current_path + "\\local_storage\\" + filename
            else:
                filename = current_path + "/local_storage/" + filename
            with open(filename, "wb") as file:
                done = False
                file_b = b""
                while not done:
                    data = s.recv(1024)
                    if b"<|:::|>" in data:
                        done=True
                    else:
                        file_b+=data
                file.write(file_b)
                file.close()
        s.close()
 
    def p2p_request_message(self, title):
        OS = platform.platform()
        message = f"GET FILE {title} HCMUT_CN \n"\
                  f"Host: {self.host}\n"\
                  f"OS: {OS}\n"
        return message


#This is where peers send files 
    def p2p_response_message(self, title):
        filename = f"{title}"
        current_time = time.strftime("%a, %d %b %Y %X %Z", time.localtime())
        OS = platform.system()
        m = filename.split()
        filename = "".join(m)
        if OS == "Windows":
            filename = "local_storage\\" + filename
        else:
            filename = "local_storage/" + filename

        if not os.path.exists(filename):
            status = "404"
            phrase = "Not Found"
            message = [f"HCMUT_CN {status} {phrase}\n"\
                      f"Date: {current_time}\n"\
                      f"OS: {OS}\n",status]
        else:
            status = "200"
            phrase = "OK"
            fileType = os.path.splitext(filename)
            last_modified = time.ctime(os.path.getmtime(filename))
            content_length = os.path.getsize(filename)
            message = [f"HCMUT_CN {status} {phrase}\n"\
                       f"Date: {current_time}\n"\
                       f"OS: {OS}\n"\
                       f"Last-Modified: {last_modified}\n"\
                       f"Content-Length: {content_length}\n"\
                       f"Content-Type: {fileType} \n",status]
        return message


        

# Usage
client = Client("127.0.0.1", 7737)
start_new_thread(client.p2p_listen_thread, ("hello", 1))

client.get_user_input()
