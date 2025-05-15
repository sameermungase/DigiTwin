#!/usr/bin/env python3
import os
import json
import base64
import zipfile
import io
import tkinter as tk
from tkinter import ttk, messagebox
import websocket
import threading
import time
from datetime import datetime

class LaptopClientApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Jetson Nano Camera Controller")
        self.root.geometry("800x600")
        
        # WebSocket server URL (update with your Render server URL when deployed)
        self.ws_url = "ws://your-render-app.onrender.com/laptop"
        
        # WebSocket connection
        self.ws = None
        self.connected = False
        
        # File transfer state
        self.receiving_file = False
        self.current_folder = None
        self.file_chunks = []
        self.file_size = 0
        
        # Base folder for saving received images
        self.save_folder = "received_images"
        if not os.path.exists(self.save_folder):
            os.makedirs(self.save_folder)
        
        # Create UI elements
        self.create_ui()
        
        # Connect to WebSocket server
        self.connect_websocket()

    def create_ui(self):
        """Create the user interface"""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Connection status
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(status_frame, text="Connection Status:").pack(side=tk.LEFT, padx=5)
        self.status_label = ttk.Label(status_frame, text="Disconnected", foreground="red")
        self.status_label.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(status_frame, text="Reconnect", command=self.connect_websocket).pack(side=tk.RIGHT, padx=5)
        
        # Separator
        ttk.Separator(main_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        
        # Capture controls
        capture_frame = ttk.LabelFrame(main_frame, text="Capture Controls", padding="10")
        capture_frame.pack(fill=tk.X, pady=10)
        
        # Folder name input
        folder_frame = ttk.Frame(capture_frame)
        folder_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(folder_frame, text="Folder Name:").pack(side=tk.LEFT, padx=5)
        
        self.folder_name_var = tk.StringVar(value=datetime.now().strftime("%Y%m%d_%H%M%S"))
        self.folder_entry = ttk.Entry(folder_frame, textvariable=self.folder_name_var, width=30)
        self.folder_entry.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(folder_frame, text="Generate New Name", 
                   command=lambda: self.folder_name_var.set(datetime.now().strftime("%Y%m%d_%H%M%S"))).pack(side=tk.LEFT, padx=5)
        
        # Buttons frame
        buttons_frame = ttk.Frame(capture_frame)
        buttons_frame.pack(fill=tk.X, pady=10)
        
        # Start capture button
        self.start_button = ttk.Button(buttons_frame, text="Start Capture", 
                                       command=self.start_capture, style="Accent.TButton")
        self.start_button.pack(side=tk.LEFT, padx=10, pady=5, expand=True, fill=tk.X)
        
        # Stop and download button
        self.stop_button = ttk.Button(buttons_frame, text="Stop Capture & Download", 
                                     command=self.stop_capture, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=10, pady=5, expand=True, fill=tk.X)
        
        # Separator
        ttk.Separator(main_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        
        # Log and status area
        log_frame = ttk.LabelFrame(main_frame, text="Status Log", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Scrolled text widget for log
        self.log_text = tk.Text(log_frame, height=10, wrap=tk.WORD, state=tk.DISABLED)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)
        
        # Progress bar for file transfer
        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(progress_frame, text="Transfer Progress:").pack(side=tk.LEFT, padx=5)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.progress_label = ttk.Label(progress_frame, text="0%")
        self.progress_label.pack(side=tk.RIGHT, padx=5)
        
        # Style configuration
        style = ttk.Style()
        style.configure("Accent.TButton", font=("Arial", 10, "bold"))

    def log_message(self, message):
        """Add a message to the log text widget"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        print(message)  # Also print to console for debugging

    def connect_websocket(self):
        """Establish connection to the WebSocket server"""
        def on_open(ws):
            self.connected = True
            self.status_label.config(text="Connected", foreground="green")
            self.log_message("Connected to server")
            # Register as laptop client
            self.ws.send(json.dumps({
                "type": "register",
                "client_type": "laptop"
            }))

        def on_message(ws, message):
            try:
                data = json.loads(message)
                message_type = data.get("type", "")
                
                # Handle different message types
                if message_type == "capture_started":
                    folder_name = data.get("folder_name", "")
                    self.log_message(f"Capture started on Jetson in folder: {folder_name}")
                    self.start_button.config(state=tk.DISABLED)
                    self.stop_button.config(state=tk.NORMAL)
                
                elif message_type == "file_transfer_start":
                    self.receiving_file = True
                    self.current_folder = data.get("folder_name", "unknown")
                    self.file_size = data.get("file_size", 0)
                    self.file_chunks = []
                    self.log_message(f"Starting to receive file for folder: {self.current_folder} ({self.file_size/1024/1024:.2f} MB)")
                    self.progress_var.set(0)
                    self.progress_label.config(text="0%")
                
                elif message_type == "file_chunk":
                    if self.receiving_file:
                        chunk_data = data.get("data", "")
                        chunk_id = data.get("chunk_id", -1)
                        is_last = data.get("is_last", False)
                        
                        # Store the chunk
                        self.file_chunks.append(base64.b64decode(chunk_data))
                        
                        # Update progress bar
                        received_size = sum(len(chunk) for chunk in self.file_chunks)
                        progress = min(100, (received_size / self.file_size) * 100)
                        self.progress_var.set(progress)
                        self.progress_label.config(text=f"{progress:.1f}%")
                        
                        # For large files, we don't want to log every chunk
                        if chunk_id % 10 == 0 or is_last:
                            self.log_message(f"Received chunk {chunk_id} - {received_size/1024/1024:.2f} MB / {self.file_size/1024/1024:.2f} MB")
                
                elif message_type == "file_transfer_complete":
                    if self.receiving_file:
                        self.receiving_file = False
                        folder_name = data.get("folder_name", "unknown")
                        self.log_message(f"File transfer complete for folder: {folder_name}")
                        self.save_received_file(folder_name)
                        self.progress_var.set(100)
                        self.progress_label.config(text="100%")
                        self.start_button.config(state=tk.NORMAL)
                        self.stop_button.config(state=tk.DISABLED)
                
                elif message_type == "error":
                    self.log_message(f"Error from server: {data.get('message', 'Unknown error')}")
                    self.start_button.config(state=tk.NORMAL)
                    self.stop_button.config(state=tk.DISABLED)
                
            except Exception as e:
                self.log_message(f"Error processing message: {e}")

        def on_error(ws, error):
            self.log_message(f"WebSocket error: {error}")

        def on_close(ws, close_status_code, close_msg):
            self.connected = False
            self.status_label.config(text="Disconnected", foreground="red")
            self.log_message(f"Disconnected from server: {close_msg}")
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            
            # Try to reconnect after a delay
            self.root.after(5000, self.connect_websocket)

        try:
            # Close existing connection if any
            if self.ws:
                self.ws.close()
            
            # Set up new connection
            self.log_message("Connecting to server...")
            websocket.enableTrace(False)
            self.ws = websocket.WebSocketApp(
                self.ws_url,
                on_open=on_open,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close
            )
            
            # Start WebSocket connection in a separate thread
            thread = threading.Thread(target=self.ws.run_forever)
            thread.daemon = True
            thread.start()
            
        except Exception as e:
            self.log_message(f"Connection error: {e}")

    def start_capture(self):
        """Send command to start capturing images"""
        if not self.connected:
            messagebox.showerror("Error", "Not connected to server")
            return
        
        folder_name = self.folder_name_var.get().strip()
        if not folder_name:
            folder_name = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.folder_name_var.set(folder_name)
        
        # Send start capture command
        try:
            self.ws.send(json.dumps({
                "type": "start_capture",
                "folder_name": folder_name
            }))
            self.log_message(f"Sent start capture command with folder name: {folder_name}")
        except Exception as e:
            self.log_message(f"Error sending start command: {e}")

    def stop_capture(self):
        """Send command to stop capturing and download images"""
        if not self.connected:
            messagebox.showerror("Error", "Not connected to server")
            return
        
        # Send stop capture command
        try:
            self.ws.send(json.dumps({
                "type": "stop_capture"
            }))
            self.log_message("Sent stop capture command")
        except Exception as e:
            self.log_message(f"Error sending stop command: {e}")

    def save_received_file(self, folder_name):
        """Save the received file chunks as a zip file and extract it"""
        try:
            # Ensure the save folder exists
            if not os.path.exists(self.save_folder):
                os.makedirs(self.save_folder)
            
            # Save the combined file chunks as a zip file
            zip_path = os.path.join(self.save_folder, f"{folder_name}.zip")
            with open(zip_path, 'wb') as f:
                for chunk in self.file_chunks:
                    f.write(chunk)
            
            self.log_message(f"Saved zip file to: {zip_path}")
            
            # Extract the zip file
            extract_folder = os.path.join(self.save_folder, folder_name)
            if not os.path.exists(extract_folder):
                os.makedirs(extract_folder)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_folder)
            
            self.log_message(f"Extracted images to folder: {extract_folder}")
            
            # Count the number of extracted files
            file_count = sum(len(files) for _, _, files in os.walk(extract_folder))
            self.log_message(f"Received {file_count} images")
            
            # Show a success message
            messagebox.showinfo("Download Complete", 
                               f"Successfully downloaded and extracted {file_count} images to:\n{extract_folder}")
            
        except Exception as e:
            self.log_message(f"Error saving received file: {e}")
            messagebox.showerror("Error", f"Failed to save or extract the received file: {e}")

def main():
    # Create and run the application
    root = tk.Tk()
    app = LaptopClientApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
