import tkinter as tk
from tkinter import ttk

import serpent_gui as srpt
import serpent_audio as srpt_audio
import settings

# Serpent Music Practice Tool

def main():
    print("Serpent v"+settings.version)
    modules = [srpt.BackingTrack, srpt.SightReading]
    window = srpt.SerpentMain()
    window.add_modules(modules)
    window.mainloop()

if __name__ == "__main__":
    main()
