TOOL = {
    "name": "system_monitor",
    "description": "Report CPU, RAM, disk, battery and temperature of this computer.",
    "parameters": {"type": "object", "properties": {}},
}


def handler(params, ctx):
    import psutil
    out = [f"CPU {psutil.cpu_percent(interval=0.5)}%",
           f"RAM {psutil.virtual_memory().percent}%",
           f"Disk {psutil.disk_usage('/').percent}%"]
    b = psutil.sensors_battery() if hasattr(psutil, "sensors_battery") else None
    if b: out.append(f"Battery {int(b.percent)}%{' (charging)' if b.power_plugged else ''}")
    if hasattr(psutil, "sensors_temperatures"):
        temps = psutil.sensors_temperatures()
        for entries in temps.values():
            if entries: out.append(f"Temp {entries[0].current:.0f}°C"); break
    return ", ".join(out)
