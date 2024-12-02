To host a FastAPI app on a DigitalOcean Droplet without Docker, follow these steps. The setup will include creating a virtual environment, installing the required packages, configuring a process manager like **Gunicorn** with **Uvicorn** worker, and setting up a reverse proxy with **Nginx**.

---

### 1. **Update and Install Dependencies**
Run these commands to update your server and install required packages:
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3-pip python3-venv nginx -y
```

---

### 2. **Upload or Clone Your FastAPI App**
- Use **`scp`** to upload your FastAPI app to the server:
  ```bash
  scp -r /path/to/your/fastapi-app username@your_server_ip:/path/to/server
  ```
- Alternatively, SSH into the server and clone your Git repository:
  ```bash
  git clone https://github.com/your-repo/fastapi-app.git /path/to/server/fastapi-app
  ```

---

### 3. **Set Up a Python Virtual Environment**
```bash
cd /path/to/server/fastapi-app
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

---

### 4. **Install and Configure Gunicorn**
Install Gunicorn with Uvicorn worker:
```bash
pip install gunicorn uvicorn
```

Create a **Gunicorn configuration** file:
```bash
nano /path/to/server/fastapi-app/gunicorn_config.py
```
Example `gunicorn_config.py`:
```python
bind = "0.0.0.0:8000"
workers = 2
worker_class = "uvicorn.workers.UvicornWorker"
```

Test the app locally:
```bash
gunicorn -c gunicorn_config.py main:app
```
Replace `main:app` with the module and app instance name in your FastAPI project.

---

### 5. **Set Up Systemd Service**
Create a service file to manage the app:
```bash
sudo nano /etc/systemd/system/fastapi.service
```

Example service file:
```ini
[Unit]
Description=Gunicorn instance to serve FastAPI
After=network.target

[Service]
User=your_username
Group=www-data
WorkingDirectory=/path/to/server/fastapi-app
Environment="PATH=/path/to/server/fastapi-app/venv/bin"
ExecStart=/path/to/server/fastapi-app/venv/bin/gunicorn -c /path/to/server/fastapi-app/gunicorn_config.py main:app

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable fastapi.service
sudo systemctl start fastapi.service
sudo systemctl status fastapi.service
```

---

### 6. **Set Up Nginx Reverse Proxy**
Create an Nginx configuration file:
```bash
sudo nano /etc/nginx/sites-available/fastapi
```

Example Nginx configuration:
```nginx
server {
    listen 80;
    server_name your_domain_or_IP;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable the configuration and restart Nginx:
```bash
sudo ln -s /etc/nginx/sites-available/fastapi /etc/nginx/sites-enabled
sudo nginx -t
sudo systemctl restart nginx
```

---

### 7. **Secure with HTTPS (Optional but Recommended)**
Install Certbot:
```bash
sudo apt install certbot python3-certbot-nginx -y
```

Generate SSL certificates:
```bash
sudo certbot --nginx -d your_domain_or_IP
```

Verify the renewal process:
```bash
sudo certbot renew --dry-run
```

---

### 8. **Test Your Setup**
Visit your server's public IP or domain name in a browser to verify the app is running:
```bash
http://your_domain_or_IP
```

---

### Summary:
- FastAPI app is served via Gunicorn with Uvicorn workers.
- Nginx acts as a reverse proxy.
- Optional HTTPS setup with Certbot.

---
