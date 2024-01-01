import socket
import time
import platform
import os
import pickle
import random
from _thread import *
import tkinter as tk
import customtkinter
from PIL import ImageTk,Image
customtkinter.set_appearance_mode("Dark")
customtkinter.set_default_color_theme("MoonlitSky.json")

class Client:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.upload_port_num = 65000 + random.randint(1, 500)

    def connect_to_server(self,username,password):
        try:
            self.s = socket.socket()
            self.s.connect((self.host, self.port))
            data = pickle.dumps([username,password])
            self.s.send(data)
            server_data = self.s.recv(1024)
            if(server_data.decode('utf-8')!="Failed."):
                self.username=username
                data = pickle.dumps([self.username,self.upload_port_num])
                self.s.send(data)
                return True
            else: 
                self.s.close()
                return False
        except ConnectionRefusedError:
            return False
    def LIST(self):
        data = pickle.dumps("LIST")
        self.s.send(data)
        res = self.s.recv(1024).decode('utf-8')
        if(res[:3]=="200"):
            server_data = pickle.loads(self.s.recv(1024))
            list_files = server_data[0]
            if len(list_files)>0:
                return list_files
        return None
                
    def DEL(self, title):
        data = pickle.dumps(self.p2s_lookup_message(title, "2"))
        self.s.send(data)
        server_data = pickle.loads(self.s.recv(1024))
        if server_data=="404":
            return False
        else:
            return True
    def EXIT(self):
            data = pickle.dumps("EXIT")
            self.s.send(data)
            self.s.close()

            
    def ADD(self,user_input_file_title):
        data = pickle.dumps(self.p2s_add_message(user_input_file_title))
        self.s.send(data)
        server_data = self.s.recv(1024)
        server_data=server_data.decode('utf-8')
        if(server_data[:3]=='200'):
            return True
        else: return False

    def GET(self,user_input_file_title):
        data = pickle.dumps(self.p2s_lookup_message(user_input_file_title, "0"))
        self.s.send(data)
        server_data = pickle.loads(self.s.recv(1024))
        if not server_data[0]:
            return False
        elif server_data[1]=="200":
            if self.p2p_get_request((user_input_file_title), server_data[0]["Hostname"], server_data[0]["Port Number"]):
                return True
            return False
        else:
            if self.p2p_get_request1((user_input_file_title), server_data[0][0]["Hostname"], server_data[0][0]["Port Number"],server_data[0][2]):
                return True
            return False
    def SHARE(self,file_name,share_name):
        data = pickle.dumps(["SHARING",file_name ,"1",share_name])
        self.s.send(data)
        server_data = pickle.loads(self.s.recv(1024))
        print("SERVER RESPONSE:", server_data)
        if not server_data[0]:
            print(server_data[1])
            return False
        else:
            return True
    def transfer_file(self,conn,title):
        filename = f"{title}"
        m = filename.split()
        filename = "".join(m)
        current_path = os.getcwd()
        if platform.system() == "Windows":
            filename = current_path+"\\local_storage\\" + filename
        else:
            filename = current_path+"/local_storage/" + filename
        try:
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
        except OSError as e:
            conn.send(bytes("404",'utf-8'))

#send file in here
    def p2p_listen_thread(self, str, i):
        upload_socket = socket.socket()
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
            datasend = self.p2p_response_message(file_name)
            c.send(pickle.dumps(datasend))
            if datasend[1]=="200":
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
        s.send(pickle.dumps(data))
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
            except ConnectionError:
                s.close()
                return False

        s.close()
        return True
     #this is where client receive the files
    def p2p_get_request1(self, title, peer_host, peer_upload_port,username):
        s = socket.socket()
        s.connect((peer_host, int(peer_upload_port)))
        data = self.p2p_request_message_share(title,username)
        s.send(pickle.dumps(data))
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
            except ConnectionError:
                s.close()
                return False
        s.close()
        return True
    def p2p_request_message(self, title):
        OS = platform.platform()
        message = f"GET FILE {title} HCMUT_CN \n"\
                  f"Host: {self.host}\n"\
                  f"OS: {OS}\n"\
                  f"Owner:\n"
        return [message,self.username]
    def p2p_request_message_share(self, title,username):
        OS = platform.platform()
        message = f"GET FILE {title} HCMUT_CN \n"\
                  f"Host: {self.host}\n"\
                  f"OS: {OS}\n"\
                  f"Owner:\n"
        return [message,username]

#This is where peers send files 
    def p2p_response_message(self, title):
        filename = f"{title}"
        current_time = time.strftime("%a, %d %b %Y %X %Z", time.localtime())
        OS = platform.system()
        m = filename.split()
        filename = "".join(m)
        current_path = os.getcwd()
        if OS == "Windows":
            filename = current_path+"\\local_storage\\" + filename
        else:
            filename =current_path+ "/local_storage/" + filename
        print(filename)
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




s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.connect(("8.8.8.8", 80))
host = s.getsockname()[0]
client = Client(host, 7737)
start_new_thread(client.p2p_listen_thread, ("hello", 1))



#create a window to login, after loggin, proceed to below || Pass the functions in the UI to the right functions in the object|| create the object first, run the login UI

app = customtkinter.CTk()  #creating cutstom tkinter window
app.geometry("600x440")
app.title('Login')



def button_function():
    if not client.connect_to_server(str(UserName.get()),str(PassWord.get())):
        return
    def clear_placeholder(event):
        if up_entry.get() == "Enter file to upload":
            up_entry.delete(0, tk.END)

    def restore_placeholder(event):
        if not up_entry.get():
            up_entry.insert(0, "Enter file to upload")

    def clear_placeholder1(event):
        if fetch_entry.get() == "Enter file to fetch":
            fetch_entry.delete(0, tk.END)

    def restore_placeholder1(event):
        if not fetch_entry.get():
            fetch_entry.insert(0, "Enter file to fetch")

    def clear_placeholder2(event):
        if share_entry.get() == "Enter file to share":
            share_entry.delete(0, tk.END)

    def restore_placeholder2(event):
        if not share_entry.get():
            share_entry.insert(0, "Enter file to share")
    def clear_placeholder3(event):
        if share_entry_name.get() == "Enter username to share":
            share_entry_name.delete(0, tk.END)

    def restore_placeholder3(event):
        if not share_entry_name.get():
            share_entry_name.insert(0, "Enter username to share")

    def clear_placeholder4(event):
        if del_entry.get() == "Enter file to delete":
            del_entry.delete(0, tk.END)

    def restore_placeholder4(event):
        if not del_entry.get():
            del_entry.insert(0, "Enter file to delete")

    def show_entry1():
        my_frame.pack_forget()
        del_frame.pack_forget()
        share.pack_forget()
        UpFrame.pack_forget()
        fetchFrame.pack(side='left')
    def show_entry2():
        my_frame.pack_forget()
        del_frame.pack_forget()
        share.pack_forget()
        fetchFrame.pack_forget()
        UpFrame.pack(side='left')
    def show_entry3():
        my_frame.pack_forget()
        del_frame.pack_forget()
        UpFrame.pack_forget()
        fetchFrame.pack_forget()
        share.pack(side='left')
    def show_entry4():
        my_frame.pack_forget()
        share.pack_forget()
        UpFrame.pack_forget()
        fetchFrame.pack_forget()
        del_frame.pack(side='left')
    def SHOW():
        del_frame.pack_forget()
        share.pack_forget()
        UpFrame.pack_forget()
        fetchFrame.pack_forget()
        for widget in my_frame.winfo_children():
            widget.destroy()
        list_files = client.LIST()
        if list_files:
            print(list_files)
            for files in list_files:
                customtkinter.CTkLabel(my_frame, text=files['File Title']).pack(pady=10)

        my_frame.pack(side='left')

    def submit_action1():
        try:
            print("i will try to fetch")
            file_name = fetch_entry.get()
            if file_name != "Enter file to fetch":
                print(f"File name entered: {file_name}")
                if client.GET(file_name):
                    succesF()
                else: failF()
                
                # Perform further actions based on the entered file name

            # Hide the submit button after submitting
            fetch_entry.delete(0, tk.END)
            fetch_entry.insert(0, "Enter file to fetch")
            fetchFrame.pack_forget()
            root.focus_set()
        except:
            destroy()
    def submit_action2():
        try:
            file_name = up_entry.get()
            if file_name != "Enter file to upload":
                print(f"File name entered: {file_name}")
                if client.ADD(file_name):
                    succesPop()
                else:
                    failPop()
                # Perform further actions based on the entered file name

            # Hide the submit button after submitting
            up_entry.delete(0, tk.END)
            up_entry.insert(0, "Enter file to upload")
            UpFrame.pack_forget()
            root.focus_set()
        except:
            destroy()
    def submit_action3():
        try:
            file_name = share_entry.get()
            share_name = share_entry_name.get()
            if file_name != "Enter file to share" and share_name!= "Enter username to share":
                print(f"File name entered: {file_name}")
                if not client.SHARE(file_name,share_name):
                    print("failed")
                else:
                    print("Success")

                # Perform further actions based on the entered file name

            # Hide the submit button after submitting
            share_entry.delete(0, tk.END)
            share_entry.insert(0, "Enter file to share")
            share_entry_name.delete(0, tk.END)
            share_entry_name.insert(0, "Enter username to share")
            share.pack_forget()
            root.focus_set()
        except:
            destroy()
    def submit_action4():
        try:
            file_name = del_entry.get()
            if file_name != "Enter file to delete" and file_name!="":
                print(f"File name entered: {file_name}")
                if client.DEL(file_name):
                    print(f"File deleted: {file_name}") 
                else:
                    print("Delete failed")
                    return False

                # Perform further actions based on the entered file name

            # Hide the submit button after submitting
            del_entry.delete(0, tk.END)
            del_entry.insert(0, "Enter file to delete")
            del_frame.pack_forget()
            root.focus_set()
        except:
            destroy()
    def EXIT():
        try:
            client.EXIT()
            root.destroy()
        except:
            destroy()
    def succesPop():
        global pop
        pop = tk.Toplevel(root)
        pop.title("Notification")
        pop.geometry("150x100")
        pop.config(bg="green")
        #pop.grab_set()
        pop_label = tk.Label(pop, text="Uploading Successful !", bg="green", fg="white", font=("helvetica", 12))
        pop_label.pack(pady=10)
    def failPop():
        global pop
        pop = tk.Toplevel(root)
        pop.title("Notification")
        pop.geometry("150x100")
        pop.config(bg="red")
        #pop.grab_set()
        pop_label = tk.Label(pop, text="Uploading Failed !", bg="red", fg="white", font=("helvetica", 12))
        pop_label.pack(pady=10)
    def succesF():
        global pop
        pop = tk.Toplevel(root)
        pop.title("Notification")
        pop.geometry("150x100")
        pop.config(bg="green")
        #pop.grab_set()
        pop_label = tk.Label(pop, text="Fetched Successful !", bg="green", fg="white", font=("helvetica", 12))
        pop_label.pack(pady=10)
    def failF():
        global pop
        pop = tk.Toplevel(root)
        pop.title("Notification")
        pop.geometry("150x100")
        pop.config(bg="red")
        #pop.grab_set()
        pop_label = tk.Label(pop, text="Fetched Failed !", bg="red", fg="white", font=("helvetica", 12))
        pop_label.pack(pady=10)
    def serverCrash():
        global pop
        pop = tk.Tk()
        pop.title("HCMUT-DRIVE")
        pop.geometry("150x100")
        pop.config(bg="red")
        #pop.grab_set()
        pop_label = tk.Label(pop, text="APP closed - Server Failed !", bg="red", fg="white", font=("helvetica", 12))
        pop_label.pack(pady=10)
    def destroy():
        serverCrash()
        root.destroy()


    app.destroy()            # destroy current window and creating new one 
    root = customtkinter.CTk()
    root.title("HCMUT DRIVE")
    root.geometry("1200x880")
    mainFrame = customtkinter.CTkFrame(root,width=400,height=400)
    mainFrame.pack_propagate(False)
    mainFrame.pack(side='left')
    title = customtkinter.CTkLabel(mainFrame,text="Welcome to HCMUT DRIVE\n",font=('Arial', 15))
    title.pack(pady=5)
    options = customtkinter.CTkLabel(mainFrame, text="Choose an action:", font=('Arial', 10, 'italic'))
    options.pack(pady=5)
    upload_button = customtkinter.CTkButton(mainFrame, text="Upload File", command=show_entry2)
    upload_button.pack(pady=10)

    fetch_button = customtkinter.CTkButton(mainFrame, text="Fetch File", command=show_entry1)
    fetch_button.pack(pady=10)

    share_button = customtkinter.CTkButton(mainFrame, text="Share File", command=show_entry3)
    share_button.pack(pady=10)

    del_button = customtkinter.CTkButton(mainFrame, text="Delete File", command=show_entry4)
    del_button.pack(pady=10)

    show_button = customtkinter.CTkButton(mainFrame, text="List File", command=SHOW)
    show_button.pack(pady=10)

    exit_button = customtkinter.CTkButton(mainFrame, text="Exit", command=EXIT)
    exit_button.configure(fg_color="Red")
    exit_button.pack(pady=10)




    fetchFrame = customtkinter.CTkFrame(root, width=200, height=400)
    fetchFrame.pack_propagate(False)
    fetchFrame.pack_forget()

    

    fetch_label = customtkinter.CTkLabel(fetchFrame, text="Enter file to fetch", font=('Arial', 10, 'italic'))
    fetch_label.pack(pady=10)

    fetch_entry = customtkinter.CTkEntry(fetchFrame, font=('Arial', 10))
    fetch_entry.insert(0, "Enter file to fetch")
    fetch_entry.bind("<FocusIn>", clear_placeholder1)
    fetch_entry.bind("<FocusOut>", restore_placeholder1)
    fetch_entry.pack(pady=10)

    submit_fetch = customtkinter.CTkButton(fetchFrame, text="Submit", command=submit_action1)
    submit_fetch.pack(pady=10)


    UpFrame = customtkinter.CTkFrame(root, width=200, height=400)
    UpFrame.pack_propagate(False)
    UpFrame.pack_forget()

    up_label = customtkinter.CTkLabel(UpFrame, text="Enter file to upload", font=('Arial', 10, 'italic'))
    up_label.pack(pady=10)

    up_entry = customtkinter.CTkEntry(UpFrame, font=('Arial', 10))
    up_entry.insert(0, "Enter file to upload")
    up_entry.bind("<FocusIn>", clear_placeholder)
    up_entry.bind("<FocusOut>", restore_placeholder)
    up_entry.pack(pady=10)

    submit_up = customtkinter.CTkButton(UpFrame, text="Submit", command=submit_action2)
    submit_up.pack(pady=10)


    share = customtkinter.CTkFrame(root, width=200, height=400)
    share.pack_propagate(False)
    share.pack_forget()

    share_label = customtkinter.CTkLabel(share, text="Enter file to share", font=('Arial', 10, 'italic'))
    share_label.pack(pady=10)

    share_entry = customtkinter.CTkEntry(share, font=('Arial', 10))
    share_entry.insert(0, "Enter file to share")
    share_entry.bind("<FocusIn>", clear_placeholder2)
    share_entry.bind("<FocusOut>", restore_placeholder2)
    share_entry.pack(pady=10)

    share_entry_name=customtkinter.CTkEntry(share, font=('Arial', 10))
    share_entry_name.insert(0, "Enter username to share")
    share_entry_name.bind("<FocusIn>", clear_placeholder3)
    share_entry_name.bind("<FocusOut>", restore_placeholder3)
    share_entry_name.pack(pady=10)    

    share_submit = customtkinter.CTkButton(share, text="Submit", command=submit_action3)
    share_submit.pack(pady=10)


    del_frame = customtkinter.CTkFrame(root, width=200, height=400)
    del_frame.pack_propagate(False)
    del_frame.pack_forget()

    del_label = customtkinter.CTkLabel(del_frame, text="Enter file to delete", font=('Arial', 10, 'italic'))
    del_label.pack(pady=10)

    del_entry = customtkinter.CTkEntry(del_frame, font=('Arial', 10))
    del_entry.insert(0, "Enter file to delete")
    del_entry.bind("<FocusIn>", clear_placeholder4)
    del_entry.bind("<FocusOut>", restore_placeholder4)
    del_entry.pack(pady=10)

    del_submit = customtkinter.CTkButton(del_frame, text="Submit", command=submit_action4)
    del_submit.pack(pady=10)

    my_frame = customtkinter.CTkScrollableFrame(root,
    width=200,
    height=340,
    label_text="List of Files:",
    label_font=("Helvetica", 12),
    label_anchor = "center")

    my_frame.pack_forget()


    root.mainloop()
        


img1=ImageTk.PhotoImage(Image.open("pattern.png"))
l1=customtkinter.CTkLabel(master=app,image=img1)
l1.pack()

#creating custom frame
frame=customtkinter.CTkFrame(master=l1, width=320, height=360, corner_radius=15)
frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

l2=customtkinter.CTkLabel(master=frame, text="Log into your Account",font=('Century Gothic',20))
l2.place(x=50, y=45)

UserName=customtkinter.CTkEntry(master=frame, width=220, placeholder_text='Username')
UserName.place(x=50, y=110)

PassWord=customtkinter.CTkEntry(master=frame, width=220, placeholder_text='Password', show="*")
PassWord.place(x=50, y=165)


#Create custom button
button1 = customtkinter.CTkButton(master=frame, width=220, text="Login", command=button_function, corner_radius=6)
button1.place(x=50, y=240)





# You can easily integrate authentication system 

app.mainloop()
# Usage

