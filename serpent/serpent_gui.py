import tkinter as tk
from tkinter import ttk
from abc import ABC, abstractmethod

import pyaudio 
import numpy as np 

import serpent_audio as srpt_audio
import settings

class BackingTrack(ttk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.title = "Backing Track"

        self.osc = srpt_audio.SineOscillator()
        self.player = srpt_audio.Player(self.osc, settings.rate, settings.frames_per_buffer)

        self.button = ttk.Button(self, command=self.button_callback, text="Testing Button")
        self.button.pack()

    def button_callback(self):
        self.osc.amp = 1 - self.osc.amp

class SightReading(ttk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.title = "Sight Reading"

class AboutBox(tk.Toplevel):
    def __init__(self, master=None):
        super().__init__(master)
        self.wm_title("About Serpent")
        self.WIDTH, self.HEIGHT = 600, 400
        self.geometry(f"{self.WIDTH}x{self.HEIGHT}")

        tk.Label(self, text="Serpent v"+settings.version).pack()

class SerpentMain(tk.Tk):
    def __init__(self, master=None):
        super().__init__()
        self.title("Serpent")

        self.WIDTH, self.HEIGHT = 1280, 960
        self.geometry(f"{self.WIDTH}x{self.HEIGHT}")

        self.menubar = tk.Menu(self)
        self.config(menu=self.menubar)

        self.menubar.add_command(label="About", command=self.open_about_box)

        self.notebook=ttk.Notebook(self)
        self.notebook.pack(fill="both",expand=True)
    
    def open_about_box(self):
        about_box = AboutBox(self)
        
    def add_modules(self, modules):
        for module in modules:
            m = module(self.notebook)
            self.notebook.add(m, text=m.title)

def main():
    # test module
    print("serpent_gui.py")

if __name__ == "__main__":
    main()
