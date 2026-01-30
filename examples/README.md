


`sudo nano /etc/logrotate.d/ssd1305_stats`

```
/var/log/ssd1305_stats.log {
    daily
    missingok
    rotate 7
    compress
    notifempty
    create 0640 root root
}
```


`sudo nano /etc/systemd/system/ssd1305_stats.service`

```
[Unit]
Description=SSD1305 OLED Status Display
After=multi-user.target

[Service]
Type=simple
User=root
ExecStart=/home/user/env/bin/python3 /home/user/Dokumente/git/Adafruit_CircuitPython_SSD1305/examples/ssd1305_stats.py
Restart=on-failure
StandardOutput=append:/var/log/ssd1305_stats.log
StandardError=append:/var/log/ssd1305_stats.log

[Install]
WantedBy=multi-user.target
```

Test
Reload the daemon:
`sudo systemctl daemon-reload`

Enable the service (this ensures it runs on boot):
`sudo systemctl enable ssd1305_stats.service`

Start the service now (to test it):
`sudo systemctl start ssd1305_stats.service`
