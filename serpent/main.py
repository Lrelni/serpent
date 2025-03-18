import wx

import serpent_gui as srpt
import serpent_audio as srpt_audio
import settings

# Serpent Music Practice Tool

def main():
    print("Serpent v"+settings.version)
    app = wx.App()
    modules = [srpt.BackingTrack, srpt.SightReading]
    main_frame = srpt.SerpentFrame(None, title="Serpent")
    main_frame.add_modules(modules)
    app.MainLoop()

if __name__ == "__main__":
    main()
