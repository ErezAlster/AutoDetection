sudo tee /etc/systemd/system/inference.service >/dev/null << EOF
[Unit]
After=multi-user.target
[Service]
Type=idle
ExecStart=/bin/bash -c 'cd /home/erez/git/AutoDetection; . setup_env.sh; make inference-server'
Restart=Always
[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable inference
sudo systemctl restart inference