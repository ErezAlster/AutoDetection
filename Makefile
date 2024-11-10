c-venv:
	python -m venv ./.venv

venv: 
	source .venv/bin/activate

run:
	python basic_pipelines/detection.py -i rpi --hef-path resources/yolov8s_h8l.hef

stream-video:
	sudo modprobe v4l2loopback devices=2 exclusive_caps=1,1 video_nr=10,11 card_label="Raw Video","Annotated Camera"
	ffmpeg -i resources/test.mp4 -r 30 -preset ultrafast -tune zerolatency -vf format=yuv420p -f v4l2 /dev/video10
	
install:
	sudo apt-get install v4l2loopback-dkms

inference-server:
	gunicorn --config gunicorn_config.py wsgi:app