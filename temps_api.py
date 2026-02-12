from flask import Flask
from flask_socketio import SocketIO
import subprocess, re, eventlet
from collections import deque
from datetime import datetime

eventlet.monkey_patch()

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

MAX_POINTS = 1800  # 1h history

cpu_temp = deque(maxlen=MAX_POINTS)
gpu_temp = deque(maxlen=MAX_POINTS)
cpu_use = deque(maxlen=MAX_POINTS)
gpu_use = deque(maxlen=MAX_POINTS)
labels = deque(maxlen=MAX_POINTS)


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


# ---------------- collector ----------------
def background():
    while True:
        ct = get_cpu_temp()
        cu = get_cpu_usage()
        gt, gu = get_gpu()

        labels.append(datetime.now().strftime("%H:%M"))

        cpu_temp.append(ct)
        gpu_temp.append(gt)
        cpu_use.append(cu)
        gpu_use.append(gu)

        socketio.emit("update", {
            "labels": list(labels),
            "ct": list(cpu_temp),
            "gt": list(gpu_temp),
            "cu": list(cpu_use),
            "gu": list(gpu_use),
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
  grid-template-columns:1fr 1fr;
  gap:12px;
  text-align:center;
}

.temp{
  font-size:42px;
  font-weight:800;
}

.cpu{color:#00bfff;}
.gpu{color:#00ff66;}

.usage{
  font-size:13px;
  opacity:.7;
}

.stats{
  font-size:12px;
  opacity:.85;
  margin-top:6px;
  line-height:1.6;
  white-space:pre-line;
}

#chart{
  width:100%!important;
  margin-top:10px;
}
</style>
</head>

<body>

<div class="grid">

  <div>
    <div class="temp cpu" id="cpu_main">--°C</div>
    <div class="usage" id="cpu_usage">--%</div>
    <br/>
    <div class="stats" id="cpu_stats"></div>
  </div>

  <div>
    <div class="temp gpu" id="gpu_main">--°C</div>
    <div class="usage" id="gpu_usage">--%</div>
    <br/>
    <div class="stats" id="gpu_stats"></div>
  </div>

</div>

<canvas id="chart"></canvas>

<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script src="https://cdn.socket.io/4.7.5/socket.io.min.js"></script>

<script>
const socket = io();

const chart = new Chart(document.getElementById('chart'), {
 type:'line',
 data:{
   labels:[],
   datasets:[
     {label:'CPU Temp',data:[],borderColor:'#00bfff',pointRadius:0,tension:.35},
     {label:'GPU Temp',data:[],borderColor:'#00ff66',pointRadius:0,tension:.35},
     {label:'CPU Use',data:[],borderColor:'#00bfff',borderDash:[5,5],pointRadius:0},
     {label:'GPU Use',data:[],borderColor:'#00ff66',borderDash:[5,5],pointRadius:0}
   ]
 },
 options:{
   responsive:true,
   maintainAspectRatio:true,
   animation:false,
   devicePixelRatio:(window.devicePixelRatio||1)*2,

   layout:{padding:{left:10,right:10,top:5,bottom:5}},

   interaction:{mode:'index',intersect:false},

   plugins:{
     legend:{display:false},
     tooltip:{
       backgroundColor:'#111',
       titleColor:'#fff',
       bodyColor:'#fff',
       borderColor:'#333',
       borderWidth:1
     }
   },

   scales:{
     y:{
       min:0,
       max:100,
       ticks:{stepSize:20},
       alignToPixels:true
     },
     x:{
       bounds:'ticks',
       ticks:{
         maxTicksLimit:10,
         maxRotation:45,
         minRotation:45,
         autoSkip:true
       }
     }
   }
 }
});


function statTemp(arr){
 const min=Math.min(...arr)
 const max=Math.max(...arr)
 const avg=(arr.reduce((a,b)=>a+b,0)/arr.length).toFixed(1)

 return `Temperature
Min: ${min}°C
Avg: ${avg}°C
Max: ${max}°C

`
}

function statUse(arr){
 const min=Math.min(...arr)
 const max=Math.max(...arr)
 const avg=(arr.reduce((a,b)=>a+b,0)/arr.length).toFixed(1)

 return `Usage
Min: ${min}%
Avg: ${avg}%
Max: ${max}%`
}



socket.on("update", d=>{

 chart.data.labels=d.labels
 chart.data.datasets[0].data=d.ct
 chart.data.datasets[1].data=d.gt
 chart.data.datasets[2].data=d.cu
 chart.data.datasets[3].data=d.gu
 chart.update()

 cpu_main.innerText=d.ct.at(-1)+"°C"
 gpu_main.innerText=d.gt.at(-1)+"°C"

 cpu_usage.innerText=d.cu.at(-1)+"% usage"
 gpu_usage.innerText=d.gu.at(-1)+"% usage"

 cpu_stats.innerText = statTemp(d.ct)+statUse(d.cu)
 gpu_stats.innerText = statTemp(d.gt)+statUse(d.gu)
})
</script>

</body>
</html>
"""


if __name__ == "__main__":
    socketio.start_background_task(background)
    socketio.run(app, host="0.0.0.0", port=2013)
