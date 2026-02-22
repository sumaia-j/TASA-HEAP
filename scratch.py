from pynput import keyboard
import rtmidi
import threading

MIDI_PORT_NAME = "WearableTest"

VOL_CC = 7
JOG_CC = 16
SCRATCH_NOTE = 60
MIDI_CH = 0

VOL_STEP = 3
JOG_TICK = 6
JOG_INTERVAL = 0.05  # send a tick every 50ms while key held

KEY_VOL_UP = keyboard.KeyCode.from_char('=')
KEY_VOL_DOWN = keyboard.KeyCode.from_char('-')
KEY_JOG_FWD = keyboard.KeyCode.from_char(']')
KEY_JOG_BACK = keyboard.KeyCode.from_char('[')
# added
SAMPLE_NOTE = 65   # used ONLY to trigger sampler
KEY_SAMPLE = keyboard.KeyCode.from_char('p')   # press P to play sample

midi = rtmidi.MidiOut()
ports = midi.get_ports()
port_index = next((i for i, name in enumerate(ports) if MIDI_PORT_NAME in name), None)
if port_index is None:
    raise RuntimeError(f"Could not find MIDI port containing '{MIDI_PORT_NAME}'. Available: {ports}")
midi.open_port(port_index)

volume = 80
jog_direction = 0       # +1, -1, or 0
jog_thread = None
jog_lock = threading.Lock()

def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v

def send_cc(cc, value):
    midi.send_message([0xB0 + MIDI_CH, cc & 0x7F, value & 0x7F])

def send_note_on():
    midi.send_message([0x90 + MIDI_CH, SCRATCH_NOTE & 0x7F, 127])
# added for sample
def send_sample():
    midi.send_message([0x90 + MIDI_CH, SAMPLE_NOTE, 127])
    midi.send_message([0x90 + MIDI_CH, SAMPLE_NOTE, 0])

def send_note_off():
    midi.send_message([0x80 + MIDI_CH, SCRATCH_NOTE & 0x7F, 0])

def jog_loop():
    """Continuously send jog ticks while a jog key is held."""
    global jog_direction
    while True:
        with jog_lock:
            d = jog_direction
        if d == 0:
            break
        val = clamp(64 + JOG_TICK * d, 1, 127)
        send_cc(JOG_CC, val)
        threading.Event().wait(JOG_INTERVAL)

def start_jog(direction):
    global jog_direction, jog_thread
    with jog_lock:
        already_running = jog_direction != 0
        jog_direction = direction
    if not already_running:
        send_note_on()
        jog_thread = threading.Thread(target=jog_loop, daemon=True)
        jog_thread.start()

def stop_jog():
    global jog_direction
    with jog_lock:
        jog_direction = 0
    send_note_off()

def on_press(key):
    global volume

    if key == KEY_VOL_UP:
        volume = clamp(volume + VOL_STEP, 0, 127)
        send_cc(VOL_CC, volume)
        print(f"VOL {volume}")

    elif key == KEY_VOL_DOWN:
        volume = clamp(volume - VOL_STEP, 0, 127)
        send_cc(VOL_CC, volume)
        print(f"VOL {volume}")

    elif key == KEY_JOG_FWD:
        start_jog(+1)

    elif key == KEY_JOG_BACK:
        start_jog(-1)
    # added
    elif key == KEY_SAMPLE:
        send_sample()
        print("SAMPLE TRIGGER")

def on_release(key):
    if key in (KEY_JOG_FWD, KEY_JOG_BACK):
        stop_jog()
    if key == keyboard.Key.esc:
        return False

print("Keys: =  -  [  ]  \\  P=sample   (Esc quits)")
with keyboard.Listener(on_press=on_press, on_release=on_release) as kl:
    kl.join()