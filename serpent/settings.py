import pyaudio #type: ignore

rate = 44100
format = pyaudio.paFloat32
frames_per_buffer = 256
a_freq = 440
sleep_delay = 3

if __name__ == "__main__":
    print("settings.py")
    print("\nNamespace: ")
    print(dir())
