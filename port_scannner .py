import csv
import ipaddress
import socket
import threading
import tkinter as tk
from concurrent.futures import ThreadPoolExecutor
from tkinter import ttk, messagebox, filedialog

results = []
lock = threading.Lock()
stop_event = threading.Event()
scanned = 0
total = 0
scan_thread = None


def grab_banner(sock, target):
    try:
        sock.settimeout(1)
        # 1) خدمات بتحكي أول (SSH, FTP, SMTP)
        try:
            data = sock.recv(1024)
            if data:
                return data.decode(errors="ignore").strip()
        except socket.timeout:
            pass
        # 2) إذا سكتت، جرّب طلب HTTP
        sock.sendall(f"HEAD / HTTP/1.0\r\nHost: {target}\r\n\r\n".encode())
        data = sock.recv(1024)
        if data:
            return data.decode(errors="ignore").strip()
    except Exception:
        pass
    return ""


def scan_port(target, port, timeout):
    global scanned
    if stop_event.is_set():
        return
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        if sock.connect_ex((target, port)) == 0:
            try:
                service = socket.getservbyport(port, "tcp")
            except OSError:
                service = "Unknown"

            raw = grab_banner(sock, target)
            if raw.startswith("HTTP/"):
                service = "HTTP"
                lines = raw.splitlines()
                banner = lines[0]
                for line in lines[1:]:
                    if line.lower().startswith("server:"):
                        banner += " | " + line.strip()
                        break
            elif raw:
                banner = raw.splitlines()[0]
            else:
                banner = "No banner received"

            banner = "".join(c for c in banner if c.isprintable())[:100]
            with lock:
                results.append((port, service, banner))
    except OSError:
        pass
    finally:
        sock.close()
        with lock:
            scanned += 1


def run_scan(ip, start_port, end_port, workers, timeout):
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for p in range(start_port, end_port + 1):
            if stop_event.is_set():
                break
            ex.submit(scan_port, ip, p, timeout)


def update_progress():
    with lock:
        done = scanned
        found = len(results)
    progress["value"] = done
    if scan_thread.is_alive():
        status.config(text=f"Scanning... {done}/{total} | open: {found}")
        root.after(100, update_progress)
    else:
        finish_scan()


def finish_scan():
    for row in tree.get_children():
        tree.delete(row)
    with lock:
        final = sorted(results)
    for port, service, banner in final:
        tree.insert("", "end", values=(port, service, banner))

    word = "Stopped" if stop_event.is_set() else "Done"
    status.config(text=f"{word} — {len(final)} open port(s)")
    scan_button.config(state="normal")
    stop_button.config(state="disabled")
    export_button.config(state="normal" if final else "disabled")


def start_scan():
    global scanned, total, scan_thread
    ip = ip_entry.get().strip()
    try:
        start_port = int(start_entry.get())
        end_port = int(end_entry.get())
        timeout = float(timeout_entry.get())
        workers = int(threads_entry.get())
    except ValueError:
        messagebox.showerror("Error", "Ports, timeout and threads must be numbers")
        return

    if not ip:
        messagebox.showerror("Error", "Enter a target IP")
        return
    try:
        ipaddress.ip_address(ip)
    except ValueError:
        messagebox.showerror("Error", "Invalid IP address")
        return
    if start_port > end_port or start_port < 1 or end_port > 65535:
        messagebox.showerror("Error", "Invalid port range!")
        return
    if timeout <= 0 or not 1 <= workers <= 500:
        messagebox.showerror("Error", "Timeout must be > 0 and threads between 1 and 500")
        return

    stop_event.clear()
    with lock:
        results.clear()
        scanned = 0
    total = end_port - start_port + 1

    for row in tree.get_children():
        tree.delete(row)
    progress.config(maximum=total, value=0)
    scan_button.config(state="disabled")
    stop_button.config(state="normal")
    export_button.config(state="disabled")
    status.config(text=f"Scanning {ip} ({start_port}-{end_port})...")

    scan_thread = threading.Thread(
        target=run_scan,
        args=(ip, start_port, end_port, workers, timeout),
        daemon=True,
    )
    scan_thread.start()
    update_progress()


def stop_scan():
    stop_event.set()
    stop_button.config(state="disabled")
    status.config(text="Stopping...")


def export_results():
    with lock:
        data = sorted(results)
    if not data:
        messagebox.showinfo("Export", "No results to export")
        return
    path = filedialog.asksaveasfilename(
        defaultextension=".csv", filetypes=[("CSV files", "*.csv")]
    )
    if not path:
        return
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["Port", "Service", "Banner"])
        writer.writerows(data)
    messagebox.showinfo("Export", f"Saved {len(data)} rows")


def on_close():
    stop_event.set()
    root.destroy()


root = tk.Tk()
root.title("Port Scanner")
root.geometry("700x650")
root.protocol("WM_DELETE_WINDOW", on_close)

tk.Label(root, text="Port Scanner", font=("Arial", 20, "bold")).pack(pady=10)

form = tk.Frame(root)
form.pack()


def add_field(row, label, default):
    tk.Label(form, text=label).grid(row=row, column=0, sticky="e", padx=5, pady=3)
    entry = tk.Entry(form, width=25)
    entry.insert(0, default)
    entry.grid(row=row, column=1, padx=5, pady=3)
    return entry


ip_entry = add_field(0, "Target IP:", "127.0.0.1")
start_entry = add_field(1, "Start Port:", "1")
end_entry = add_field(2, "End Port:", "1024")
timeout_entry = add_field(3, "Timeout (s):", "0.5")
threads_entry = add_field(4, "Threads:", "100")

buttons = tk.Frame(root)
buttons.pack(pady=10)
scan_button = tk.Button(buttons, text="Start Scan", width=12, command=start_scan)
scan_button.grid(row=0, column=0, padx=5)
stop_button = tk.Button(buttons, text="Stop", width=12, command=stop_scan, state="disabled")
stop_button.grid(row=0, column=1, padx=5)
export_button = tk.Button(buttons, text="Export CSV", width=12, command=export_results, state="disabled")
export_button.grid(row=0, column=2, padx=5)

progress = ttk.Progressbar(root, length=500, mode="determinate")
progress.pack(pady=5)

status = tk.Label(root, text="Ready")
status.pack()

table_frame = tk.Frame(root)
table_frame.pack(fill="both", expand=True, padx=10, pady=10)
tree = ttk.Treeview(table_frame, columns=("port", "service", "banner"), show="headings", height=10)
for col, w in (("port", 80), ("service", 120), ("banner", 420)):
    tree.heading(col, text=col.capitalize())
    tree.column(col, width=w)
scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
tree.configure(yscrollcommand=scrollbar.set)
tree.pack(side="left", fill="both", expand=True)
scrollbar.pack(side="right", fill="y")

root.mainloop()



