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

class SerpentMain(tk.Tk):
    def __init__(self, master=None):
        super().__init__()
        self.title("Serpent")

        self.WIDTH, self.HEIGHT = 1280, 960
        self.geometry(f"{self.WIDTH}x{self.HEIGHT}")
        self.notebook=ttk.Notebook(self)
        self.notebook.pack(fill="both",expand=True)
    
    def add_modules(self, modules):
        for module in modules:
            m = module(self.notebook)
            self.notebook.add(m, text=m.title)

def main():
    # test module
    print("serpent_gui.py")

if __name__ == "__main__":
    main()
