import gzip
import os
import platform
import tkinter
import xml.etree.ElementTree as ET
import re
import shutil
import pathlib
import json
from tkinter import *
from tkinter import ttk, messagebox, filedialog

settings = {}
config_filename = ".path_converter_config"

if os.path.isfile(config_filename):
    with open(config_filename, 'r') as config:
        try:
            settings = json.load(config)
        except json.JSONDecodeError:
            print("Could not decode config file. Reverting to default settings.")
            settings = {"target": "win",
                        "win_path": "C:\\",
                        "mac_path": "/"}
else:
    settings = {"target": "win",
                "win_path": "C:\\",
                "mac_path": "/"}


def apply_changes(filename, root_node, old, repl, target_os, warning_window):
    shutil.copy2(filename, filename + ".bak")
    iterate(root_node, old, repl, target_os, read_only_mode=False)
    with gzip.open(filename, 'wb') as f:
        f.write(ET.tostring(root_node))

        messagebox.showinfo("Success", "File paths successfully altered. A backup of the original project file has been saved as " +
                            pathlib.PurePath(filename).name + ".bak.")
        warning_window.destroy()
    return


def iterate(node, mac_p, win_p, target_os, read_only_mode):
    i = node.iter()
    next_node = next(i)

    results = ""
    if target_os == "win":
        old = re.escape(mac_p)
        new = re.escape(win_p)
    else:
        old = re.escape(win_p)
        new = re.escape(mac_p)
        if re.match("^.:\\\\", old):
            old = "\\\\*" + old

    while True:
        try:
            next_node = next(i)
            if next_node.tag in ["FilePath", "ActualMediaFilePath"]:

                path = next_node.text
                if re.search(old, next_node.text):
                    path = re.sub(old, new, next_node.text, flags=re.IGNORECASE)
                    if target_os == "win":
                        path = re.sub(r"/", r"\\", path)
                    elif target_os == "mac":
                        path = re.sub(r"\\", r"/", path)
                if path != next_node.text:
                    results += path + "\n"
                    if not read_only_mode:
                        next_node.text = path
            else:
                results += iterate(next_node, mac_p, win_p, target_os, read_only_mode)
        except StopIteration:
            return results


def open_project(mac_p, win_p, target_os):
    settings["target"] = target_os
    settings["win_path"] = win_p
    settings["mac_path"] = mac_p
    try:
        with open(config_filename, "w") as conf:
            json.dump(settings, conf)
    except:
        print("Failed to save settings")

    filetypes = [('Premiere project files', '*.prproj')]
    filename = filedialog.askopenfilename(filetypes=filetypes)
    if filename == "":
        return

    with gzip.open(filename, 'rt') as f:
        try:
            file_content = f.read()
        except:
            print("Could not read file")
            return

    root_node = ET.fromstring(file_content)
    results = iterate(root_node, mac_p, win_p, target_os, read_only_mode=True)

    warning_window = Toplevel(root)
    warning_window.rowconfigure(0, weight=1)
    warning_window.columnconfigure(0, weight=1)

    warning_frame = ttk.Frame(warning_window)
    warning_frame.grid(column=0, row=0, sticky=(N, W, E, S))

    textbox = tkinter.Text(warning_frame, width=150, height=50)
    textbox.grid(column=0, row=0, sticky=(N, W, E, S))
    textbox.insert("1.0", results)
    warning_label = ttk.Label(warning_frame, padding=20,
                              text="Do these new file paths look correct? If not, press Cancel!")
    warning_label.grid(column=0, row=1)

    apply_cancel_frame = Frame(warning_frame)
    apply_cancel_frame.grid(column=0, row=2)
    apply_button = ttk.Button(apply_cancel_frame, text="Apply", command=lambda: apply_changes(filename, root_node, mac_p, win_p, target_os, warning_window))
    cancel_button = ttk.Button(apply_cancel_frame, text="Cancel", command=lambda: warning_window.destroy())
    apply_button.grid(column=0, row=0)
    cancel_button.grid(column=1, row=0)

    warning_window.grab_set()
    return


def browse_for_directory(platform):
    initial = ""
    if platform == "win":
        initial = win_path.get()
    else:
        initial = mac_path.get()

    new_path = filedialog.askdirectory(initialdir=initial)
    if new_path == "":
        return
    if platform == "win":
        win_path.set(new_path)
    else:
        mac_path.set(new_path)


root = Tk()
root.title("Premiere Path Converter")
root.columnconfigure(0, weight=1)

mac_path = StringVar()
mac_path.set(settings["mac_path"])
win_path = StringVar()
win_path.set(settings["win_path"])
target_var = StringVar()

frame = ttk.Frame(root, padding=10)
frame.grid(column=0, row=0, sticky=(N, W, E, S))
frame.columnconfigure(0, weight=1)

options_frame = ttk.Frame(frame, padding=10)
options_frame.grid(column=0, row=0)

target_button_frame = ttk.LabelFrame(options_frame, text="Target OS", padding=5)
target_button_frame.grid(column=0, row=0, sticky=(N, S, W, E))


target_radio1 = ttk.Radiobutton(target_button_frame, text="Windows", variable=target_var, value="win", padding=5)
target_radio1.grid(column=0, row=0)
target_radio2 = ttk.Radiobutton(target_button_frame, text="Mac", variable=target_var, value="mac", padding=5)
target_radio2.grid(column=1, row=0)
target_var.set(settings["target"])

path_frame = ttk.Frame(frame, padding=10)
path_frame.columnconfigure(0, weight=1)

path_frame.grid(column=0, row=1, sticky=(N, S, W, E))


mac_path_frame = ttk.LabelFrame(path_frame, text="Mac Path")
mac_path_frame.columnconfigure(0, weight=1)
mac_path_frame.grid(column=0, row=1, sticky=(N, S, W, E))

mac_path_entry = ttk.Entry(mac_path_frame, textvariable=mac_path)
mac_path_entry.grid(column=0, row=0, sticky=(N, S, W, E))

if platform.system() == "Darwin":
    mac_path_browse_button = ttk.Button(mac_path_frame, text="...", width=.5, command=lambda: browse_for_directory("mac"))
    mac_path_browse_button.grid(column=1, row=0)


win_path_frame = ttk.LabelFrame(path_frame, text="Windows Path")
win_path_frame.columnconfigure(0, weight=1)
win_path_frame.grid(column=0, row=2, sticky=(N, S, W, E))

win_path_entry = ttk.Entry(win_path_frame, textvariable=win_path)
win_path_entry.grid(column=0, row=0, sticky=(N, S, W, E))

if platform.system() == "Windows":
    win_path_browse_button = ttk.Button(win_path_frame, text="...", width=.5, command=lambda: browse_for_directory("win"))
    win_path_browse_button.grid(column=1, row=0, sticky=(N, S, W, E))

load_button = ttk.Button(frame, text="Open Premiere Project", command=lambda: open_project(mac_path.get(), win_path.get(), target_var.get()))
load_button.grid(column=0, row=2)

root.mainloop()


