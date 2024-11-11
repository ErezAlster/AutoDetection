
import threading
from PCA9685 import PCA9685
from systemd import journal
import supervision as sv

def log(message):
    journal.write(message)
    print(message)


log("joystick controller started")
pwm = PCA9685()
pwm.setPWMFreq(50)

currentMM = 5
currentYAngleView = 110
currentXAngleView = 70
imageWidth = 1280
imageHeight = 720
currentXAngle = 90
currentYAngle = 90
pwm.setRotationAngle(0, currentYAngle)


def trackCamera(bbox):
    global currentMM, currentXAngleView, imageWidth, imageHight, currentXAngle
    xmin, ymin, xmax, ymax = bbox[0], bbox[1], bbox[2], bbox[3]
    bbox_x_center = xmax - xmin/2
    
    mXAngleChange = 90 + (currentXAngleView/2)
    movetopixel = (imageWidth / 2) - bbox_x_center
    m = (imageWidth/2) / (mXAngleChange-90)

    print(movetopixel / m)
    currentXAngle = (movetopixel/m) + currentXAngle

    log(f'{currentXAngle}')

    if currentXAngle<0:
        currentXAngle = 0
    if currentXAngle>180:
        currentXAngle = 180
    pwm.setRotationAngle(0, currentXAngle)