
from multiprocessing import Process
import multiprocessing as mp 
import threading
import time
from PCA9685 import PCA9685
from systemd import journal
import supervision as sv
import pyjoystick
from pyjoystick.sdl2 import Key, Joystick, run_event_loop
import signal
from multiprocessing.connection import Listener

def log(message):
    journal.write(message)
    print(message)


log("joystick controller started")
pwm = PCA9685()
pwm.setPWMFreq(50)

currentMM = 5
currentXAngleView = 53
currentYAngleView = 70
imageWidth = 1920
imageHeight = 1080
currentXAngle = 91
panFactor = 0
manualX = False
manualY = False
tiltFactor = 0
currentYAngle = 90
pwm.setRotationAngle(0, currentXAngle)
pwm.setRotationAngle(1, currentYAngle)


def handleServoMovment(centerPixel, axisPixels, angleView):
    mXAngleChange = 90 + (angleView/2)
    movetopixel =  centerPixel - (axisPixels / 2)
    m = (imageWidth/2) / (mXAngleChange-90)
    return movetopixel/(m*15)

def setXaxis(angle):

    if(angle<0):
        angle = 0
    elif (angle>180):
        angle = 180

    pwm.setRotationAngle(0, angle)

def setYaxis(angle):
    if(angle<0):
        angle = 0
    elif (angle>180):
        angle = 180
    
    pwm.setRotationAngle(1, angle)

def trackCamera(bbox):
    global currentMM, currentXAngleView, imageWidth, imageHeight, currentXAngle,currentYAngle
    xmin, ymin, xmax, ymax = bbox[0], bbox[1], bbox[2], bbox[3]
    if(not manualX):
        #handle x axix, make the ball in the center of the frame
        bbox_x_center = (xmax + xmin)/2
        currentXAngle -= handleServoMovment(centerPixel=bbox_x_center, axisPixels=imageWidth, angleView=currentXAngleView)
        setXaxis(currentXAngle)

    if(not manualY):
        bbox_y_center = (ymax + ymin)/2
        currentYAngle += handleServoMovment(centerPixel=bbox_y_center, axisPixels=imageHeight, angleView=currentYAngleView)
        setYaxis(currentYAngle)

def key_received(key):
    global panFactor, tiltFactor, manualX, manualY
    match key:
        case "Axis 0":
            panFactor = key.value
        case "-Axis 0":
            panFactor = key.value
        case "-Axis 1":
            tiltFactor = key.value
        case "Axis 1":
            tiltFactor = key.value
        case "Button 12":
            if(key.value == 1):
                manualX = not manualX
                manualY = not manualY
        case "Button 5":
            if(key.value == 1):
                manualX = not manualX
                manualY = not manualY

def signal_term_handler(sigNum, frame):
    exit(0)
signal.signal(signal.SIGTERM, signal_term_handler)


mngr = pyjoystick.ThreadEventManager(event_loop=run_event_loop, handle_key_event=key_received)
mngr.start()

def joystick_worker():
    global currentXAngle,currentYAngle, panFactor, tiltFactor
    while (True):
        if(manualX):
            factor = (pow(abs(panFactor), 2)) / 7
            if(panFactor < 0):
                factor = factor * -1
            currentXAngle = currentXAngle - factor
            setXaxis(currentXAngle)

        if(manualX):
            factor = (pow(abs(tiltFactor), 2)) / 20
            if(tiltFactor < 0):
                factor = factor * -1
            currentYAngle = currentYAngle + factor
            setYaxis(currentYAngle)


tolat = mp.Queue() 

#p = Process(target=joystick_worker)
#p.start()