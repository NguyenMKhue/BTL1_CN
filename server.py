import socket
from _thread import *
import pickle
import time
import platform
from threading import Lock
import traceback

class Server:
    def __init__(self, host, port,peer_port):
        self.peer_list_lock = Lock()
        self.file_list_lock = Lock()
        self.s = socket.socket()
        self.host = host
        self.port = port
        self.users = [{'name': '1','pw':'1'},{'name':'2','pw':'2'}]
        self.peer_list = []
        self.combined_list = []
        self.peerS = socket.socket()
        self.peerPort = peer_port
        print("\n>>>>>HCMUT DRIVE - Centralized Server<<<<<\n")
        try:
            with open('serverIF.pickle', "rb") as f:
                    s = (pickle.load(f))
                    if s:
                        self.combined_list = s
        except:
            pass
    def start_Client(self):
        self.s.bind((self.host, self.port))
        self.s.listen(5)
        print(f">>>>>Listening Clients on {self.host}:{self.port}")
        while True:
            c, addr = self.s.accept()
            start_new_thread(self.client_thread, (c, addr))
    def authenticate(self,name,pw):
        for user in self.users:
            if user["pw"] == pw and user["name"]==name:
                return True
        return False

    def start_Cluster(self):
        self.peerS.bind((self.host, self.peerPort))
        self.peerS.listen(5)
        print(f">>>>>>Listening Peers on {self.host}:{self.peerPort}")
        while True:
            c, addr = self.peerS.accept()
            start_new_thread(self.peer_thread, (c, addr))
    
    def peer_thread(self,conn,addr):
        conn.send(bytes('>>>>>Connected to Cluster Storage>>>>>\n', 'utf-8'))
        print('\nGot connection from Peer: \n', addr)
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
        message = f"{status} {phrase}\n"
        return message

    def client_thread(self, conn, addr):
        data = pickle.loads(conn.recv(1024))
        if not (self.authenticate(data[0],data[1])):
            conn.send("Failed.".encode())
            conn.close()
            return 
        conn.send(bytes('Connected to Server - Drive Storage HCMUT', 'utf-8'))
        data = pickle.loads(conn.recv(1024))
        my_port = data[1]
        print(f"\nGot connection from Client: {addr}, Client's receive port: {my_port}\n")
        username = data[0]
        while True:
            try:
                data = pickle.loads(conn.recv(1024))
                if data == "EXIT":
                    break
                elif data == "LIST":
                    print("Listing")
                    self.p2s_list_response(conn)
                    new_data = pickle.dumps(self.return_dict(username))
                    conn.send(new_data)
                else:
                    if data[0][0] == "A":
                        print(f"Client: {username} wants to upload\n")
                        success = self.handleADD(data[1], addr[0], my_port,username)
                        if not success:
                            print(f"Username: {username} - Upload failed, no peer to connect\n")
                            conn.send(bytes("404/Cannot upload at the moment, please try again later.\n",'utf-8'))
                        else:
                            print(f"Username: {username} - Peer found, connecting to peer\n")
                            self.p2s_add_response(conn, data[1], addr[0], addr[1])

                    elif data[2] == "0":
                        res = self.handleFetch(data[1],addr[0],username)
                        if(res==False):
                            new_data = pickle.dumps([None,"404"])
                            conn.send(new_data)
                        elif res[1]!="share":
                            new_data = pickle.dumps([res[0],"200"])
                            conn.send(new_data)
                        else:
                            new_data = pickle.dumps([res,"201"])
                            conn.send(new_data)
                    elif data[2] == "2":
                        res = self.handleDel(data[1],username)
                        if(res==False):
                            new_data = pickle.dumps("404")
                            
                            conn.send(new_data)
                        else:
                            self.delete_combined_dictionary(self.combined_list,data[1])
                            new_data = pickle.dumps("200")
                            conn.send(new_data)


                    elif data[2] == "1":
                        res = self.handleShare(data[1],addr[0],username,data[3])
                        if res:
                            new_data = pickle.dumps([res,"200"])
                            conn.send(new_data)
                        else:
                            new_data = pickle.dumps([None,"404"])
                            conn.send(new_data) 
            except KeyboardInterrupt: 
                break
            except socket.error:
                break
            except EOFError:
                break
        print("Closing connection!")
        conn.close()


    def ping(self,conn,lock):
        try:
            lock.acquire()
            conn.send(pickle.dumps("ping"))
            response = pickle.loads(conn.recv(1024))
            lock.release()
            if response[0] == "pong":
                return [True,response[1]]
            else:
                return [False]
        except (socket.error, ConnectionError):
            lock.release()
            for peers in self.peer_list:
                if peers["Connection"]==conn:
                    self.delete_peers_dictionary(peers["Hostname"])
            return "Ping failed."


    def handleDel(self,title,username):
        for inf in self.combined_list:
            if inf["File Title"]==title:
                for peer in self.peer_list:
                    if peer["Hostname"]==inf["Hostname"]:
                        res = self.ping(peer['Connection'],peer['PeerLock'])
                        if(res[0]!=False):
                            try:
                                peer['PeerLock'].acquire()
                                peer["Connection"].send(pickle.dumps(["delete",title,username]))
                                data = (peer["Connection"].recv(1024)).decode('utf-8')
                                peer['PeerLock'].release()
                                if(data=="200"):
                                    return True
                                else:
                                    print("hello")
                                    return False
                            except ConnectionError:
                                print("\nConnection Error with Peer")
                                peer['PeerLock'].release()
                                self.delete_peers_dictionary(self.peer_list,peer['Hostname'])

                            except:
                                print("\nUnexpected Error!\n")     
                                peer['PeerLock'].release()  
                                return False                       
        return False       

    def handleADD(self,title,host,up_port,owner):
        load= None
        chosenPeer = None
        for peer in self.peer_list:
            try:
                res = self.ping(peer['Connection'],peer['PeerLock'])
                if(res[0]!=False):
                    peerload = res[1]
                    print(peerload)
                    if (load==None) or peerload<load:
                        load=peerload 
                        chosenPeer = peer
            except:
                pass
        if(chosenPeer):
            sendData = pickle.dumps(["upload",title,host,up_port,owner])
            try:
                chosenPeer['PeerLock'].acquire()
                chosenPeer["Connection"].send(sendData)
                rtn = chosenPeer["Connection"].recv(1024).decode('utf-8')
                chosenPeer['PeerLock'].release()
                if rtn=="200": self.append_to_combined_list(self.combined_list,title,chosenPeer["Hostname"],chosenPeer["Upload Port"],owner)
                else: return False
            except:
                print("Error sending to peer:",chosenPeer["Host Name"])
                chosenPeer['PeerLock'].release()
                return False
            return True
        else:
            return False

    def handleFetch(self,title,host,username):
        found = None
        for inf in self.combined_list:
            if inf["File Title"]==title:
                for peer in self.peer_list:
                    if peer["Hostname"]==inf["Hostname"]:
                        res = self.ping(peer['Connection'],peer['PeerLock'])
                        if(res[0]!=False):
                            try:
                                peer['PeerLock'].acquire()
                                peer["Connection"].send(pickle.dumps(["fetch",title,host,username]))
                                data = pickle.loads(peer["Connection"].recv(1024))
                                peer['PeerLock'].release()
                                if(data=="200"):
                                    return [inf,'author']
                                elif data!="404":
                                    found = [inf,'share',data[1]]
                            except ConnectionError:
                                print("\nConnection Error with Peer")
                                peer['PeerLock'].release()   
                            except:
                                print("\nUnexpected Error!\n")     
                                peer['PeerLock'].release()   
        if found: return found                
        else: return False

    def handleShare(self,title,host,username,shareName):
        for inf in self.combined_list:
            if inf["File Title"]==title:
                for peer in self.peer_list:
                    if peer["Hostname"]==inf["Hostname"]:
                        res = self.ping(peer['Connection'],peer['PeerLock'])
                        if(res[0]!=False):
                            try:
                                peer['PeerLock'].acquire()
                                peer["Connection"].send(pickle.dumps(["share",title,host,username,shareName]))
                                data = peer["Connection"].recv(1024).decode('utf-8')
                                peer['PeerLock'].release()
                                if(data=="200"):
                                    return True
                            except ConnectionError:
                                print("\nConnection Error with Peer")
                                peer['PeerLock'].release()
                                self.delete_peers_dictionary(self.peer_list,peer['Hostname'])
                            except:
                                print("\nUnexpected Error!\n")
                                peer['PeerLock'].release()
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
            self.file_list_lock.acquire()
            dictionary_list.insert(0, dict(zip(keys, entry)))
            self.file_list_lock.release()

        return dictionary_list, keys

    def append_peer_list(self, dictionary_list, hostname, port,conn,up):
        keys = ['Hostname', 'Port Number','Connection','Upload Port','PeerLock']
        entry = [hostname, str(port),conn,up,Lock()]
        self.peer_list_lock.acquire()
        dictionary_list.insert(0, dict(zip(keys, entry)))
        self.peer_list_lock.release()
        return dictionary_list, keys


    def append_to_combined_list(self, dictionary_list, title, hostname, port,owner):
        keys = ['File Title', 'Hostname', 'Port Number','Owner']
        entry = [title, hostname, str(port),owner]
        self.file_list_lock.acquire()
        dictionary_list.insert(0, dict(zip(keys, entry)))
        self.file_list_lock.release()
        return dictionary_list

    def print_dictionary(self, dictionary_list, keys):
        for item in dictionary_list:
            print(' '.join([item[key] for key in keys]))

    def delete_peers_dictionary(self, dict_list_of_peers, hostname):
        dict_list_of_peers[:] = [d for d in dict_list_of_peers if d.get('Hostname') != hostname]
        return dict_list_of_peers


    def delete_combined_dictionary(self, combined_dict, title):
        self.file_list_lock.acquire()
        combined_dict[:] = [d for d in combined_dict if d.get('File Title') != title]
        self.file_list_lock.release()
        return combined_dict

    def search_combined_dict(self, title):
        for d in self.combined_list:
            if d['File Title'] == title:
                return d
        return False


    def return_dict(self,user):
        keys = ['File Title', 'Hostname', 'Port Number','Owner']
        return_list = [d for d in self.combined_list if d['Owner']==user]

        return return_list, keys
    def backup(self):
        with open('serverIF.pickle', 'wb') as f:  # open a text file
            listOfFiles = []
            for entries in self.combined_list:
                keys = ['File Title', 'Hostname', 'Port Number','Owner']
                entry = [entries['File Title'], entries['Hostname'], entries['Port Number'],entries['Owner']]
                listOfFiles.insert(0,dict(zip(keys,entry)))
            data = [listOfFiles]
            pickle.dump(data, f) # serialize the list

if __name__ == "__main__":
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        host = s.getsockname()[0]
        s.close()
        client_port = 7737
        peer_port = 7736
        server = Server(host, client_port,peer_port)
        start_new_thread(server.start_Client,())
        start_new_thread(server.start_Cluster,())
        while True:
            pass
    except KeyboardInterrupt:
        server.backup()
