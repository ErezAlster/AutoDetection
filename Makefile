run:
	python basic_pipelines/detection.py -i /dev/video10 --network yolov8s

run-mp4:
	python basic_pipelines/detection.py -i football.mp4

inference-server:
	gunicorn --config gunicorn_config.py wsgi:app

train: clear-data find

clear-data:
	cd data;find . -name \*.jpg -type f -print0  | xargs -0 rm -f

find:
	python basic_pipelines/detection.py -i ~/data/raw/1.mp4 --network yolov8s