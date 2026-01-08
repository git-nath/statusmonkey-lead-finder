import os
import sys
import webbrowser
import threading
from flask import Flask
# Import your app (adjust path)
from app import app  # or however your main app is imported

def open_browser():
    webbrowser.open('http://127.0.0.1:5000')

if __name__ == '__main__':
    # Start Flask in thread
    threading.Thread(target=lambda: app.run(host='127.0.0.1', port=5000, debug=False)).start()
    
    # Open browser after 1 second
    threading.Timer(1.0, open_browser).start()
    
    # Keep running
    input("StatusMonkey is running! Close this window to stop.\nPress Enter to exit...")
