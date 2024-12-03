import requests


def report_status(key, value):
    try:
        headers = {
            'Content-Type': 'text/plain'
        }
        requests.put(f"http://localhost:7070/api/env/{key}", data=value, headers=headers)
    finally:
        pass