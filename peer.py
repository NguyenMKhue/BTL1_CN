import socket
import time
import platform
import os
import pickle
import random
from _thread import *
import schedule
from threading import Lock
class Peer:
    def __init__(self, host, port):
        self.serverLock = Lock()
        self.dictLock = Lock()
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
        if self.dict_list_of_rfcs:
            for entries in self.dict_list_of_rfcs:
                entries['FileLock'] = Lock()

    def listenServer(self):
        while True:
            try:
                data = pickle.loads(self.s.recv(1024))
                if data == "ping":
                    data = pickle.dumps(["pong",self.load])
                    self.serverLock.acquire()
                    self.s.send(data)
                    self.serverLock.release()
                if data:
                    if data[0] == "fetch":
                        print("Received fetch request from Server\n")
                        found = False
                        for file in self.dict_list_of_rfcs:
                            print(file)
                            if file["File Title"]==data[1]:
                                if (data[3]==file["Owner"]):
                                    self.serverLock.acquire()
                                    self.s.send(pickle.dumps("200"))
                                    self.serverLock.release()
                                    found=True
                                elif file['Share']:
                                    if data[3] in file["Share"]:
                                        print("found 1")
                                        username=file["Owner"]
                                        self.serverLock.acquire()
                                        self.s.send(pickle.dumps(["201",username]))
                                        self.serverLock.release()
                                        found=True
                        if(found==False):
                            print("not found")
                            self.serverLock.acquire()
                            self.s.send(pickle.dumps("404"))
                            self.serverLock.release()
                    elif data[0]=="delete":
                        print("Delete request from Server\n")
                        found = False
                        del_file = None
                        for file in self.dict_list_of_rfcs:
                            if file["File Title"]==data[1]:
                                if (data[2]==file["Owner"]):
                                    del_file=file
                                    found=True
                                    break
                                elif file['Share']:
                                    if data[2] in file["Share"]:
                                        print("found 1")
                                        username=file["Owner"]
                                        del_file=file
                                        found=True
                                        break
                        if(found==False):
                            print("not found")
                            self.serverLock.acquire()
                            self.s.send("404".encode())
                            self.serverLock.release()
                        else:
                            start_new_thread(self.delete_file, (data[1], data[2],del_file))


                    elif data[0]=="upload":
                        print("Received upload request from Server\n")
                        start_new_thread(self.p2p_get_request,(data[1],data[2],data[3],data[4]))
                    elif data[0]=="share":
                        print("Sharing a file to a new user\n")
                        found = False
                        for file in self.dict_list_of_rfcs:
                            if file["File Title"]==data[1]:
                                if (data[3]==file["Owner"]):
                                    if file["Share"]:
                                        file["Share"].insert(0,data[4])
                                    else:
                                        file["Share"] = [data[4]]
                                    self.serverLock.acquire()
                                    self.s.send("200".encode())
                                    self.serverLock.release()
                                    found=True
                        if(found==False):
                            self.serverLock.acquire()
                            self.s.send("404".encode())
                            self.serverLock.release()

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

    def delete_file(self,title,owner,file):
        fileLock = file["FileLock"]
        current_path = os.getcwd()
        OS = platform.system()
        filename = f"{title}"
        folderDir = f""
        if OS == "Windows":
            folderDir = current_path + "\\peer_storage\\" + owner
            filename = folderDir+"\\"+filename
        else:
            folderDir = current_path + "/peer_storage/" + owner
            filename = folderDir + "/" + filename
        print(filename)
        try:
            if fileLock: fileLock.acquire()
            os.chmod(filename, 0o777)
            os.remove(filename)
            if fileLock: fileLock.release()
            self.serverLock.acquire()
            self.s.send("200".encode())
            self.serverLock.release()
            self.delete_combined_dictionary(self.dict_list_of_rfcs,title)

        except Exception:
            print(Exception)
            if fileLock: fileLock.release()
            self.serverLock.acquire()
            self.s.send("404".encode())
            self.serverLock.release()
       
    def delete_combined_dictionary(self, combined_dict, title):
        self.dictLock.acquire()
        combined_dict[:] = [d for d in combined_dict if d.get('File Title') != title]
        self.dictLock.release()
        return combined_dict

    def transfer_file(self,conn,title,username):
        fileLock = None
        for file in self.dict_list_of_rfcs:
            if file["File Title"]==title:
                if file['Owner']==username:
                    fileLock = file['FileLock']
        current_path = os.getcwd()
        OS = platform.system()
        filename = f"{title}"
        m = filename.split()
        filename = "".join(m)
        folderDir = f""
        if OS == "Windows":
            folderDir = current_path + "\\peer_storage\\" + username
            filename = folderDir+"\\"+filename
        else:
            folderDir = current_path + "/peer_storage/" + username
            filename = folderDir + "/" + filename
        try:
            if fileLock: fileLock.acquire()
            file = open(filename,"rb")
            sendbyte=b""
            while True:
                data = file.read(4096)  # Read 1 KB at a time (adjust as needed)
                if not data:
                    break
                sendbyte+=data
            conn.sendall(sendbyte)
            conn.send(b"<|:::|>")
            file.close()
        except OSError:
            conn.send(bytes("404",'utf-8'))
        finally:
            if fileLock: fileLock.release()

#send file in here
    def p2p_listen_thread(self, str, i):
        upload_socket = socket.socket()
        upload_socket.bind((host, self.upload_port_num))
        upload_socket.listen(5)
        while True:
            try:
                c, addr = upload_socket.accept()
                start_new_thread(self.handleClients,(c,addr))
            except KeyboardInterrupt:
                break
        upload_socket.close()

    def handleClients(self,c,addr):
        self.load = self.load + 1
        try:
            data_p2p_undecode = c.recv(1024)
            data_p2p = pickle.loads(data_p2p_undecode)
            indexP = data_p2p[0].index('H')
            indexL = data_p2p[0].index('L')
            file_name = data_p2p[0][indexL+2:indexP-1]
            username = data_p2p[1]
            print('Got request from:', addr)
            c.send(pickle.dumps(self.p2p_response_message(file_name,username)))
            self.transfer_file(c,file_name,username)
            c.close()
            self.load = self.load - 1
        except pickle.UnpicklingError:
            self.load = self.load - 1
            print("pickling error!")
            self.handleClients(c,addr)
        except ConnectionError:
            print("Connection error with: ",addr)
            self.load = self.load - 1
            return
 

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
            folderDir = f""
            if OS == "Windows":
                folderDir = current_path + "\\peer_storage\\" + owner
                filename = folderDir+"\\"+filename
            else:
                folderDir = current_path + "/peer_storage/" + owner
                filename = folderDir + "/" + filename
            os.makedirs(folderDir, exist_ok=True)
            fileLock = None
            for file in self.dict_list_of_rfcs:
                if file["File Title"]==title and file['Owner']==owner:
                    fileLock = file['FileLock']
            if fileLock:
                fileLock.acquire()
                try:
                    with open(filename, "wb") as file:
                        done = False
                        file_b = b""
                        while not done:
                            data = s.recv(4096)
                            if file_b[-7:]==b"<|:::|>":
                                done=True
                            else:
                                file_b+=data
                        file.write(file_b[:-7])
                        file.close()
                        self.serverLock.acquire()
                        self.s.send("200".encode())
                        self.serverLock.release()
                except:
                    self.serverLock.acquire()
                    self.s.send("404".encode())
                    self.serverLock.release() 
                finally:
                    fileLock.release()

            
            else:
                try:
                    with open(filename, "wb") as file:
                        done = False
                        file_b = b""
                        while not done:
                            data = s.recv(4096)
                            if file_b[-7:]==b"<|:::|>":
                                done=True
                            else:
                                file_b+=data
                        file.write(file_b[:-7])
                        file.close()
                        keys = ['File Title', 'Owner','Share','FileLock']
                        entry = [title, owner, None,Lock()]
                        self.dictLock.acquire()
                        self.dict_list_of_rfcs.insert(0,dict(zip(keys,entry)))
                        self.dictLock.release()
                        self.serverLock.acquire()
                        self.s.send("200".encode())
                        self.serverLock.release()
                except:
                    print("Error occured when transferring!")
                    self.serverLock.acquire()
                    self.s.send("404".encode())
                    self.serverLock.release()
                    return


                print(f"\nNew file added - username: {owner}, file name:{title}\n")
        s.close()

    def p2p_request_message(self, title):
        OS = platform.platform()
        message = f"GET FILE {title} HCMUT \n"\
                  f"Host: {self.host}\n"\
                  f"OS: {OS}\n"
        return message


#This is where peers send files 
    def p2p_response_message(self, title, username):
        filename = f"{title}"
        current_time = time.strftime("%a, %d %b %Y %X %Z", time.localtime())
        OS = platform.system()
        m = filename.split()
        filename = "".join(m)
        folderDir = f""
        current_path = os.getcwd()
        if OS == "Windows":
            folderDir = current_path + "\\peer_storage\\" + username
            filename = folderDir+"\\"+filename
        else:
            folderDir = current_path + "/peer_storage/" + username
            filename = folderDir + "/" + filename

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
        print("\n>>>>>Peer Backing Up\n")
        with open('peerIF.pickle', 'wb') as f:  # open a text file
            listOfFiles = []
            for entries in self.dict_list_of_rfcs:
                keys = ['File Title', 'Owner','Share']
                entry = [entries['File Title'], entries['Owner'], entries['Share']]
                listOfFiles.insert(0,dict(zip(keys,entry)))
            data = [listOfFiles,self.upload_port_num]
            pickle.dump(data, f) # serialize the list
    def scheduledBackup(self):
        schedule.every(2).minutes.do(self.backup)
        while True:
            schedule.run_pending()
            time.sleep(10)


        

# Usage
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.connect(("8.8.8.8", 80))
host = s.getsockname()[0]
worker = Peer(host, 7736)
start_new_thread(worker.p2p_listen_thread, ("hello", 1))
start_new_thread(worker.scheduledBackup,())
worker.listenServer()
