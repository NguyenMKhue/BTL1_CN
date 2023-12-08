import socket
import time
import platform
import os
import pickle
import random
from _thread import *
import schedule
class PeerWorker:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.upload_port_num = 65000 + random.randint(1, 500)
        self.dict_list_of_rfcs = []
        self.s = socket.socket()
        self.load = 0
        self.connect_to_server()

    def connect_to_server(self):
        self.s.connect((self.host, self.port))
        data = pickle.dumps(self.peer_information())
        self.s.send(data)
        server_data = self.s.recv(1024)
        print(server_data.decode('utf-8'))

    def listenServer(self):
        while True:
            try:
                data = pickle.loads(self.s.recv(1024))
                if data == "ping":
                    print("server ping!\n")
                    data = pickle.dumps(["pong",self.load])
                    self.s.send(data)
                elif data[0] == "fetch":
                    found = False
                    for file in self.dict_list_of_rfcs:
                        if file["File Title"]==data[1]:
                            if (data[3]==file["Owner"] or (data[3] in file["Share"])):
                                self.s.send("200".encode())
                                found=True
                    if(found==False):
                        self.s.send("404".encode())

                elif data[0]=="upload":
                    self.p2p_get_request(data[1],data[2],data[3],data[4])
                else:
                    pass
                    
            except KeyboardInterrupt:
                break
            except socket.error:
                break
        self.s.close()

    def peer_information(self):
        try:
            with open('peerIF.pickle', "rb") as f:
                    s = (pickle.load(f))
                    self.upload_port_num = s[1]
                    self.dict_list_of_rfcs = s[0]
                    return s
        except EOFError:
            return [None,self.upload_port_num]
        except Exception as ex:
            print("Error during unpickling object (Possibly unsupported):", ex)


    def transfer_file(self,conn,title):
        filename = f"{title}"
        m = filename.split()
        filename = "".join(m)
        if platform.system() == "Windows":
            filename = "peer_storage\\" + filename
        else:
            filename = "peer_storage/" + filename
        file = open(filename,"rb")
        data = file.read()
        conn.sendall(data)
        conn.send(b"<|:::|>")
        file.close()

#send file in here
    def p2p_listen_thread(self, str, i):
        print("THIS IS MY PORT: ",self.upload_port_num)
        upload_socket = socket.socket()
        host = socket.gethostname()
        upload_socket.bind((host, self.upload_port_num))
        upload_socket.listen(5)
        while True:
            try:
                c, addr = upload_socket.accept()
                data_p2p_undecode = c.recv(1024)
                data_p2p = data_p2p_undecode.decode('utf-8')
                indexP = data_p2p.index('H')
                indexL = data_p2p.index('L')
                file_name = data_p2p[indexL+2:indexP-1]
                print('Got request from:', addr)
                c.send(pickle.dumps(self.p2p_response_message(file_name)))
                self.transfer_file(c,file_name)
                c.close()
            except KeyboardInterrupt:
                break
        upload_socket.close()




    #this is where client receive the files
    def p2p_get_request(self, title, peer_host, peer_upload_port,owner):
        print("this is peer uploadport: ",peer_upload_port)
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
                filename = current_path + "\\peer_storage\\" + filename
            else:
                filename = current_path + "/peer_storage/" + filename
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
        keys = ['File Title', 'Owner']
        entry = [title, owner]
        self.dict_list_of_rfcs.insert(0,dict(zip(keys,entry)))
        s.close()

    def p2p_request_message(self, title):
        OS = platform.platform()
        message = f"GET FILE {title} HCMUT \n"\
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
            filename = "peer_storage\\" + filename
        else:
            filename = "peer_storage/" + filename

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
            message = [f"HCMUT {status} {phrase}\n"\
                       f"Date: {current_time}\n"\
                       f"OS: {OS}\n"\
                       f"Last-Modified: {last_modified}\n"\
                       f"Content-Length: {content_length}\n"\
                       f"Content-Type: {fileType} \n",status]
        return message
    def backup(self):
        print("Peer Backing Up\n")
        with open('peerIF.pickle', 'wb') as f:  # open a text file
            data = [self.dict_list_of_rfcs,self.upload_port_num]
            pickle.dump(data, f) # serialize the list
    def scheduledBackup(self):
        schedule.every(1).minutes.do(self.backup)
        while True:
            schedule.run_pending()
            time.sleep(10)


        

# Usage
worker = PeerWorker("127.0.0.1", 7736)
start_new_thread(worker.p2p_listen_thread, ("hello", 1))
start_new_thread(worker.scheduledBackup,())
worker.listenServer()
