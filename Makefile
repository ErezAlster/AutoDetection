run:
	python basic_pipelines/detection.py -i /dev/video10 --network yolov8s

inference-server:
	gunicorn --config gunicorn_config.py wsgi:app