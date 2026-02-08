from flask import Flask
import psutil

app = Flask(__name__)

IGNORE = {"/boot", "/boot/efi"}


# -------------------------
# Helpers
# -------------------------

def human(b):
    for u in ['B','KB','MB','GB','TB','PB']:
        if b < 1024:
            return f"{b:.1f} {u}"
        b /= 1024


def usage_color(p):
    """
    p = used percent
    green → yellow → orange → red
    """
    if p < 25:
        return "#22c55e"   # green
    elif p < 50:
        return "#a3e635"   # yellow-green
    elif p < 70:
        return "#facc15"   # yellow
    elif p < 85:
        return "#fb923c"   # orange
    else:
        return "#ef4444"   # red


def get_disks():
    disks = []

    for part in psutil.disk_partitions(all=False):
        if part.mountpoint in IGNORE:
            continue

        try:
            u = psutil.disk_usage(part.mountpoint)

            disks.append({
                "mount": part.mountpoint,
                "free": human(u.free),
                "total": human(u.total),
                "used_percent": u.percent
            })

        except PermissionError:
            pass

    # show most full first (way more useful visually)
    disks.sort(key=lambda d: d["used_percent"], reverse=True)

    return disks


# -------------------------
# Route
# -------------------------

@app.route("/")
def index():

    rows = ""

    for d in get_disks():
        color = usage_color(d["used_percent"])

        rows += f"""
        <div class="disk">
            <div class="row">
                <span class="mount">{d["mount"]}</span>
                <span class="space"></span>
                <span class="percent">Free {d["free"]} / {d["total"]} | {d["used_percent"]:.0f}%</span>
            </div>

            <div class="bar">
                <div class="fill" style="width:{d["used_percent"]}%; background:{color};"></div>
            </div>
        </div>
        """

    return f"""
    <html>
    <head>
      <meta http-equiv="refresh" content="10">

      <style>
        html, body {{
            margin:0;
            background:transparent;
            color:#eee;
            font-family:system-ui;
            width:100%;
        }}

        .disk {{
            width:100%;
            margin-bottom:14px;
        }}

        .row {{
            display:flex;
            justify-content:space-between;
            font-size:13px;
            margin-bottom:6px;
            opacity:.9;
        }}

        .mount {{
            font-weight:600;
        }}

        .bar {{
            width:100%;
            height:14px;          /* thicker */
            background:#222;
            border-radius:8px;
            overflow:hidden;
        }}

        .fill {{
            height:100%;
            transition:width .3s ease;
        }}
      </style>
    </head>
    <body>
        {rows}
    </body>
    </html>
    """


# -------------------------
# Run
# -------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=2014)
