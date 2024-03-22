import paho.mqtt.client as mqtt
import customtkinter as ctk
import webbrowser
from tkinter import messagebox
import json
import tkinter as tk
import os.path as path

# TODO: File sharing

class DataSharingApp(ctk.CTk):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        self.title("Local Data Sharing")
        
        ctk.set_appearance_mode("dark")
        
        self.columnconfigure((0, 1), weight=1)
        
        # load config
        with open("config.json") as f:
            self.__config = json.load(f)
        self.__current_channel = self.__config.get("channel", "datashare/default")
        
        # create interface
        channel_frame = ctk.CTkFrame(self, bg_color="transparent")
        channel_frame.grid(row=0, column=0, columnspan=2, sticky="NSEW", padx=5, pady=5)
        channel_frame.columnconfigure(0, weight=4)
        channel_frame.columnconfigure(1, weight=1)
        
        self.__channel_entry = ctk.CTkEntry(channel_frame, placeholder_text="MQTT Channel")
        self.__channel_entry.grid(row=0, column=0, sticky="NSEW", padx=5, pady=5)
        self.__channel_entry.insert(0, self.__current_channel)
        ctk.CTkButton(channel_frame, text="Set Channel", command=self.set_channel).grid(row=0, column=1, sticky="NSEW", padx=5, pady=5)
        
        self.__message_entry = ctk.CTkEntry(self, placeholder_text="Message Text")
        self.__message_entry.grid(row=1, column=0, columnspan=2, sticky="NSEW", padx=5, pady=5)
        
        ctk.CTkButton(self, text="Send as Text", command=self.send_text).grid(row=2, column=0, sticky="NSEW", padx=5, pady=5)
        ctk.CTkButton(self, text="Send as Link", command=self.send_link).grid(row=2, column=1, sticky="NSEW", padx=5, pady=5)
        
        ctk.CTkButton(self, text="Send a File", command=self.send_file).grid(row=3, column=0, columnspan=2, sticky="NSEW", padx=5, pady=5)
        
        self.__data_stream = ctk.CTkTextbox(self)
        self.__data_stream.grid(row=4, column=0, columnspan=2, sticky="NSEW", padx=5, pady=5)
        
        self.setup_mqtt()
        
        self.__just_sent = False
        
    def setup_mqtt(self):
        self.__client = mqtt.Client()
        
        self.__client_connected = False
        
        self.__client.on_connect = self.on_connect
        self.__client.on_message = self.on_message
        self.__client.on_disconnect = self.on_disconnect
        
        self.__client.connect(self.__config.get("server", "127.0.0.1"), self.__config.get("port", 1883), 60)
        self.__client.loop_start()
        
    def on_connect(self, client, userdata, flags, rc):
        messagebox.showinfo("MQTT Connected", f"Connected to MQTT Server with response code {rc}.")
        self.__client_connected = True
        self.__client.subscribe(self.__current_channel)
    
    def on_disconnect(self, client, userdata, rc):
        messagebox.showerror("MQTT Disconnected", f"Disconnected from MQTT Server with response code {rc}.")
        self.__client_connected = False
    
    def on_message(self, client, userdata, msg):
        decoded = msg.payload.decode("utf-8")
        payload = json.loads(decoded)
        if payload.get("type") == "text":
            self.add_to_list(f"Text Received: {payload.get('content')}")
        elif payload.get("type") == "link":
            link = payload.get('content')
            self.add_to_list(f"Link Received: {link}")
            if self.__just_sent:
                self.__just_sent = False
            else:
                if self.__config.get("auto_open_link"):
                    webbrowser.open(link)
                else:
                    if messagebox.askyesno("Link Received", f"Link Received: '{link}'. Open?"):
                        webbrowser.open(link)
        elif payload.get("type") == "file":
            if self.__just_sent:
                self.__just_sent = False
            else:
                save_location = tk.filedialog.askdirectory()
                if not save_location:
                    return
                
                with open(path.join(save_location, payload.get("filename", "unknown")), "wb") as f:
                    f.write(payload.get("content"))
        
    def add_to_list(self, text):
        self.__data_stream.insert(tk.END, text + "\n")
        
    def set_channel(self):
        if self.__client_connected:
            self.__client.unsubscribe(self.__current_channel)
            self.__client.subscribe(self.__channel_entry.get())
            self.__current_channel = self.__channel_entry.get()
    
    def send_text(self):
        if self.__client_connected:
            payload = {
                "type" : "text",
                "content" : self.__message_entry.get()
            }
            self.__client.publish(self.__current_channel, json.dumps(payload))
            self.__message_entry.delete(0, tk.END)
    
    def send_link(self):
        if self.__client_connected:
            payload = {
                "type" : "link",
                "content" : self.__message_entry.get()
            }
            self.__client.publish(self.__current_channel, json.dumps(payload))
            self.__message_entry.delete(0, tk.END)
            self.__just_sent = True
    
    def send_file(self):
        filename = tk.filedialog.askopenfilename(filetypes=(("All files","*.*")))
        if not filename:
            return
        
        with open(filename, "rb") as f:
            content = f.read()
            
        basename = path.basename(filename)
        
        if self.__client_connected:
            payload = {
                "type" : "file",
                "filename" : basename,
                "content" : content
            }
            
            self.__client.publish(self.__current_channel, json.dumps(payload))
            self.__just_sent = True
            
app = DataSharingApp()
app.mainloop()