import socket
from _thread import *
import pickle
import time
import platform
import traceback

class P2PServer:
    def __init__(self, host, port,peer_port):
        self.s = socket.socket()
        self.host = host
        self.port = port
        self.users = [{'name': 'khueminh','pw':'password'}]
        self.peer_list = []
        self.combined_list = []
        self.peerS = socket.socket()
        self.peerPort = peer_port
        print("firststep")
    def start_Client(self):
        print("second")
        self.s.bind((self.host, self.port))
        self.s.listen(5)
        print(f"Listening Clients onnn {self.host}:{self.port}")
        while True:
            c, addr = self.s.accept()
            data = pickle.loads(c.recv(1024))
            if(self.authenticate(data[0],data[1])):
                start_new_thread(self.client_thread, (c, addr))
            else:
                c.send("Failed.".encode())
                c.close()
    def authenticate(self,name,pw):
        for user in self.users:
            if user["pw"] == pw and user["name"]==name:
                return True
        return False

    def start_Cluster(self):
        self.peerS.bind((self.host, self.peerPort))
        self.peerS.listen(5)
        print(f"Listening Peers on {self.host}:{self.peerPort}")
        while True:
            c, addr = self.peerS.accept()
            start_new_thread(self.peer_thread, (c, addr))
    
    def peer_thread(self,conn,addr):
        conn.send(bytes('Connected to Cluster Storage', 'utf-8'))
        print('Got connection from Peer: ', addr)
        data = pickle.loads(conn.recv(1024))
        self.append_peer_list(self.peer_list,addr[0],addr[1],conn,data[1])
        if(data[0]):
            self.create_combined_list(self.combined_list,data[0],addr[0],data[1])

    def response_message(self, status):
        if status == "200":
            phrase = "OK"
        elif status == "404":
            phrase = "Not Found"
        elif status == "400":
            phrase = "Bad Request"
        message = f"HCMUT_CN {status} {phrase}\n"
        return message

    def client_thread(self, conn, addr):
        conn.send(bytes('Connected to Server - Drive Storage HCMUT', 'utf-8'))
        print('Got connection from Client: ', addr)
        data = pickle.loads(conn.recv(1024))
        my_port = data[1]
        print("Client's receive port:",my_port)
        username = data[0]
        while True:
            try:
                data = pickle.loads(conn.recv(1024))
                if data == "EXIT":
                    break
                elif type(data) == str:
                    print("Listing")
                    self.p2s_list_response(conn)
                    new_data = pickle.dumps(self.return_dict())
                    conn.send(new_data)
                else:
                    if data[0][0] == "A":
                        print("Someone wants to add")
                        success = self.handleADD(data[1], addr[0], my_port,username)
                        if not success:
                            print("not success")
                            conn.send(bytes("Cannot upload at the moment, please try again later.\n",'utf-8'))
                        else:
                            print("success")
                            self.p2s_add_response(conn, data[1], addr[0], addr[1])

                    elif data[2] == "0":
                        res = self.handleFetch(data[1],addr[0],username)
                        if(res!=False):
                            new_data = pickle.dumps([res,"200"])
                            conn.send(new_data)
                        else:
                            new_data = pickle.dumps([None,"404"])
                            conn.send(new_data)
            except KeyboardInterrupt: 
                break
            except socket.error:
                break
        print("Closing connection!")
        conn.close()


    def ping(self,conn):
        try:
            conn.send(pickle.dumps("ping"))
            response = pickle.loads(conn.recv(1024))
            if response[0] == "pong":
                return [True,response[1]]
            else:
                print("pingfailed")
                return False
        except (socket.error, ConnectionError):
            return "Ping failed."


    def handleADD(self,title,host,up_port,owner):
        load=-1
        chosenPeer = None
        for peer in self.peer_list:
            res = self.ping(peer['Connection'])
            print(res)
            if(res[0]!=False):
                peerload = res[1]
                print(peerload)
                if peerload>=0 or peerload<load:
                    load=peerload 
                    chosenPeer = peer
        if(chosenPeer):
            sendData = pickle.dumps(["upload",title,host,up_port,owner])
            chosenPeer["Connection"].send(sendData)
            self.append_to_combined_list(self.combined_list,title,chosenPeer["Hostname"],chosenPeer["Upload Port"])
            return True
        else:
            return False

    def handleFetch(self,title,host,username):
        for inf in self.combined_list:
            if inf["File Title"]==title:
                for peer in self.peer_list:
                    if peer["Hostname"]==inf["Hostname"]:
                        res = self.ping(peer['Connection'])
                        if(res[0]!=False):
                            peer["Connection"].send(pickle.dumps(["fetch",title,host,username]))
                            data = peer["Connection"].recv(1024).decode('utf-8')
                            if(data=="200"):
                                return inf
        return False

        

    def p2s_lookup_response(self, title):
        current_time = time.strftime("%a, %d %b %Y %X %Z", time.localtime())
        OS = platform.platform()
        response = self.search_combined_dict(title)
        if not response:
            status = "404"
            phrase = "Not Found"
            message = f"P2P-CI1111/1.0 {status} {phrase}\n"\
                      f"Date: {current_time}\n"\
                      f"OS: {str(OS)}\n"
            return response, message
        else:
            status = "200"
            phrase = "OK"
            message = f"P2P-CI11111/1.0 {status} {phrase}\n"
            return response, message



    def p2s_add_response(self, conn, title, hostname, port):
        response = f"200 OK \nFile Title: {title} || {str(hostname)} {str(port)}"
        conn.send(bytes(response, 'utf-8'))

    def p2s_list_response(self, conn):
        message = self.response_message("200")
        print(message)
        conn.send(str(message).encode())

    def send_file(self, filename):
        txt = open(filename)
        data = txt.read(1024)
        while data:
            self.s.send(data)
            data = txt.read(1024)
        self.s.close()


    def create_combined_list(self, dictionary_list, dict_list_of_files, hostname, port):
        keys = ['File Title', 'Hostname', 'Port Number']

        for file in dict_list_of_files:
            title = file['File Title']
            entry = [title, hostname, str(port)]
            dictionary_list.insert(0, dict(zip(keys, entry)))

        return dictionary_list, keys

    def append_peer_list(self, dictionary_list, hostname, port,conn,up):
        keys = ['Hostname', 'Port Number','Connection','Upload Port']

        entry = [hostname, str(port),conn,up]
        dictionary_list.insert(0, dict(zip(keys, entry)))
        return dictionary_list, keys


    def append_to_combined_list(self, dictionary_list, title, hostname, port):
        keys = ['File Title', 'Hostname', 'Port Number']
        entry = [title, hostname, str(port)]

        dictionary_list.insert(0, dict(zip(keys, entry)))
        return dictionary_list

    def print_dictionary(self, dictionary_list, keys):
        for item in dictionary_list:
            print(' '.join([item[key] for key in keys]))

    def delete_peers_dictionary(self, dict_list_of_peers, hostname):
        dict_list_of_peers[:] = [d for d in dict_list_of_peers if d.get('Hostname') != hostname]
        return dict_list_of_peers

    def delete_files_dictionary(self, dict_list_of_files, hostname):
        dict_list_of_files[:] = [d for d in dict_list_of_files if d.get('Hostname') != hostname]
        return dict_list_of_files

    def delete_combined_dictionary(self, combined_dict, hostname):
        combined_dict[:] = [d for d in combined_dict if d.get('Hostname') != hostname]
        return combined_dict

    def search_combined_dict(self, title):
        for d in self.combined_list:
            if d['File Title'] == title:
                return d
        return False

    def search_combined_dict2(self, title):
        my_list = []
        for d in self.combined_list:
            if d['File Title'] == title:
                my_list.append(d)
        return my_list

    def return_dict(self):
        keys = ['File Title', 'Hostname', 'Port Number']
        return self.combined_list, keys


if __name__ == "__main__":
    host = socket.gethostbyname(socket.gethostname())
    client_port = 7737
    peer_port = 7736
    loginPort = 7735
    server = P2PServer(host, client_port,peer_port)
    start_new_thread(server.start_Client,())
    start_new_thread(server.start_Cluster,())
    while True:
        pass
