c-venv:
	python -m venv ./.venv

venv: 
	source .venv/bin/activate

run:
	python basic_pipelines/detection.py -i /dev/video10 --hef-path resources/yolov8s.hef

stream-video:
	sudo modprobe v4l2loopback devices=2 exclusive_caps=1,1 video_nr=10,11 card_label="Raw Video","Annotated Camera"
	rpicam-vid -t 0 --camera 0 --framerate 30 --nopreview --codec yuv420 --width 1280 --height 720 --exposure sport --metering average --inline --listen -o - | \
	ffmpeg -f rawvideo -s:v 1280x720 -i pipe:0 -r 30 -preset ultrafast -tune zerolatency -f v4l2 /dev/video10
	
install:
	sudo apt-get install v4l2loopback-dkms

inference-server:
	gunicorn --config gunicorn_config.py wsgi:app