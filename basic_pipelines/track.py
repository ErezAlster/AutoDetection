
from PCA9685 import PCA9685
import signal
from systemd import journal
import threading

def log(message):
    journal.write(message)
    print(message)


log("joystick controller started")
pwm = PCA9685()
pwm.setPWMFreq(50)
val = {"pan" : 90.0, "panFactor": 0, "panInterval": None, "tilt": 90.0, "tiltFactor": 0, "tiltInterval": None, "panRatio": 0.2, "tiltRatio": 0.2}

def resetCamera():
    log("reset camera position")
    val["pan"] = 90.0
    val["tilt"] = 90.0
    if(val["panInterval"] != None):
        val["panInterval"].cancel()
        val["panInterval"] = None
    if(val["tiltInterval"] != None):
        val["tiltInterval"].cancel()
        val["tiltInterval"] = None
    pwm.setRotationAngle(1, val["tilt"])
    pwm.setRotationAngle(0, val["pan"])

def pan():
    factor = (pow(abs(val["panFactor"]), 2)) / 10
    if(val["panFactor"] < 0):
        factor = factor * -1
    val["pan"] = val["pan"] - factor
    if(val["pan"] > 180):
        val["pan"]=180
    if(val["pan"] < 0):
        val["pan"]=0
    pwm.setRotationAngle(1, val["pan"])

def tilt():
    factor = (pow(abs(val["tiltFactor"]), 2)) / 20
    if(val["tiltFactor"] < 0):
        factor = factor * -1
    val["tilt"] = val["tilt"] + factor
    if(val["tilt"] > 180):
        val["tilt"]=180
    if(val["tilt"] < 0):
        val["tilt"]=0
    pwm.setRotationAngle(0, val["tilt"])

def doit(): 
    while (True):
        pan()
        tilt()

t1 = threading.Thread(target=doit)
t1.start()

def stopCamera():
    val["panFactor"] = 0
    val["tiltFactor"] = 0

def trackCamera(bbox):
    centerX = bbox.xmin() + (bbox.width() / 2) 
    centerY = bbox.ymin() + (bbox.height() / 2)

    val["panFactor"] = centerX/-0.5
    #val["tiltFactor"] = centerY/-0.5

    log(f'{centerX} {val["panFactor"]}')
    return