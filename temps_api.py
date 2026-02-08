from flask import Flask
import subprocess
import re
from collections import deque
from datetime import datetime

app = Flask(__name__)

# Keep last 60 samples (~5 minutes @ 5s refresh)
history_maxlen = 60
cpu_temp_history = deque(maxlen=history_maxlen)
gpu_temp_history = deque(maxlen=history_maxlen)
time_labels = deque(maxlen=history_maxlen)

# ---------- CPU TEMP ----------
def get_cpu_temp():
    out = subprocess.getoutput("sensors")
    match = re.search(r"Package id 0:\s+\+?([\d\.]+)", out)
    return match.group(1) if match else "0"

# ---------- CPU USAGE (Your working version) ----------
def get_cpu_usage():
    out = subprocess.getoutput("top -bn1 | grep 'Cpu(s)'")
    match = re.search(r"(\d+\.\d+)\s*id", out)
    if match:
        idle = float(match.group(1))
        return round(100 - idle, 1)
    return "0"

# ---------- GPU (Your working version) ----------
def get_gpu_stats():
    try:
        out = subprocess.getoutput(
            "nvidia-smi --query-gpu=temperature.gpu,utilization.gpu --format=csv,noheader,nounits"
        )
        temp, usage = out.split(",")
        return temp.strip(), usage.strip()
    except:
        return "0", "0"

@app.route("/")
def index():
    c_temp = get_cpu_temp()
    c_usage = get_cpu_usage()
    g_temp, g_usage = get_gpu_stats()
    
    # Get current time for labels
    now = datetime.now().strftime("%H:%M:%S")

    # Store in history
    try:
        cpu_temp_history.append(float(c_temp))
        gpu_temp_history.append(float(g_temp))
        time_labels.append(now)
    except:
        pass

    return f"""
<html>
<head>
    <meta http-equiv="refresh" content="5">
    <style>
        body {{
            background: transparent;
            color: #eee;
            font-family: system-ui, -apple-system, sans-serif;
            margin: 0;
            padding: 15px;
            overflow: hidden;
        }}

        .grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            text-align: center;
            margin-bottom: 10px;
        }}

        .title {{
            font-size: 14px;
            opacity: 0.7;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}

        .temp {{
            font-size: 36px; /* Bigger, clearer numbers */
            font-weight: 800;
            margin-top: 2px;
            line-height: 1;
        }}

        .usage {{
            font-size: 15px;
            opacity: 0.6;
            margin-top: 4px;
        }}

        .chart-container {{
            position: relative;
            height: 200px;
            width: 100%;
            margin-top: 10px;
        }}

        .footer-time {{
            text-align: center;
            font-size: 12px;
            color: #666;
            margin-top: 10px;
            font-family: monospace;
        }}
    </style>
</head>
<body>

<div class="grid">
    <div>
        <div class="title">CPU</div>
        <div class="temp" style="color: #00bfff;">{c_temp}°C</div>
        <div class="usage">{c_usage}% load</div>
    </div>
    <div>
        <div class="title">GPU</div>
        <div class="temp" style="color: #00ff66;">{g_temp}°C</div>
        <div class="usage">{g_usage}% load</div>
    </div>
</div>

<div class="chart-container">
    <canvas id="chart"></canvas>
</div>

<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
const ctx = document.getElementById('chart').getContext('2d');

new Chart(ctx, {{
    type: 'line',
    data: {{
        labels: {list(time_labels)},
        datasets: [
            {{
                label: 'CPU Temp',
                data: {list(cpu_temp_history)},
                borderColor: '#00bfff',
                backgroundColor: 'rgba(0, 191, 255, 0.1)',
                borderWidth: 3,
                tension: 0.4,
                pointRadius: 0,
                pointHoverRadius: 6,
                fill: true
            }},
            {{
                label: 'GPU Temp',
                data: {list(gpu_temp_history)},
                borderColor: '#00ff66',
                backgroundColor: 'rgba(0, 255, 102, 0.1)',
                borderWidth: 3,
                tension: 0.4,
                pointRadius: 0,
                pointHoverRadius: 6,
                fill: true
            }}
        ]
    }},
    options: {{
        responsive: true,
        maintainAspectRatio: false,
        interaction: {{
            mode: 'index',
            intersect: false,
        }},
        plugins: {{
            legend: {{ display: false }},
            tooltip: {{
                enabled: true,
                backgroundColor: 'rgba(0, 0, 0, 0.8)',
                padding: 12,
                titleFont: {{ size: 14 }},
                bodyFont: {{ size: 14, weight: 'bold' }},
                displayColors: true,
                callbacks: {{
                    label: function(context) {{
                        return context.dataset.label + ": " + context.parsed.y + "°C";
                    }}
                }}
            }}
        }},
        scales: {{
            x: {{
                display: false /* Hide axis but keep labels for tooltips */
            }},
            y: {{
                min: 20,
                max: 100,
                ticks: {{
                    color: '#999',
                    font: {{
                        size: 14, /* Larger chart numbers */
                        weight: 'bold'
                    }},
                    padding: 10
                }},
                grid: {{
                    color: 'rgba(255, 255, 255, 0.05)'
                }},
                border: {{ display: false }}
            }}
        }}
    }}
}});
</script>
</body>
</html>
"""

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=2013)