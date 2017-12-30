import rtmidi
import serial
import curses

# set up curses, for async keyboard input
stdscr = curses.initscr()
curses.noecho()
stdscr.nodelay(1) # set getch() non-blocking

midiin = rtmidi.RtMidiIn()

curses_window = None

def p(message):
    global curses_window
    curses_window.addstr(message + "\n")
    curses_window.refresh()

def print_message(midi):
    if midi.isNoteOn():
        p('ON: ' + str(midi.getMidiNoteName(midi.getNoteNumber())) + " " + str(midi.getVelocity()))
    elif midi.isNoteOff():
        p('OFF:' + str(midi.getMidiNoteName(midi.getNoteNumber())))
    elif midi.isController():
        p('CONTROLLER' + str(midi.getControllerNumber()) + " " + str(midi.getControllerValue()))

ser = serial.Serial('/dev/tty.usbmodem1411', 57600)

num_pixels = 64
note_bitmap = [0] * num_pixels

ports = range(midiin.getPortCount())
if not ports:
    print('NO MIDI INPUT PORTS!')

def main_loop(window):
    global curses_window
    global note_bitmap
    global num_pixels
    curses_window = window
    curses_window.scrollok(1)

    for i in ports:
        p(midiin.getPortName(i))
    p("Opening port 0!") 
    midiin.openPort(0)


    while True:
        # process any midi input
        m = midiin.getMessage(0) # some timeout in ms
        if m:
            if m.isNoteOn():
                note_bitmap[m.getNoteNumber() - 36] = 1
                send_notes_to_arduino() # TODO: do this on an explicit framerate instead
            elif m.isNoteOff():
                note_bitmap[m.getNoteNumber() - 36] = 0
                send_notes_to_arduino()
            print_message(m)
            

        # check for any keyboard input
        character = stdscr.getch()
        if character == ord('o') and not ser.is_open:
            p("Opening serial!")
            ser.open()
        if character == ord('c') and ser.is_open:
            p("Closing serial!")
            ser.close()

def send_notes_to_arduino():
    global num_pixels
    global note_bitmap

    p("Writing to Arduino: " + str(note_bitmap))
    ser.write(bytearray(note_bitmap))
    response_string = ser.readline() # does this block?
    p("received byte back from Arduino: " + response_string)




curses.wrapper(main_loop)
