c-venv:
	python -m venv ./.venv

venv: 
	source .venv/bin/activate

streamsds:
	ffmpeg -re -stream_loop -1 -i test4.mp4 -c:v libx264 -preset ultrafast -tune zerolatency -b:v 6000k -c:a aac -b:a 128k -f rtsp rtsp://192.168.68.142:8554/starium

run-test:
	python basic_pipelines/detection.py -i rtsp://192.168.68.142:8554/starium --hef-path resources/starium.hef -o rtsp://192.168.68.142:8554/hailo

run:
	python basic_pipelines/detection.py -i /dev/video10 --hef-path resources/starium.hef

run-rtsp:
	python basic_pipelines/detection.py -i /dev/video10 --hef-path resources/starium.hef -o rtsp

run-rpi:
	python basic_pipelines/detection.py -i rpi --hef-path resources/starium.hef -o rtsp

copyconf:
	sudo cp starium.yaml /usr/local/etc

copymediamtx:
	sudo cp ../starium-device/mediamtx.yml /usr/local/etc/mediamtx.yml

stream-video:
	sudo modprobe v4l2loopback devices=2 exclusive_caps=1,1 video_nr=10,11 card_label="Raw Video","Annotated Camera"
	rpicam-vid -t 0 --camera 0 --f`ramerate 30 --nopreview --codec yuv420 --width 1280 --height 720 --exposure sport --metering average --inline --listen -o - | \
	ffmpeg -f rawvideo -s:v 1280x720 -i pipe:0 -r 30 -preset ultrafast -tune zerolatency -f v4l2 /dev/video10
	
install:
	sudo apt-get install v4l2loopback-dkms
	sudo apt install gstreamer1.0-rtsp
	sudo apt-get install gstreamer1.0-plugins-ugly

inference-server:
	gunicorn --config gunicorn_config.py wsgi:app