import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import paho.mqtt.client as mqtt
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from collections import deque
import threading
import time
import datetime
import csv

# Configuración MQTT
MQTT_BROKER = "213.194.129.165"
MQTT_PORT = 1883

TOPICS = {
    "luz": "sensores/luz",
    "sonido": "sensores/sonido",
    "temperatura": "sensores/temperatura",
    "humedad": "sensores/humedad",
    "distancia": "sensores/distancia",
}

data_buffers = {key: deque(maxlen=100) for key in TOPICS}
time_buffer = deque(maxlen=100)

def on_connect(client, userdata, flags, rc):
    print("Conectado con código:", rc)
    if rc == 0:
        for topic in TOPICS.values():
            client.subscribe(topic)
    else:
        messagebox.showerror("Error", f"No se pudo conectar al broker (rc={rc})")

def on_message(client, userdata, msg):
    topic = msg.topic
    payload = msg.payload.decode()
    try:
        value = float(payload)
        timestamp = time.time()
        for key, t in TOPICS.items():
            if topic == t:
                data_buffers[key].append(value)
                if len(time_buffer) == 0 or timestamp != time_buffer[-1]:
                    time_buffer.append(timestamp)
    except ValueError:
        print(f"Valor no válido recibido en {topic}: {payload}")

def mostrar_login():
    login_win = tk.Toplevel()
    login_win.title("Login MQTT")
    login_win.grab_set()

    ttk.Label(login_win, text="Usuario:").grid(row=0, column=0, padx=10, pady=10)
    usuario_entry = ttk.Entry(login_win)
    usuario_entry.grid(row=0, column=1, padx=10, pady=10)

    ttk.Label(login_win, text="Contraseña:").grid(row=1, column=0, padx=10, pady=10)
    password_entry = ttk.Entry(login_win, show="*")
    password_entry.grid(row=1, column=1, padx=10, pady=10)

    resultado = {"usuario": None, "password": None}

    def aceptar():
        resultado["usuario"] = usuario_entry.get()
        resultado["password"] = password_entry.get()
        if not resultado["usuario"] or not resultado["password"]:
            messagebox.showwarning("Campos requeridos", "Debes ingresar usuario y contraseña.")
        else:
            login_win.destroy()

    ttk.Button(login_win, text="Conectar", command=aceptar).grid(row=2, column=0, columnspan=2, pady=10)
    login_win.wait_window()
    return resultado["usuario"], resultado["password"]

def guardar_datos():
    if not time_buffer:
        messagebox.showinfo("Sin datos", "No hay datos para guardar.")
        return

    file_path = filedialog.asksaveasfilename(
        defaultextension=".csv",
        filetypes=[("CSV files", "*.csv")],
        title="Guardar datos de sensores"
    )

    if not file_path:
        return

    with open(file_path, mode='w', newline='') as file:
        writer = csv.writer(file)
        header = ["Hora"] + list(TOPICS.keys())
        writer.writerow(header)

        for i in range(len(time_buffer)):
            row = []
            timestamp = datetime.datetime.fromtimestamp(time_buffer[i]).strftime("%Y-%m-%d %H:%M:%S")
            row.append(timestamp)
            for key in TOPICS:
                buffer = data_buffers[key]
                if i < len(buffer):
                    row.append(buffer[i])
                else:
                    row.append("")
            writer.writerow(row)

    messagebox.showinfo("Datos guardados", f"Datos guardados en:\n{file_path}")

root = tk.Tk()
root.withdraw()

usuario, password = mostrar_login()
if not usuario or not password:
    root.destroy()
    exit()

client = mqtt.Client()
client.username_pw_set(usuario, password)
client.on_connect = on_connect
client.on_message = on_message
client.connect(MQTT_BROKER, MQTT_PORT, 60)

threading.Thread(target=client.loop_forever, daemon=True).start()

root.deiconify()
root.title("Dashboard MQTT")

frame = ttk.Frame(root, padding="20")
frame.grid(row=0, column=0)

button_opts = {"width": 15, "padding": 10}

ttk.Button(frame, text="Adelante", command=lambda: client.publish("movimiento", "adelante"), **button_opts).grid(row=0, column=1, pady=5)
ttk.Button(frame, text="Izquierda", command=lambda: client.publish("movimiento", "izquierda"), **button_opts).grid(row=1, column=0, padx=5)
ttk.Button(frame, text="Derecha", command=lambda: client.publish("movimiento", "derecha"), **button_opts).grid(row=1, column=2, padx=5)
ttk.Button(frame, text="Atrás", command=lambda: client.publish("movimiento", "atras"), **button_opts).grid(row=2, column=1, pady=5)

ttk.Button(frame, text="Guardar datos", command=guardar_datos).grid(row=3, column=1, pady=10)

fig, axs = plt.subplots(3, 2, figsize=(12, 9))
fig.tight_layout(pad=3.0)

def update(frame):
    times = list(time_buffer)
    for ax in axs.flat:
        ax.clear()

    for i, key in enumerate(TOPICS):
        row, col = divmod(i, 2)
        ax = axs[row][col]
        ax.set_title(key.capitalize())

        y_values = list(data_buffers[key])
        raw_times = times[-len(y_values):]
        x_values = [datetime.datetime.fromtimestamp(t).strftime("%H:%M:%S") for t in raw_times]

        if len(x_values) == len(y_values) and len(y_values) > 0:
            ax.plot(x_values, y_values)
            ax.set_xlabel("Hora")
            ax.set_ylabel(key)
            ax.tick_params(axis='x', rotation=45)
        else:
            ax.text(0.5, 0.5, "Sin datos", ha="center", va="center", transform=ax.transAxes)

    for j in range(i + 1, len(axs.flat)):
        axs.flat[j].clear()
        axs.flat[j].text(0.5, 0.5, "Sin datos", ha="center", va="center", transform=axs.flat[j].transAxes)

ani = FuncAnimation(fig, update, interval=1000)

plt.show()
root.mainloop()
