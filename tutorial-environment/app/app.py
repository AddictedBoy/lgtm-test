# Tutorial App - Python version mimicking Grafana TNS app
# Generates metrics and logs for Grafana tutorials

import random
import time
import os
import threading
import logging
from flask import Flask, render_template_string, request, jsonify
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from pythonjsonlogger import jsonlogger

app = Flask(__name__)

SERVICE_NAME = os.getenv("SERVICE_NAME", "tns-app")
AUTO_GENERATE = os.getenv("AUTO_GENERATE", "true").lower() == "true"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(SERVICE_NAME)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter(fmt='%(asctime)s %(levelname)s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

requests_total = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
request_duration = Histogram('http_request_duration_seconds', 'Request duration')
active_users = Gauge('app_active_users', 'Number of active users')
votes_total = Counter('votes_total', 'Total votes', ['candidate'])
posts_total = Counter('posts_total', 'Total posts')

links_data = [
    {"id": 1, "title": "Grafana", "url": "https://grafana.com", "points": random.randint(100, 500)},
    {"id": 2, "title": "Prometheus", "url": "https://prometheus.io", "points": random.randint(100, 500)},
    {"id": 3, "title": "Loki", "url": "https://grafana.com/loki", "points": random.randint(100, 500)},
    {"id": 4, "title": "Tempo", "url": "https://grafana.com/tempo", "points": random.randint(100, 500)},
    {"id": 5, "title": "Mimir", "url": "https://grafana.com/mimir", "points": random.randint(100, 500)},
]

html_template = """
<!DOCTYPE html>
<html>
<head><title>Vote App</title></head>
<body>
<h1>Vote for your favorite!</h1>
<ul>
{% for link in links %}
<li>{{ link.title }} - {{ link.points }} votes <a href="/vote?id={{ link.id }}">Vote</a></li>
{% endfor %}
</ul>
<h2>Add a new link</h2>
<form action="/post" method="post">
  Title: <input type="text" name="title"><br>
  URL: <input type="text" name="url"><br>
  <input type="submit" value="Submit">
</form>
<p>App ID: {{ app_id }}</p>
</body>
</html>
"""

def auto_generate_traffic():
    while True:
        try:
            action = random.choice(["view", "vote", "post"])
            
            if action == "view":
                requests_total.labels(method="GET", endpoint="/", status="200").inc()
                active_users.set(random.randint(50, 200))
                logger.info("Page viewed", extra={"action": "view", "endpoint": "/"})
                
            elif action == "vote":
                link_id = random.randint(1, 5)
                votes_total.labels(candidate=f"candidate_{link_id}").inc()
                requests_total.labels(method="GET", endpoint="/vote", status="302").inc()
                logger.info("Vote cast", extra={"action": "vote", "candidate": link_id})
                
                global links_data
                for link in links_data:
                    if link["id"] == link_id:
                        link["points"] += 1
                        
            elif action == "post":
                posts_total.inc()
                requests_total.labels(method="POST", endpoint="/post", status="302").inc()
                logger.info("Post created", extra={"action": "post"})
            
            time.sleep(random.uniform(2, 8))
        except Exception as e:
            logger.error(f"Error in auto generator: {e}")

if AUTO_GENERATE:
    thread = threading.Thread(target=auto_generate_traffic, daemon=True)
    thread.start()

@app.route("/")
def index():
    with request_duration.time():
        time.sleep(random.uniform(0.01, 0.1))
    requests_total.labels(method="GET", endpoint="/", status="200").inc()
    active_users.set(random.randint(50, 200))
    
    logger.info("Page viewed", extra={"endpoint": "/"})
    return render_template_string(html_template, links=links_data, app_id=os.environ.get('HOSTNAME', 'local'))

@app.route("/post", methods=["POST"])
def post():
    title = request.form.get("title", "New Link")
    url = request.form.get("url", "https://example.com")
    
    global links_data
    new_id = max(l["id"] for l in links_data) + 1
    links_data.append({
        "id": new_id,
        "title": title,
        "url": url,
        "points": 0
    })
    
    posts_total.inc()
    requests_total.labels(method="POST", endpoint="/post", status="302").inc()
    logger.info("Post created", extra={"title": title, "url": url})
    
    return "", 302, {"Location": "/"}

@app.route("/vote")
def vote():
    link_id = int(request.args.get("id", 1))
    
    votes_total.labels(candidate=f"candidate_{link_id}").inc()
    requests_total.labels(method="GET", endpoint="/vote", status="302").inc()
    
    global links_data
    for link in links_data:
        if link["id"] == link_id:
            link["points"] += 1
            logger.info("Vote cast", extra={"candidate": link_id, "title": link["title"]})
            break
    
    return "", 302, {"Location": "/"}

@app.route("/metrics")
def metrics():
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

@app.route("/health")
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    print(f"Starting TNS app on port 8081")
    print(f"Auto-generate traffic: {AUTO_GENERATE}")
    app.run(host="0.0.0.0", port=8081)
