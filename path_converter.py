import gzip
import os
import tkinter
import xml.etree.ElementTree as ET
import re
import shutil
import pathlib
import json
from tkinter import *
from tkinter import ttk, messagebox, filedialog

settings = {"source_os": "win",
            "dest_os": "mac",
            "source_path": "C:\\",
            "dest_path": "/"
            }

config_filename = ".path_converter_config"

if os.path.isfile(config_filename):
    with open(config_filename, 'r') as config:
        try:
            loaded_settings = json.load(config)
            for key in settings.keys():
                if key not in loaded_settings:
                    raise KeyError
            settings = loaded_settings
        except json.JSONDecodeError:
            print("Could not decode settings file. Reverting to defaults.")
        except KeyError:
            print("Saved settings are corrupt or out of date. Reverting to defaults.")


def apply_changes(filename, root_node, source_path, dest_path, source_os, dest_os, warning_window):
    shutil.copy2(filename, filename + ".bak")

    # TODO: investigate this more. Is this actually that common?
    # TODO: figure out network share paths
    if (source_os == "win") and re.match("^.:\\\\", source_path):
        old = "\\\\*" + source_path     # Ensures that any leading backslashes are included in the search.

    iterate(root_node, source_path, dest_path, source_os, dest_os, filename, read_only_mode=False)
    with gzip.open(filename, 'wb') as f:
        f.write(ET.tostring(root_node))

        messagebox.showinfo("Success",
                            "File paths successfully altered. A backup of the original project file has been saved as "
                            + pathlib.PurePath(filename).name + ".bak.")
        warning_window.destroy()
    return


def iterate(node, source_path, dest_path, source_os, dest_os, project_file_path, read_only_mode):
    i = node.iter()
    next_node = next(i)

    results = ""

    while True:
        try:
            next_node = next(i)
            if next_node.tag != "FilePath":
                results += iterate(next_node, source_path, dest_path, source_os, dest_os, project_file_path, read_only_mode)
            else:
                # Do the main FilePath replacement
                path = next_node.text
                if re.search(source_path, next_node.text):
                    print(source_path)
                    print(dest_path)
                    path = re.sub(source_path, dest_path, next_node.text, flags=re.IGNORECASE)

                if dest_os == "win":
                    path = re.sub(r"/", r"\\", path)
                    # pure_path = pathlib.PureWindowsPath(path)
                else:  # Mac
                    path = re.sub(r"\\", r"/", path)
                    # pure_path = pathlib.PurePosixPath(path)

                if path == next_node.text:
                    # Nothing was changed, so move on to the next node
                    continue

                results += path + "\n"
                if not read_only_mode:
                    next_node.text = path

                # Change the ActualMediaFilePath nodes.
                # I'm not sure what the purpose of this node is. Changing it or leaving it alone seems to
                # have the same effect.
                actual_path_nodes = node.findall("ActualMediaFilePath")
                for apn in actual_path_nodes:
                    if not read_only_mode:
                        apn.text = path

                # Generate the RelativePath
                relative_path = ""
                if dest_os == "win":
                    try:
                        # If it's a simple relative path, let pathlib figure it out.
                        pure_path = pathlib.PureWindowsPath(path)
                        relative_path = pure_path.relative_to(pathlib.PureWindowsPath(project_file_path))
                    except ValueError:
                        # If that fails, append enough ".."s to get up to root and append the file's path, including
                        # the drive letter. It looks strange, but it's how Premiere does it internally.
                        for _ in range(len(pure_path.parents)):
                            relative_path += "..\\"
                        relative_path += str(pure_path)
                else:       # Mac
                    try:
                        pure_path = pathlib.PurePosixPath(path)
                        relative_path = pure_path.relative_to(pathlib.PurePosixPath(project_file_path))
                    except ValueError:
                        for _ in range(len(pure_path.parents)):
                            relative_path += "../"
                        path = str(pure_path)
                        if path[0] == "/":      # Make sure we don't accidentally add an extra slash
                            path = path[1:]
                        relative_path += str(path)

                # results += relative_path + "\n"

                # Change the RelativePath nodes.
                rel_path_nodes = node.findall("RelativePath")
                for rpn in rel_path_nodes:
                    if not read_only_mode:
                        rpn.text = relative_path

        except StopIteration:
            return results


def open_project(source_path, dest_path, source_os, dest_os):
    settings["source_os"] = source_os
    settings["dest_os"] = dest_os
    settings["source_path"] = source_path
    settings["dest_path"] = dest_path

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
    source_path = re.escape(source_path)
    dest_path = re.escape(dest_path)
    results = iterate(root_node, source_path, dest_path, source_os, dest_os, filename, read_only_mode=True)

    warning_window = Toplevel(root)
    warning_window.rowconfigure(0, weight=1)
    warning_window.columnconfigure(0, weight=1)

    warning_frame = ttk.Frame(warning_window, padding=10)
    warning_frame.grid(column=0, row=0, sticky=(N, W, E, S))

    textbox = tkinter.Text(warning_frame, width=150, height=50)
    textbox.grid(column=0, row=0, sticky=(N, W, E, S))
    textbox.insert("1.0", results)
    warning_label = ttk.Label(warning_frame, padding=20,
                              text="Do these new file paths look correct? If not, press Cancel!")
    warning_label.grid(column=0, row=1)

    apply_cancel_frame = Frame(warning_frame)
    apply_cancel_frame.grid(column=0, row=2)
    apply_button = ttk.Button(apply_cancel_frame, text="Apply",
                              command=lambda: apply_changes(filename, root_node, source_path, dest_path,
                                                            source_os, dest_os, warning_window))
    cancel_button = ttk.Button(apply_cancel_frame, text="Cancel", command=lambda: warning_window.destroy())
    apply_button.grid(column=0, row=0)
    cancel_button.grid(column=1, row=0)

    warning_window.grab_set()
    return


def browse_for_directory(source_or_dest, start_dir):
    new_path = filedialog.askdirectory(initialdir=start_dir)
    if new_path == "":
        return
    if source_or_dest == "source":
        source_path.set(new_path)
    else:
        dest_path.set(new_path)


root = Tk()
root.title("Premiere Path Converter")
root.columnconfigure(0, weight=1)

source_path = StringVar()
source_path.set(settings["source_path"])
dest_path = StringVar()
dest_path.set(settings["dest_path"])
source_os = StringVar()
dest_os = StringVar()

frame = ttk.Frame(root, padding=10)
frame.grid(column=0, row=0, sticky=(N, W, E, S))
frame.columnconfigure(0, weight=1)

options_frame = ttk.Frame(frame, padding=10)
options_frame.grid(column=0, row=0)

path_frame = ttk.Frame(frame, padding=10)
path_frame.columnconfigure(0, weight=1)

path_frame.grid(column=0, row=1, sticky=(N, S, W, E))

source_path_frame = ttk.LabelFrame(path_frame, text="Source Path")
source_path_frame.columnconfigure(0, weight=1, minsize=120)
source_path_frame.columnconfigure(1, weight=10000)
source_path_frame.grid(column=0, row=1, sticky=(N, S, W, E))

source_button_frame = ttk.Frame(source_path_frame, padding=5)
source_button_frame.grid(column=0, row=0, sticky=(N, S, W, E))

source_radio1 = ttk.Radiobutton(source_button_frame, text="Win", variable=source_os, value="win", padding=5)
source_radio1.grid(column=0, row=0)
source_radio2 = ttk.Radiobutton(source_button_frame, text="Mac", variable=source_os, value="mac", padding=5)
source_radio2.grid(column=1, row=0)
source_os.set(settings["source_os"])

source_path_entry = ttk.Entry(source_path_frame, textvariable=source_path)
source_path_entry.grid(column=1, row=0, sticky=(N, S, W, E))


source_path_browse_button = ttk.Button(source_path_frame, text="...", width=.5,
                                           command=lambda: browse_for_directory("source", source_path.get()))
source_path_browse_button.grid(column=2, row=0)

dest_path_frame = ttk.LabelFrame(path_frame, text="Destination Path")
dest_path_frame.columnconfigure(0, weight=1, minsize=120)
dest_path_frame.columnconfigure(1, weight=10000)
dest_path_frame.grid(column=0, row=2, sticky=(N, S, W, E))

dest_button_frame = ttk.Frame(dest_path_frame, padding=5)
dest_button_frame.grid(column=0, row=0, sticky=(N, S, W, E))

dest_radio1 = ttk.Radiobutton(dest_button_frame, text="Win", variable=dest_os, value="win", padding=5)
dest_radio1.grid(column=0, row=0)
dest_radio2 = ttk.Radiobutton(dest_button_frame, text="Mac", variable=dest_os, value="mac", padding=5)
dest_radio2.grid(column=1, row=0)
dest_os.set(settings["dest_os"])

dest_path_entry = ttk.Entry(dest_path_frame, textvariable=dest_path)
dest_path_entry.grid(column=1, row=0, sticky=(N, S, W, E))


dest_path_browse_button = ttk.Button(dest_path_frame, text="...", width=.5,
                                         command=lambda: browse_for_directory("dest", dest_path.get()))
dest_path_browse_button.grid(column=2, row=0)

load_button = ttk.Button(frame, text="Open Premiere Project",
                         command=lambda: open_project(source_path.get(), dest_path.get(), source_os.get(), dest_os.get()))
load_button.grid(column=0, row=2)

root.mainloop()
