import os
import json
from datetime import datetime, timezone
from tkinter import *
from tkinter import ttk
from ttkthemes import themed_tk as tk
import ctypes
import threading
import pyperclip
import time

# Help with GUI resolution by increasing pixel density
ctypes.windll.shcore.SetProcessDpiAwareness(1)

def get_drives():
    drives = []
    bitmask = ctypes.windll.kernel32.GetLogicalDrives()
    for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
        if bitmask & 1:
            drives.append(letter)
        bitmask >>= 1
    return drives

class fileHypersearch:
    def __init__(self):
        self.indexed_files = []
        self.matches = []
        self.count = 0  # Number of matches per search query
        
    def reindex(self):
        # Initiate a thread to reindex
        self.indexed_files.clear()
        threading.Thread(target=self.helperThread).start()
        
    def helperThread(self):
        # Initiate indeterminate Progress bar
        progress = ttk.Progressbar(window, orient=HORIZONTAL, length=400)
        progress.place(x=400, y=450)
        progress.config(mode='indeterminate')
        progress.start()

        # Retrieve active drives on PC
        drives = get_drives()

        # Walk file tree for each drive letter, store tuple of (path, all files in path)
        for letter in drives:
            tmp = [(root, files) for (root, dirs, files) in os.walk(letter + ':/')]
            self.indexed_files.extend(tmp)

        # Store indexed files 
        with open('indexed_files.json', 'w') as write_file:
            json.dump(self.indexed_files, write_file)

        progress.stop()
        progress.destroy()

    def load_prev_indexed(self):
        # Load from JSON file if exists
        try:
            with open('indexed_files.json', 'r') as read_file:
                self.indexed_files = json.load(read_file)
        except:
            self.indexed_files = []

    def update_matches(self, file, path):
        try:
            file_stats = os.stat(path + '/' + file)
            self.matches.append((file, path, file_stats.st_size // 1024, datetime.fromtimestamp(file_stats.st_mtime)))
            self.count += 1
        except:
            return

    def search(self, query, search_mode = 'contains'):
        # Reset search results
        self.matches.clear()
        self.count = 0
        query = query.lower()
        for path, file_list in self.indexed_files:
            for file in file_list:
                if search_mode == 'contains':
                    if query in file.lower():
                        self.update_matches(file, path)
                elif search_mode == 'endswith':
                    if file.lower().endswith(query):
                        self.update_matches(file, path)
                elif search_mode == 'startswith':
                    if file.lower().startswith(query):
                        self.update_matches(file, path)
    
    def onClick(self, tree, opt, matchesLabel):
        # Retrieve search query
        query = search_box.get()
        
        if len(query) == 0:
            matchesLabel.config(text='Please provide a valid query')
            return

        # Perform search and reset treeview
        engine.search(query, opt.get())
        tree.delete(*tree.get_children())

        # Populate treeview
        i = 0
        for file, path, size, dt in engine.matches:
            tree.insert(parent='', index='end', iid=i, text='', values=(file, path, str(size) + ' KB', dt.date()))
            i += 1

        # Add Copy to clipboard functionality to double click
        tree.bind("<Double-1>", self.onDoubleClick)
        matchesLabel.config(text=str(engine.count) + ' matches found')

    def onDoubleClick(self, event):
        item = tree.selection()[0]
        pyperclip.copy(tree.item(item,"values")[1])
        threading.Thread(target=self.msgThread).start()
        
    def msgThread(self):
        # Generate self-destructing message
        msg = Label(window)
        msg.place(x=1000, y=873)
        msg.config(text='Path copied to clipboard!')
        window.update()
        time.sleep(2)
        msg.destroy()
        

if __name__ == '__main__':
    engine = fileHypersearch()
    engine.load_prev_indexed()

    window = tk.ThemedTk()
    window.geometry('1200x900')
    window.set_theme('equilux')
    window.title('File Hypersearch')

    search_box = Entry(window, width=85)
    search_box.place(x=10, y=10, height=20)

    tree_frame = Frame(window)
    tree_frame.place(x=0,y=40)
    
    tree_scroll = Scrollbar(tree_frame)
    tree_scroll.pack(side=RIGHT, fill=Y)

    tree = ttk.Treeview(tree_frame, yscrollcommand=tree_scroll.set, height=40)
    tree_scroll.config(command=tree.yview)

    tree['columns'] = ('Name', 'Path', 'Size', 'Date Modified')
    tree.column('#0', width=0)
    tree.column('Name', anchor=W, width=300)
    tree.column('Path', anchor=W, width=450)
    tree.column('Size', anchor=E, width=150)
    tree.column('Date Modified', anchor=W, width=277)
    tree.heading('Name', text='Name', anchor=W)
    tree.heading('Path', text=' Path', anchor=W)
    tree.heading('Size', text='Size ', anchor=E)
    tree.heading('Date Modified', text=' Date Modified', anchor=W)

    for col in tree['columns']:
        tree.heading(col, command=lambda c=col: sort_tree_col(tree, c, False))

    matchesLabel = Label(window)
    matchesLabel.place(x=0, y=873)
    

    def sort_tree_col(tree, col, reverse):
        data = []
        if col == 'Size':
            data = [ (int(tree.set(iid, col)[:-3]), iid) for iid in tree.get_children('') ]
        elif col == 'Name': 
            data = [ (tree.set(iid, col).lower(), iid) for iid in tree.get_children('') ]
        else: 
            data = [ (tree.set(iid, col), iid) for iid in tree.get_children('') ]  

        data.sort(reverse=reverse)

        for i, (val, iid) in enumerate(data):
            tree.move(iid, '', i)

        tree.heading(col, command=lambda c=col: sort_tree_col(tree, c, not reverse))

    opt = StringVar()
    opt.set('contains')
    drop = OptionMenu(window, opt, 'contains', 'endswith', 'startswith')
    drop.place(x=920, y=0)

    browse_btn = Button(window, text='Browse', padx=10, command=lambda: engine.onClick(tree, opt, matchesLabel))
    browse_btn.place(x=705, y=3)

    reindex_btn = Button(window, text='Reindex', command=lambda: engine.reindex())
    reindex_btn.place(x=1115, y=3)

    searchByLabel = Label(window, text='Search Mode:')
    searchByLabel.place(x=820, y=7)

    tree.pack()
    window.mainloop()
