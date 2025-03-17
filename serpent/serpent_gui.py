import tkinter as tk
from tkinter import ttk
from tkinter import font
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
        self._time_signature = (3,4)

        self.time_signature_font = font.Font(family="Helvetica", size=48, weight="bold")
        self.time_signature_labels = [ttk.Label(self, text=str(self.time_signature[0]), font=self.time_signature_font), 
                                      ttk.Label(self, text=str(self.time_signature[1]), font=self.time_signature_font)]
        for label in self.time_signature_labels:
            label.pack()
    
    @property
    def time_signature(self):
        return self._time_signature
    
    @time_signature.setter
    def time_signature(self, val):
        self.time_signature = val
        self.time_signature_labels[0].config(text=str(self.time_signature[0]))
        self.time_signature_labels[1].config(text=str(self.time_signature[1]))
        
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

        self.notebook_style = ttk.Style(self)
        self.notebook_style.configure("TNotebook", tabposition="s")

        self.notebook=ttk.Notebook(self, style="TNotebook")
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
