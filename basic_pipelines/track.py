
import threading
from PCA9685 import PCA9685
import time
from systemd import journal
import supervision as sv

def log(message):
    journal.write(message)
    print(message)


log("joystick controller started")
pwm = PCA9685()
pwm.setPWMFreq(50)

currentMM = 5
currentXAngleView = 53
imageWidth = 1920
currentXAngle = 90
currentYAngle = 100
pwm.setRotationAngle(0, currentXAngle)
pwm.setRotationAngle(1, currentYAngle)


def trackCamera(bbox):
    global currentMM, currentXAngleView, imageWidth, currentXAngle,didit
    xmin, ymin, xmax, ymax = bbox[0], bbox[1], bbox[2], bbox[3]
    bbox_x_center = (xmax + xmin)/2
    
    mXAngleChange = 90 + (currentXAngleView/2)
    movetopixel =  bbox_x_center - (imageWidth / 2)
    m = (imageWidth/2) / (mXAngleChange-90)
    diff = movetopixel/(m*15)
    print(diff)
    if(abs(diff) > 0.2):
        prevXAngle = currentXAngle
        currentXAngle = currentXAngle - diff
        if currentXAngle<0:
            currentXAngle = 0
        elif currentXAngle>180:
            currentXAngle = 180
    pwm.setRotationAngle(0, currentXAngle)



def doit():
    while True:
        pwm.setRotationAngle(0, currentXAngle)

#hread = threading.Thread(target=doit)
#thread.start()