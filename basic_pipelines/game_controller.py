from PCA9685 import PCA9685
from config import readGlobalConfiguration

class GameController:
    def __init__(self, identifier):
        self.identifier = identifier

        self.pwm = PCA9685()
        self.pwm.setPWMFreq(50)
        self.conf = readGlobalConfiguration()
        self.video_width = 1920
        self.video_height = 1080
        self.reset()

    def reset(self):
        self.currentXAngle = self.conf["initialXAxis"]
        self.currentYAngle = self.conf["initialYAxis"]

        self.setXaxis(self.currentYAngle)
        self.setYaxis(self.currentYAngle)

    def setXaxis(self, angle):
        conf = self.conf
        if(angle<conf["minXAxis"]):
            angle = conf["minXAxis"]
        elif (angle>conf["maxXAxis"]):
            angle = conf["maxXAxis"]

        self.currentXAngle = angle
        self.pwm.setRotationAngle(0, angle)

    def setYaxis(self, angle):
        conf = readGlobalConfiguration()

        if(angle<conf["minYAxis"]):
            angle = conf["minYAxis"]
        elif (angle>conf["maxYAxis"]):
            angle = conf["maxYAxis"]

        self.currentYAngle = angle
        self.pwm.setRotationAngle(1, angle)

    def handleServoMovment(centerPixel, axisPixels, angleView=53):
        mXAngleChange = 90 + (angleView/2)
        movetopixel =  centerPixel - (axisPixels / 2)
        m = (axisPixels/2) / (mXAngleChange-90)
        return movetopixel/(m*60)

    def track(self,bbox):
        #center camera to the ball or relevant object
        xmin, ymin, xmax, ymax = bbox[0], bbox[1], bbox[2], bbox[3]

        bbox_x_center = (xmax + xmin)/2
        currentXAngle -= self.handleServoMovment(centerPixel=bbox_x_center, axisPixels=self.video_width)
        self.setXaxis(currentXAngle)

        bbox_y_center = (ymax + ymin)/2
        currentYAngle += self.handleServoMovment(centerPixel=bbox_y_center, axisPixels=self.video_height)
        self.setYaxis(currentYAngle)