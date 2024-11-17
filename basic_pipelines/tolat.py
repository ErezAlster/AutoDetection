from pyjoystick.sdl2 import Key, Joystick, run_event_loop
from PCA9685 import PCA9685
import signal
import pyjoystick
from systemd import journal

from datetime import datetime


def log(message):
    journal.write(message)
    print(message)


log("joystick controller started")
pwm = PCA9685()
pwm.setPWMFreq(50)
val = {"pan" : 90.0, "panFactor": 0, "tilt": 45.0, "tiltFactor": 0, "panRatio": 3, "tiltRatio": 3}

def signal_term_handler(sigNum, frame):
    exit(0)

def reset():
    log("reset camera position")
    val["pan"] = 90.0
    val["tilt"] = 90.0

def pan():
    factor = (pow(abs(val["panFactor"]), 2)) / 7
    if(val["panFactor"] < 0):
        factor = factor * -1
    val["pan"] = val["pan"] - factor
    if(val["pan"] > 180):
        val["pan"]=180
    if(val["pan"] < 0):
        val["pan"]=0
    #pwm.setRotationAngle(0, val["pan"])

def tilt():
    factor = (pow(abs(val["tiltFactor"]), 2)) / 20
    if(val["tiltFactor"] < 0):
        factor = factor * -1
    val["tilt"] = val["tilt"] + factor
    if(val["tilt"] > 180):
        val["tilt"]=180
    if(val["tilt"] < 0):
        val["tilt"]=0
    pwm.setRotationAngle(1, val["tilt"])
    
'''
      "CREATE TABLE playtypes(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, customType INTEGER DEFAULT 1)",
      "INSERT INTO playtypes (name, customType) values ('half_start', 0)",
      "INSERT INTO playtypes (name, customType) values ('goalie_kick', 0)",
      "INSERT INTO playtypes (name, customType) values ('freekick', 0)",
      "INSERT INTO playtypes (name, customType) values ('shot_on_goal', 0)",
      "INSERT INTO playtypes (name, customType) values ('goal', 0)",
      "INSERT INTO playtypes (name, customType) values ('kickoff', 0)",
      "INSERT INTO playtypes (name, customType) values ('corner', 0)",
      "INSERT INTO playtypes (name, customType) values ('half_end', 0)",
      "INSERT INTO playtypes (name, customType) values ('penalty_kick', 0)",

'''

def write_event(key):
    if(key.value ==1):
        eventName = None
        match key.number:
            case 0: #A
                eventName = "goal"
            case 1: #B
                eventName = "shot_on_goal"
            case 3: #Y
                eventName = "freekick"
            case 2: #X
                eventName = "corner"
            case 6: #hamburger
                eventName = "foul"
            case 15: #small arrow up
                eventName = "penalty_kick"
            case 9: #left, top back
                eventName = "half_start"
            case 10: #right, top back
                eventName = "half_end"
        with open("/home/erez/recordings/metadata/currentmatch", 'r') as file:
            # Read the content of the file
            currentMatchId = file.read()
   
        with open(f"/home/erez/recordings/metadata/{currentMatchId}_events.txt", "a") as events_file:
            now = datetime.now()
            events_file.write(f'{now.strftime("%Y-%m-%dT%H:%M:%SZ")}\t{eventName}\n')

def key_received(key):
    if key.keytype == Key.BUTTON:
        write_event(key)
    
    match key:
        case "Axis 0":
            val["panFactor"] = key.value
        case "-Axis 0":
            val["panFactor"] = key.value
        case "-Axis 1":
            val["tiltFactor"] = key.value
        case "Axis 1":
            val["tiltFactor"] = key.value
        case "Button 5":
            if(key.value ==1):
                reset()
        #up to increase tilt moment
        case "Button 11":
            if(key.value ==1):
                val["tiltRatio"] = val["tiltRatio"] + 0.1
        #Down to decrease tilt moment
        case "Button 12":
            if(key.value ==1):
                val["tiltRatio"] = val["tiltRatio"] - 0.1
        #Right to increase pan moment
        case "Button 14":
            if(key.value ==1):
                val["panRatio"] = val["panRatio"] + 0.1
        #Left to decrease pan moment
        case "Button 13":
            if(key.value ==1):
                val["panRatio"] = val["panRatio"] - 0.1

reset()
signal.signal(signal.SIGTERM, signal_term_handler)


mngr = pyjoystick.ThreadEventManager(event_loop=run_event_loop, handle_key_event=key_received)
mngr.start()

while (True):
    pan()
    tilt()
