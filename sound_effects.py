from pynput import keyboard
import pygame
import sys

# 1. Initialize Pygame Mixer
pygame.mixer.init()

# 2. Load your sounds (ensure these files are in the same folder)
try:
    sound_a = pygame.mixer.Sound("/Users/tphan/Desktop/All stuff school/Cornell/Haptic Glove/matimassa-fx-scratch-02-379219.mp3")
    sound_b = pygame.mixer.Sound("/Users/tphan/Desktop/All stuff school/Cornell/Haptic Glove/waitwhatimsignedin-air-horn-273892.mp3")
except pygame.error as e:
    print(f"Could not load sounds: {e}")
    sys.exit()

print("--- System Active ---")
print("Press 'a' for Sound 1")
print("Press 'b' for Sound 2")
print("Press 'Esc' to exit")

# 3. Define what happens when keys are pressed
def on_press(key):
    try:
        # Check for alphanumeric keys
        if hasattr(key, 'char'):
            if key.char == 'a':
                sound_a.play()
                print("Played Sound 1")
            elif key.char == 'b':
                sound_b.play()
                print("Played Sound 2")
                
    except Exception as e:
        print(f"Error: {e}")

def on_release(key):
    # Stop the listener if Escape is pressed
    if key == keyboard.Key.esc:
        print("Exiting...")
        return False

# 4. Start the listener
with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
    listener.join()