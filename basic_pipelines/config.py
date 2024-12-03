import yaml

def readGlobalConfiguration():
    filePath = f'/usr/local/etc/starium.yaml'
    with open(filePath, 'r') as f:
        return yaml.full_load(f)