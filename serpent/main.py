import tkinter as tk
from tkinter import ttk

import serpent_gui as srpt

def main():
    print("Serpent v0.1")
    modules = [srpt.BackingTrack, srpt.SightReading]
    window = srpt.SerpentMain()
    window.add_modules(modules)
    window.mainloop()

if __name__ == "__main__":
    main()
