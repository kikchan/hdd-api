import eventlet
eventlet.monkey_patch()

from flask import Flask
from flask_socketio import SocketIO
import subprocess, re
from collections import deque
from datetime import datetime
import psutil


app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

MAX_POINTS = 1800


cpu_temp = deque(maxlen=MAX_POINTS)
gpu_temp = deque(maxlen=MAX_POINTS)
cpu_use = deque(maxlen=MAX_POINTS)
gpu_use = deque(maxlen=MAX_POINTS)
ram_use = deque(maxlen=MAX_POINTS)
labels = deque(maxlen=MAX_POINTS)
swap_use = deque(maxlen=MAX_POINTS)


# ---------------- helpers ----------------
def get_cpu_temp():
    out = subprocess.getoutput("sensors")
    m = re.search(r"Package id 0:\s+\+?([\d\.]+)", out)
    return float(m.group(1)) if m else 0


def get_cpu_usage():
    out = subprocess.getoutput("top -bn1 | grep 'Cpu(s)'")
    m = re.search(r"(\d+\.\d+)\s*id", out)
    return round(100 - float(m.group(1)), 1) if m else 0


def get_gpu():
    try:
        out = subprocess.getoutput(
            "nvidia-smi --query-gpu=temperature.gpu,utilization.gpu --format=csv,noheader,nounits"
        )
        t, u = out.split(",")
        return float(t), float(u)
    except:
        return 0, 0


def get_ram_usage():
    return round(psutil.virtual_memory().percent, 1)
    
def get_swap_usage():
    return round(psutil.swap_memory().percent, 1)


def get_ram_top():
    processes = []
    for p in psutil.process_iter(['name', 'memory_percent']):
        try:
            processes.append((p.info['name'], p.info['memory_percent']))
        except:
            continue

    top3 = sorted(processes, key=lambda x: x[1], reverse=True)[:3]
    return [f"{name}: {mem:.1f}%" for name, mem in top3]


# ---------------- collector ----------------
def background():
    while True:
        ct = get_cpu_temp()
        cu = get_cpu_usage()
        gt, gu = get_gpu()
        ru = get_ram_usage()
        su = get_swap_usage() 

        labels.append(datetime.now().strftime("%H:%M"))

        cpu_temp.append(ct)
        gpu_temp.append(gt)
        cpu_use.append(cu)
        gpu_use.append(gu)
        ram_use.append(ru)
        swap_use.append(su)

        socketio.emit("update", {
            "labels": list(labels),
            "ct": list(cpu_temp),
            "gt": list(gpu_temp),
            "cu": list(cpu_use),
            "gu": list(gpu_use),
            "ru": list(ram_use),
            "su": list(swap_use),
            "top_ram": get_ram_top()
        })

        eventlet.sleep(2)


# ---------------- UI ----------------
@app.route("/")
def root():
    return """
<html>
<head>
<meta charset="utf-8">

<style>
body{
  background:transparent;
  color:#eee;
  font-family:system-ui;
  margin:0;
  padding:10px;
}

.grid{
  display:grid;
  grid-template-columns:1fr 1fr 1fr;
  gap:12px;
  text-align:center;
}

.temp{font-size:20px;font-weight:800;}
.cpu{color:#00bfff;}
.gpu{color:#00ff66;}
.ram{color:orange;}

.usage{font-size:20px;opacity:.7;}

.stats{
  font-size:12px;
  opacity:.85;
  margin-top:6px;
  line-height:1.6;
  white-space:pre-line;
}

#chart{
  width:100%!important;
  height:400px;
  margin-top:10px;
}

.overlay{
  position:fixed;   /* ← KEY FIX */
  pointer-events:none;
  background:rgba(20,20,20,0.92);
  border:1px solid rgba(255,255,255,.12);
  border-radius:10px;
  padding:8px 12px;
  font-size:12px;
  display:none;
  backdrop-filter:blur(6px);
}

</style>
</head>

<body>

<div class="grid">
  <div>
    <div class="temp cpu">CPU</div>
    <div class="temp" id="cpu_main">--°C</div>
    <div class="usage" id="cpu_usage">--%</div>
    <div class="stats" id="cpu_stats"></div>
  </div>

  <div>
    <div class="temp gpu">GPU</div>
    <div class="temp" id="gpu_main">--°C</div>
    <div class="usage" id="gpu_usage">--%</div>
    <div class="stats" id="gpu_stats"></div>
  </div>

  <div>
    <div class="temp ram">RAM</div>
    <div class="temp" id="ram_main">--%</div>
    <div class="usage" id="swap_usage" title="Swap usage">--%</div>
    <div class="stats" id="ram_stats"></div>
  </div>
</div>

<div id="overlay" class="overlay"></div>
<canvas id="chart"></canvas>

<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script src="https://cdn.socket.io/4.7.5/socket.io.min.js"></script>

<script>
const socket = io();
const overlay = document.getElementById("overlay");

const chart = new Chart(document.getElementById('chart'), {
 type:'line',
 data:{
   labels:[],
   datasets:[
     {label:'CPU Temp',data:[],borderColor:'#00bfff',pointRadius:0,tension:.35},
     {label:'GPU Temp',data:[],borderColor:'#00ff66',pointRadius:0,tension:.35},
     {label:'CPU Use',data:[],borderColor:'#00bfff',borderDash:[5,5],pointRadius:0},
     {label:'GPU Use',data:[],borderColor:'#00ff66',borderDash:[5,5],pointRadius:0},
     {label:'RAM Use',data:[],borderColor:'orange',borderDash:[5,5],pointRadius:0},
     {label:'Swap Use', data:[], borderColor:'violet', borderDash:[5,5], pointRadius:0}
   ]
 },
 options:{
   responsive:true,
   animation:false,
   interaction:{mode:'index',intersect:false},
   plugins:{legend:{display:false},tooltip:{enabled:false}},
   onHover:(e, elements)=>{
      if(!elements.length){
        overlay.style.display="none";
        return;
      }

      const i = elements[0].index;

      overlay.style.display="block";

      // ✅ PERFECT ALIGNMENT
      overlay.style.left = (e.native.clientX + 14) + "px";
      overlay.style.top  = (e.native.clientY + 14) + "px";

      overlay.innerHTML =
        "Time: "+chart.data.labels[i]+"<br>"+
        "CPU: "+chart.data.datasets[0].data[i]+"°C ("+chart.data.datasets[2].data[i]+"%)<br>"+
        "GPU: "+chart.data.datasets[1].data[i]+"°C ("+chart.data.datasets[3].data[i]+"%)<br>"+
        "RAM: "+chart.data.datasets[4].data[i]+"%"
   },
   scales:{
     y:{min:0,max:100},
     x:{ticks:{maxTicksLimit:10}}
   }
 }
});


function statTemp(arr){
 const min=Math.min(...arr)
 const max=Math.max(...arr)
 const avg=(arr.reduce((a,b)=>a+b,0)/arr.length).toFixed(1)
 return `Temperature\nMin: ${min}°C\nAvg: ${avg}°C\nMax: ${max}°C`
}

function statUse(arr){
 const min=Math.min(...arr)
 const max=Math.max(...arr)
 const avg=(arr.reduce((a,b)=>a+b,0)/arr.length).toFixed(1)
 return `Usage\nMin: ${min}%\nAvg: ${avg}%\nMax: ${max}%`
}


socket.on("update", d=>{
 chart.data.labels=d.labels
 chart.data.datasets[0].data=d.ct
 chart.data.datasets[1].data=d.gt
 chart.data.datasets[2].data=d.cu
 chart.data.datasets[3].data=d.gu
 chart.data.datasets[4].data=d.ru
 chart.data.datasets[5].data=d.su
 chart.update()

 cpu_main.innerText=d.ct.at(-1)+"°C"
 gpu_main.innerText=d.gt.at(-1)+"°C"
 ram_main.innerText=d.ru.at(-1)+"%"
 cpu_usage.innerText=d.cu.at(-1)+"%"
 gpu_usage.innerText=d.gu.at(-1)+"%"
 swap_usage.innerText=d.su.at(-1)+"%"

 cpu_stats.innerText = statUse(d.cu) + "\\n\\n" + statTemp(d.ct)
 gpu_stats.innerText = statUse(d.gu) + "\\n\\n" + statTemp(d.gt)
 ram_stats.innerText = statUse(d.ru) + "\\n\\nTop Processes:\\n" + d.top_ram.join("\\n")
})
</script>
</body>
</html>
"""


if __name__ == "__main__":
    socketio.start_background_task(background)
    socketio.run(app, host="0.0.0.0", port=2013)
