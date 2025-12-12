import os
import sys
import ctypes

# --- FAST STARTUP CHECK (Still needed for Manager) ---
def hide_console():
    """Hides the console window immediately."""
    try:
        whnd = ctypes.windll.kernel32.GetConsoleWindow()
        if whnd != 0:
            ctypes.windll.user32.ShowWindow(whnd, 0)
    except: pass

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() == 1
    except:
        return False

if __name__ == "__main__":
    hide_console()
    if len(sys.argv) > 1 and sys.argv[1].startswith("--"):
        # CLI Mode (Legacy or specific util)
        pass 
    else:
        # GUI Mode: Needs Admin for Symlinks
        if not is_admin():
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
            sys.exit(0)

import json
import xml.etree.ElementTree as ET
import subprocess
import socket
import webbrowser
import urllib.request
import re
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog

# Configuration
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "loader_config.json")
TAGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mod_tags.json")
MOD_CONFIG_PATH = os.path.expandvars(r"%APPDATA%\..\LocalLow\Nolla_Games_Noita\save00\mod_config.xml")
PRESETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "presets")

os.makedirs(PRESETS_DIR, exist_ok=True)

def load_tags():
    if os.path.exists(TAGS_FILE):
        try:
            with open(TAGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: pass
    return {}

def save_tags(tags_data):
    try:
        with open(TAGS_FILE, "w", encoding="utf-8") as f:
            json.dump(tags_data, f, indent=2, ensure_ascii=False)
    except: pass

TAGS_DATA = load_tags()

def load_settings():
    default_settings = {
        "noita_path": r"C:\Program Files (x86)\Steam\steamapps\common\Noita",
        "workshop_path": r"C:\Program Files (x86)\Steam\steamapps\workshop\content\881100",
        "mod_config_path": os.path.expandvars(r"%APPDATA%\..\LocalLow\Nolla_Games_Noita\save00\mod_config.xml")
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
                default_settings.update(data)
        except: pass
    return default_settings

def save_settings(settings):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(settings, f, indent=2)
    except: pass

SETTINGS = load_settings()
STEAM_NOITA_PATH = SETTINGS["noita_path"]
WORKSHOP_PATH = SETTINGS["workshop_path"]
MOD_CONFIG_PATH = SETTINGS["mod_config_path"]

# Helper to generate XML content
def generate_xml_content(mods_data):
    root = ET.Element("Mods")
    for mod in mods_data:
        clean = {k:v for k,v in mod.items() if not k.startswith('_')}
        # CRITICAL FIX: Force workshop_item_id to 0.
        # This tricks the game into treating Workshop mods as Local mods,
        # allowing them to load from the 'mods' folder (via symlinks) without Steam API.
        if 'workshop_item_id' in clean:
            clean['workshop_item_id'] = '0'
        ET.SubElement(root, "Mod", clean)
    return ET.tostring(root, encoding='utf-8', method='xml')

class DragManager:
    def __init__(self, tree, app):
        self.tree = tree
        self.app = app
        self.drag_item = None
        self.start_pos = None
        self.ghost_window = None
        self.line_window = None
        self.tree.bind("<ButtonPress-1>", self.on_press)
        self.tree.bind("<B1-Motion>", self.on_motion)
        self.tree.bind("<ButtonRelease-1>", self.on_release)

    def on_press(self, event):
        # Allow press even if searching, but we will block DRAG later
        region = self.tree.identify("region", event.x, event.y)
        if region == "tree" or region == "cell":
            # Always capture the item for potential drag OR click
            item = self.tree.identify_row(event.y)
            if item:
                self.drag_item = item
                self.start_pos = (event.x, event.y)

    def on_motion(self, event):
        if not self.drag_item: return
        
        # Disable dragging if search is active
        if self.app.search_var.get(): return

        # Drag Threshold (5 pixels) to prevent accidental drags when clicking
        if not self.ghost_window and self.start_pos:
            if abs(event.x - self.start_pos[0]) < 5 and abs(event.y - self.start_pos[1]) < 5:
                return

        if not self.ghost_window:
            text = self.tree.item(self.drag_item, "values")[0]
            self.ghost_window = tk.Toplevel(self.tree)
            self.ghost_window.overrideredirect(True)
            self.ghost_window.attributes("-alpha", 0.7)
            self.ghost_window.configure(bg="#333333")
            f = tk.Frame(self.ghost_window, bg="#444", borderwidth=1, relief="solid")
            f.pack()
            tk.Label(f, text=text, bg="#2d2d30", fg="white", font=("Segoe UI", 10), padx=10).pack()
        x = self.tree.winfo_rootx() + event.x + 15
        y = self.tree.winfo_rooty() + event.y + 5
        self.ghost_window.geometry(f"+{x}+{y}")
        self.ghost_window.lift()

        target = self.tree.identify_row(event.y)
        if target:
            bbox = self.tree.bbox(target)
            if bbox:
                row_y = bbox[1]
                row_h = bbox[3]
                is_below = (event.y - row_y) > (row_h / 2)
                line_y = self.tree.winfo_rooty() + row_y + (row_h if is_below else 0)
                line_x = self.tree.winfo_rootx()
                line_w = self.tree.winfo_width()
                if not self.line_window:
                    self.line_window = tk.Toplevel(self.tree)
                    self.line_window.overrideredirect(True)
                    self.line_window.configure(bg="white")
                    self.line_window.attributes("-topmost", True)
                self.line_window.geometry(f"{line_w}x2+{line_x}+{line_y}")
                self.line_window.lift()

    def on_release(self, event):
        was_drag = self.ghost_window is not None
        if self.ghost_window: self.ghost_window.destroy(); self.ghost_window=None
        if self.line_window: self.line_window.destroy(); self.line_window=None
        if not self.drag_item: return
        
        if not was_drag:
            self.app.handle_click(self.drag_item, event)
            self.drag_item = None
            return

        target = self.tree.identify_row(event.y)
        if target and target != self.drag_item:
            bbox = self.tree.bbox(target)
            if bbox:
                row_y = bbox[1]
                row_h = bbox[3]
                is_below = (event.y - row_y) > (row_h / 2)
                src_idx = self.app.get_item_index(self.drag_item)
                dst_idx = self.app.get_item_index(target)
                if src_idx is not None and dst_idx is not None:
                    if is_below: dst_idx += 1
                    if dst_idx > src_idx: dst_idx -= 1
                    item = self.app.mods_data.pop(src_idx)
                    self.app.mods_data.insert(dst_idx, item)
                    self.app.filtered_data = list(self.app.mods_data)
                    self.app.populate_tree()
                    self.app.save_config()
        self.drag_item = None

class NoitaLoader(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Noita 模组管理器")
        self.geometry("900x700")
        self.configure(bg="#1e1e1e")
        self.setup_style()
        
        self.check_paths()
        
        self.mods_data = []
        self.filtered_data = []
        self.create_ui()
        self.load_data()
        self.drag_manager = DragManager(self.tree, self)

    def check_paths(self):
        global STEAM_NOITA_PATH, WORKSHOP_PATH, MOD_CONFIG_PATH
        
        # Check if paths are valid
        noita_valid = os.path.exists(os.path.join(STEAM_NOITA_PATH, "noita.exe"))
        workshop_valid = os.path.exists(WORKSHOP_PATH)
        
        if not noita_valid or not workshop_valid:
            messagebox.showinfo("初次设置", "未检测到 Noita 或 创意工坊路径，请手动指定。")
            
            # Ask for Noita Path
            while not noita_valid:
                path = filedialog.askdirectory(title="请选择 Noita 游戏目录 (包含 noita.exe)")
                if not path: sys.exit(0) # User cancelled
                path = os.path.normpath(path)
                if os.path.exists(os.path.join(path, "noita.exe")):
                    STEAM_NOITA_PATH = path
                    SETTINGS["noita_path"] = path
                    noita_valid = True
                else:
                    messagebox.showerror("错误", "该目录下没有找到 noita.exe")

            # Ask for Workshop Path
            if not workshop_valid:
                guess = os.path.abspath(os.path.join(STEAM_NOITA_PATH, "..", "..", "workshop", "content", "881100"))
                if os.path.exists(guess):
                    WORKSHOP_PATH = guess
                    SETTINGS["workshop_path"] = guess
                    workshop_valid = True
            
            while not workshop_valid:
                path = filedialog.askdirectory(title="请选择 Noita 创意工坊目录 (Steam/steamapps/workshop/content/881100)")
                if not path: break
                path = os.path.normpath(path)
                if os.path.exists(path):
                    WORKSHOP_PATH = path
                    SETTINGS["workshop_path"] = path
                    workshop_valid = True
            
            save_settings(SETTINGS)

    def open_settings(self):
        win = tk.Toplevel(self)
        win.title("设置")
        win.geometry("600x250")
        win.configure(bg=self.colors["bg"])
        
        def create_row(parent, label, var, cmd):
            f = tk.Frame(parent, bg=self.colors["bg"], pady=5)
            f.pack(fill="x", padx=10)
            tk.Label(f, text=label, width=15, anchor="w", bg=self.colors["bg"], fg="white").pack(side="left")
            e = tk.Entry(f, textvariable=var, bg="#2d2d30", fg="white", relief="flat")
            e.pack(side="left", fill="x", expand=True, padx=5)
            ttk.Button(f, text="浏览", width=6, command=cmd).pack(side="right")

        v_noita = tk.StringVar(value=STEAM_NOITA_PATH)
        v_workshop = tk.StringVar(value=WORKSHOP_PATH)
        v_config = tk.StringVar(value=MOD_CONFIG_PATH)

        create_row(win, "Noita 目录:", v_noita, lambda: v_noita.set(filedialog.askdirectory() or v_noita.get()))
        create_row(win, "创意工坊目录:", v_workshop, lambda: v_workshop.set(filedialog.askdirectory() or v_workshop.get()))
        create_row(win, "配置文件路径:", v_config, lambda: v_config.set(filedialog.askopenfilename(filetypes=[("XML", "*.xml")]) or v_config.get()))

        def save():
            global STEAM_NOITA_PATH, WORKSHOP_PATH, MOD_CONFIG_PATH
            # Normalize paths to use system separator (backslash on Windows)
            SETTINGS["noita_path"] = os.path.normpath(v_noita.get())
            SETTINGS["workshop_path"] = os.path.normpath(v_workshop.get())
            SETTINGS["mod_config_path"] = os.path.normpath(v_config.get())
            
            STEAM_NOITA_PATH = SETTINGS["noita_path"]
            WORKSHOP_PATH = SETTINGS["workshop_path"]
            MOD_CONFIG_PATH = SETTINGS["mod_config_path"]
            
            save_settings(SETTINGS)
            self.load_data()
            messagebox.showinfo("成功", "设置已保存并重新加载")
            win.destroy()

        tk.Frame(win, bg=self.colors["bg"], height=20).pack()
        ttk.Button(win, text="保存设置", command=save).pack()

    def setup_style(self):
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.colors = {"bg": "#1e1e1e", "fg": "#cccccc", "list_bg": "#252526", "select_bg": "#094771", "btn": "#007acc", "btn_hover": "#0098ff"}
        self.style.configure(".", background=self.colors["bg"], foreground=self.colors["fg"], font=("Microsoft YaHei UI", 10))
        self.style.configure("TButton", padding=6, relief="flat", background=self.colors["btn"], foreground="white")
        self.style.map("TButton", background=[("active", self.colors["btn_hover"])])
        self.style.configure("Treeview", background=self.colors["list_bg"], foreground=self.colors["fg"], fieldbackground=self.colors["list_bg"], rowheight=30, borderwidth=0)
        self.style.map("Treeview", background=[("selected", self.colors["select_bg"])])
        self.style.layout("Treeview", [('Treeview.treearea', {'sticky': 'nswe'})]) 

    def create_ui(self):
        top_bar = tk.Frame(self, bg=self.colors["bg"], pady=10, padx=10)
        top_bar.pack(fill="x")
        tk.Label(top_bar, text="NOITA MODS", bg=self.colors["bg"], fg="white", font=("Microsoft YaHei UI", 14, "bold")).pack(side="left")
        
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self.on_search)
        search_frame = tk.Frame(top_bar, bg="#2d2d30", padx=5, pady=5)
        search_frame.pack(side="left", padx=20, fill="x", expand=True)
        entry_search = tk.Entry(search_frame, textvariable=self.search_var, bg="#2d2d30", fg="white", insertbackground="white", relief="flat", font=("Microsoft YaHei UI", 10))
        entry_search.pack(fill="x")

        toolbar = tk.Frame(self, bg=self.colors["bg"], padx=10, pady=5)
        toolbar.pack(fill="x")
        tk.Label(toolbar, text="预设:", bg=self.colors["bg"], fg=self.colors["fg"]).pack(side="left", padx=5)
        self.combo_presets = ttk.Combobox(toolbar, values=self.get_preset_list(), state="readonly", width=15)
        self.combo_presets.pack(side="left")
        self.combo_presets.bind("<<ComboboxSelected>>", self.load_preset)
        ttk.Button(toolbar, text="保存", width=6, command=self.save_preset_dialog).pack(side="left", padx=2)
        ttk.Button(toolbar, text="删除", width=6, command=self.delete_preset).pack(side="left", padx=2)
        # Normal Shortcut
        ttk.Button(toolbar, text="生成快捷方式", command=lambda: self.create_shortcut(dev=False)).pack(side="left", padx=2)
        # Dev Shortcut
        ttk.Button(toolbar, text="生成 Dev 快捷方式", command=lambda: self.create_shortcut(dev=True)).pack(side="left", padx=2)
        
        ttk.Button(toolbar, text="⚙ 设置", command=self.open_settings).pack(side="right", padx=5)
        # Normal Launch
        ttk.Button(toolbar, text="▶ 启动", command=lambda: self.launch_game(dev=False)).pack(side="right", padx=2)
        # Dev Launch
        ttk.Button(toolbar, text="▶ 启动 Dev", command=lambda: self.launch_game(dev=True)).pack(side="right", padx=2)
        
        ttk.Button(toolbar, text="↻ 同步", command=self.sync_mods).pack(side="right", padx=5)
        ttk.Button(toolbar, text="☁ 获取标签", command=self.fetch_tags).pack(side="right", padx=5)

        list_frame = tk.Frame(self, bg=self.colors["bg"], padx=10, pady=5)
        list_frame.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(list_frame, columns=("name", "type", "user_tags", "workshop_tags", "link"), selectmode="extended", show="headings")
        self.tree.heading("name", text="模组名称", anchor="w")
        self.tree.heading("type", text="类型", anchor="w")
        self.tree.heading("user_tags", text="用户标签", anchor="w")
        self.tree.heading("workshop_tags", text="工坊标签", anchor="w")
        self.tree.heading("link", text="创意工坊", anchor="center")
        
        self.tree.column("name", width=300)
        self.tree.column("type", width=100)
        self.tree.column("user_tags", width=150)
        self.tree.column("workshop_tags", width=150)
        self.tree.column("link", width=80, anchor="center")
        
        sb = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.tree.bind("<Double-1>", self.on_double_click)
        # self.tree.bind("<Button-1>", self.on_click) # Handled by DragManager

        # Tag Cloud Area
        tag_frame = tk.LabelFrame(self, text="标签云 (Ctrl+点击添加到搜索)", bg=self.colors["bg"], fg="white", padx=5, pady=5)
        tag_frame.pack(fill="x", padx=10, pady=5)
        self.tag_cloud_frame = tag_frame # Container
        
        # Use Text widget for wrapping tags
        self.tag_text = tk.Text(tag_frame, height=4, bg=self.colors["bg"], fg="white", relief="flat", wrap="word", cursor="arrow")
        self.tag_text.pack(fill="x")
        
        bottom = tk.Frame(self, bg=self.colors["bg"], pady=10, padx=10)
        bottom.pack(fill="x")
        ttk.Button(bottom, text="全选", command=lambda: self.set_all_enabled(True)).pack(side="left")
        ttk.Button(bottom, text="全不选", command=lambda: self.set_all_enabled(False)).pack(side="left", padx=5)
        self.status = tk.StringVar(value="就绪")
        tk.Label(bottom, textvariable=self.status, bg=self.colors["bg"], fg="#777", font=("Microsoft YaHei UI", 9)).pack(side="right")
        
        # Initial Tag Cloud Update
        self.after(100, self.update_tag_cloud)
        
        # Bind Ctrl+F
        self.bind("<Control-f>", self.show_find_bar)
        
    def show_find_bar(self, event=None):
        if hasattr(self, 'find_window') and self.find_window:
            self.find_window.lift()
            self.find_entry.focus_set()
            return

        self.find_window = tk.Toplevel(self)
        self.find_window.title("查找")
        self.find_window.geometry("400x50")
        self.find_window.configure(bg=self.colors["bg"])
        self.find_window.resizable(False, False)
        # Position relative to main window
        x = self.winfo_x() + self.winfo_width() - 420
        y = self.winfo_y() + 80
        self.find_window.geometry(f"+{x}+{y}")
        
        f = tk.Frame(self.find_window, bg=self.colors["bg"], padx=5, pady=10)
        f.pack(fill="both")
        
        tk.Label(f, text="查找:", bg=self.colors["bg"], fg="white").pack(side="left")
        self.find_entry = tk.Entry(f, bg="#2d2d30", fg="white", insertbackground="white")
        self.find_entry.pack(side="left", fill="x", expand=True, padx=5)
        self.find_entry.bind("<Return>", self.find_next)
        self.find_entry.bind("<Shift-Return>", self.find_prev)
        
        self.find_label = tk.Label(f, text="0/0", bg=self.colors["bg"], fg="#aaa", width=6)
        self.find_label.pack(side="left", padx=5)
        
        ttk.Button(f, text="↓", width=3, command=self.find_next).pack(side="left")
        ttk.Button(f, text="↑", width=3, command=self.find_prev).pack(side="left")
        
        self.find_entry.focus_set()
        
    def find_next(self, event=None):
        self._find(1)
        
    def find_prev(self, event=None):
        self._find(-1)
        
    def _find(self, direction):
        query = self.find_entry.get().lower()
        
        # Clear previous highlights
        for item in self.tree.get_children():
            tags = list(self.tree.item(item, "tags"))
            if "found" in tags:
                tags.remove("found")
                self.tree.item(item, tags=tags)

        if not query:
            self.find_label.config(text="0/0")
            return
        
        total = len(self.filtered_data)
        if total == 0: return
        
        # Find ALL matches
        matches = []
        for i, mod in enumerate(self.filtered_data):
            text = f"{mod.get('_display_name', '')} {','.join(mod.get('user_tags', []))} {','.join(mod.get('workshop_tags', []))}".lower()
            if query in text:
                matches.append(str(i))
        
        if not matches:
            self.find_label.config(text="0/0")
            return

        # Highlight ALL matches
        # self.tree.selection_set(matches) # Don't select, just highlight
        for m in matches:
            tags = list(self.tree.item(m, "tags"))
            if "found" not in tags:
                tags.append("found")
                self.tree.item(m, tags=tags)
        
        # Navigate
        # Get current focus or first selection
        current = self.tree.focus()
        if current in matches:
            curr_idx = matches.index(current)
            next_idx = (curr_idx + direction) % len(matches)
            target = matches[next_idx]
        else:
            target = matches[0] if direction > 0 else matches[-1]
            
        self.tree.focus(target)
        self.tree.see(target)
        self.find_label.config(text=f"{matches.index(target)+1}/{len(matches)}")

    def on_search(self, *args):
        query = self.search_var.get().lower().strip()
        if not query:
            self.filtered_data = list(self.mods_data)
        else:
            # Parse Query
            # Terms separated by space are AND
            # Terms separated by | are OR (within a term group)
            # Terms starting with # are Tags
            
            terms = query.split()
            self.filtered_data = []
            
            for mod in self.mods_data:
                match_all = True
                for term in terms:
                    # Handle Negation (e.g. -#tag or -name)
                    is_negation = term.startswith('-')
                    if is_negation:
                        term = term[1:]
                        if not term: continue # Skip empty negation

                    # Handle OR logic (e.g. #magic|#item)
                    sub_terms = term.split('|')
                    match_any = False
                    
                    for sub in sub_terms:
                        sub = sub.strip()
                        if not sub: continue
                        is_tag = sub.startswith('#')
                        clean_sub = sub[1:] if is_tag else sub
                        
                        if is_tag:
                            # Check tags
                            mod_tags = [t.lower().strip() for t in mod.get('user_tags', []) + mod.get('workshop_tags', [])]
                            if any(clean_sub in t for t in mod_tags):
                                match_any = True
                                break
                        elif sub.startswith('@'):
                            # Name Only Search (e.g. @magic)
                            clean_name_sub = sub[1:]
                            name = mod.get('_display_name', mod['name']).lower()
                            if clean_name_sub in name:
                                match_any = True
                                break
                        else:
                            # Default: Check Name OR Tags
                            name = mod.get('_display_name', mod['name']).lower()
                            mod_tags = [t.lower().strip() for t in mod.get('user_tags', []) + mod.get('workshop_tags', [])]
                            
                            # Check Name
                            if clean_sub in name:
                                match_any = True
                            # Check Tags
                            elif any(clean_sub in t for t in mod_tags):
                                match_any = True
                                
                            if match_any: break
                    
                    # Logic:
                    # Normal: If NOT match_any -> Fail
                    # Negation: If match_any -> Fail
                    if is_negation:
                        if match_any:
                            match_all = False
                            break
                    else:
                        if not match_any:
                            match_all = False
                            break
                
                if match_all:
                    self.filtered_data.append(mod)

        self.populate_tree()
        self.update_tag_cloud()

    def update_tag_cloud(self):
        # Collect all tags from visible mods
        tags = set()
        for mod in self.mods_data:
            # Ensure tags are stripped
            tags.update([t.strip() for t in mod.get('user_tags', []) if t.strip()])
            tags.update([t.strip() for t in mod.get('workshop_tags', []) if t.strip()])
        
        sorted_tags = sorted(list(tags))
        
        self.tag_text.config(state="normal")
        self.tag_text.delete("1.0", "end")
        
        if not sorted_tags:
            self.tag_text.insert("end", "暂无标签 (点击 '获取标签' 或手动添加)")
        
        for tag in sorted_tags:
            # Create a label that looks like a chip
            btn = tk.Label(self.tag_text, text=f" {tag} ", bg="#3e3e42", fg="#dcdcdc", cursor="hand2", relief="flat", padx=4, pady=2)
            btn.bind("<Button-1>", lambda e, t=tag: self.add_tag_to_search(t))
            self.tag_text.window_create("end", window=btn, padx=4, pady=4)
            
        self.tag_text.config(state="disabled")

    def add_tag_to_search(self, tag):
        current = self.search_var.get().strip()
        tag_str = f"#{tag}"
        if tag_str not in current:
            if current: current += " "
            self.search_var.set(current + tag_str)

    def build_workshop_map(self):
        """Scans Workshop config to map ModFolderName -> WorkshopID"""
        id_map = {}
        if os.path.exists(WORKSHOP_PATH):
            for item_id in os.listdir(WORKSHOP_PATH):
                # Item ID usually numeric
                if not item_id.isdigit(): continue
                
                mod_path = os.path.join(WORKSHOP_PATH, item_id)
                if not os.path.isdir(mod_path): continue
                
                # Check mod_id.txt for the folder name Noita uses
                mid_txt = os.path.join(mod_path, "mod_id.txt")
                if os.path.exists(mid_txt):
                    try:
                        name = open(mid_txt, "r", encoding="utf-8", errors="ignore").read().strip()
                        if name:
                            # Store lowercase name for case-insensitive lookup
                            id_map[name.lower()] = item_id
                    except: pass
        return id_map

    def load_data(self):
        self.mods_data = []
        # 0. Build Workshop Map (The Robust Way)
        workshop_map = self.build_workshop_map()

        # 1. Parse Config
        if os.path.exists(MOD_CONFIG_PATH):
            try:
                tree = ET.parse(MOD_CONFIG_PATH)
                root = tree.getroot()
                for mod in root.findall('Mod'):
                    self.mods_data.append(mod.attrib)
            except: pass
        
        # 2. Scan Filesystem
        local_mods = os.path.join(STEAM_NOITA_PATH, "mods")
        if os.path.exists(local_mods):
            # Use lowercase map for case-insensitive matching
            existing_map = {m['name'].lower(): m for m in self.mods_data}
            
            for d in os.listdir(local_mods):
                path = os.path.join(local_mods, d)
                if os.path.isdir(path):
                    # Check if it is a symlink
                    is_link = os.path.islink(path)
                    
                    # Get Display Name
                    disp = d
                    try:
                        mxml = os.path.join(path, "mod.xml")
                        if os.path.exists(mxml): disp = ET.parse(mxml).getroot().attrib.get('name', d)
                    except: pass
                    
                    # Resolve ID using Map (Case Insensitive)
                    d_lower = d.lower()
                    wid = workshop_map.get(d_lower, '0')
                    
                    if d_lower in existing_map:
                        mod = existing_map[d_lower]
                        mod['_display_name'] = disp
                        mod['_is_link'] = is_link
                        # Update ID if missing
                        if mod.get('workshop_item_id', '0') == '0' and wid != '0':
                             mod['workshop_item_id'] = wid
                    else:
                        self.mods_data.append({
                            'name': d,
                            'enabled': '0',
                            'workshop_item_id': wid,
                            '_display_name': disp,
                            '_is_link': is_link
                        })
        
        # Merge Tags
        for mod in self.mods_data:
            key = mod['name']
            if key in TAGS_DATA:
                mod['user_tags'] = [t.strip() for t in TAGS_DATA[key].get('user_tags', []) if t.strip()]
                mod['workshop_tags'] = [t.strip() for t in TAGS_DATA[key].get('workshop_tags', []) if t.strip()]
            else:
                mod['user_tags'] = []
                mod['workshop_tags'] = []

        self.filtered_data = list(self.mods_data)
        self.populate_tree()
        self.update_tag_cloud()

    def populate_tree(self):
        self.tree.delete(*self.tree.get_children())
        # Style for link
        self.tree.tag_configure("mylink", foreground="#4da6ff") # Light Blue
        self.tree.tag_configure("local", foreground="#aaaaaa")
        self.tree.tag_configure("workshop", foreground="#dddddd")
        self.tree.tag_configure("linked", foreground="#00ff00") # Green for linked
        self.tree.tag_configure("found", background="#663300") # Brighter Orange Highlight

        for i, mod in enumerate(self.filtered_data):
            enabled = mod.get('enabled') == '1'
            prefix = "☑ " if enabled else "☐ "
            
            name = prefix + mod.get('_display_name', mod['name'])
            wid = mod.get('workshop_item_id', '0')
            is_link = mod.get('_is_link', False)
            
            # Determine Type String
            if wid != '0':
                if is_link:
                    type_str = "工坊 (软链接)"
                    row_tag = "linked"
                else:
                    type_str = "工坊 (本地副本)"
                    row_tag = "workshop"
            else:
                type_str = "本地模组"
                row_tag = "local"

            link_txt = "Steam" if wid != '0' else "-"
            
            u_tags = ", ".join(mod.get('user_tags', []))
            w_tags = ", ".join(mod.get('workshop_tags', []))

            # Combine tags
            tags = [row_tag]
            if wid != '0': tags.append("mylink")
            
            self.tree.insert("", "end", iid=str(i), values=(name, type_str, u_tags, w_tags, link_txt), tags=tags)

    def get_item_index(self, item_id):
        try: return int(item_id)
        except: return None
    def on_double_click(self, event):
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell": return
        
        col = self.tree.identify_column(event.x)
        item_id = self.tree.identify_row(event.y)
        if not item_id: return
        
        mod_idx = int(item_id)
        mod = self.filtered_data[mod_idx]

        # Column #1: Toggle Checkbox (Name column)
        if col == "#1":
            curr = mod.get('enabled', '0')
            mod['enabled'] = '1' if curr == '0' else '0'
            self.populate_tree()
            self.save_config()
            
        # Column #3: User Tags, #4: Workshop Tags
        elif col in ("#3", "#4"):
            self.edit_cell(item_id, col, mod)

    def edit_cell(self, item_id, col, mod):
        try:
            bbox = self.tree.bbox(item_id, column=col)
            if not bbox: return
            x, y, w, h = bbox
        except: return

        # Close existing editor if any
        if hasattr(self, 'editor_win') and self.editor_win:
            self.editor_win.destroy()

        key = 'user_tags' if col == "#3" else 'workshop_tags'
        
        # Calculate screen coordinates
        root_x = self.tree.winfo_rootx() + x
        root_y = self.tree.winfo_rooty() + y
        
        # Create Overlay Window
        self.editor_win = tk.Toplevel(self)
        self.editor_win.overrideredirect(True)
        # Use a slightly larger height to allow flow layout to show multiple lines if needed
        # But keep width matched to cell
        editor_h = max(h, 100)
        self.editor_win.geometry(f"{w}x{editor_h}+{root_x}+{root_y}")
        self.editor_win.configure(bg=self.colors["bg"])
        self.editor_win.attributes("-topmost", True)
        
        # Container for tags (Flow layout using Text widget)
        container = tk.Text(self.editor_win, bg=self.colors["bg"], fg="white", relief="flat", wrap="word", cursor="arrow")
        container.pack(fill="both", expand=True, padx=2, pady=2)
        
        def save_changes():
            mod_name = mod['name']
            if mod_name not in TAGS_DATA: TAGS_DATA[mod_name] = {}
            TAGS_DATA[mod_name][key] = mod.get(key, [])
            save_tags(TAGS_DATA)
            self.populate_tree()
            self.update_tag_cloud()

        def render():
            container.config(state="normal")
            container.delete("1.0", "end")
            
            tags = mod.get(key, [])
            for i, tag in enumerate(tags):
                # Tag Chip Frame
                f = tk.Frame(container, bg="#3e3e42", pady=1, padx=2)
                
                # Tag Label
                lbl = tk.Label(f, text=tag, bg="#3e3e42", fg="#dcdcdc", font=("Segoe UI", 9))
                lbl.pack(side="left")
                
                # Delete Button (small x)
                x_btn = tk.Label(f, text="✕", bg="#3e3e42", fg="#ff5555", cursor="hand2", font=("Segoe UI", 7))
                x_btn.pack(side="left", padx=(2, 0))
                x_btn.bind("<Button-1>", lambda e, idx=i: delete_tag(idx))
                
                # Bind Double Click on Label and Frame to Edit
                lbl.bind("<Double-Button-1>", lambda e, idx=i: start_edit(idx))
                f.bind("<Double-Button-1>", lambda e, idx=i: start_edit(idx))
                
                container.window_create("end", window=f, padx=2, pady=2)
            
            # Add "+" Button
            add_btn = tk.Label(container, text=" + ", bg="#2d2d30", fg="#4da6ff", cursor="hand2", font=("Segoe UI", 10, "bold"), relief="solid", borderwidth=1)
            add_btn.bind("<Button-1>", lambda e: start_add())
            container.window_create("end", window=add_btn, padx=2, pady=2)
            
            container.config(state="disabled")

        def delete_tag(index):
            tags = mod.get(key, [])
            if 0 <= index < len(tags):
                tags.pop(index)
                save_changes()
                render()

        def start_edit(index):
            container.config(state="normal")
            container.delete("1.0", "end")
            
            tags = mod.get(key, [])
            for i, tag in enumerate(tags):
                if i == index:
                    # Render Entry
                    e = tk.Entry(container, bg="#252526", fg="white", font=("Segoe UI", 9), width=max(5, len(tag)+2))
                    e.insert(0, tag)
                    e.select_range(0, "end")
                    e.bind("<Return>", lambda event, idx=i, entry=e: finish_edit(idx, entry))
                    e.bind("<FocusOut>", lambda event, idx=i, entry=e: finish_edit(idx, entry))
                    container.window_create("end", window=e, padx=2, pady=2)
                    e.focus_set()
                else:
                    # Render Chip
                    f = tk.Frame(container, bg="#3e3e42", pady=1, padx=2)
                    lbl = tk.Label(f, text=tag, bg="#3e3e42", fg="#dcdcdc", font=("Segoe UI", 9))
                    lbl.pack(side="left")
                    x_btn = tk.Label(f, text="✕", bg="#3e3e42", fg="#ff5555", cursor="hand2", font=("Segoe UI", 7))
                    x_btn.pack(side="left", padx=(2, 0))
                    x_btn.bind("<Button-1>", lambda e, idx=i: delete_tag(idx))
                    lbl.bind("<Double-Button-1>", lambda e, idx=i: start_edit(idx))
                    f.bind("<Double-Button-1>", lambda e, idx=i: start_edit(idx))
                    container.window_create("end", window=f, padx=2, pady=2)
            
            container.config(state="disabled")

        def finish_edit(index, entry):
            entry.unbind("<Return>")
            entry.unbind("<FocusOut>")
            new_text = entry.get().strip()
            
            tags = mod.get(key, [])
            if index >= len(tags):
                render()
                return
            
            if new_text:
                if new_text not in tags or tags.index(new_text) == index:
                    tags[index] = new_text
                    save_changes()
            else:
                tags.pop(index)
                save_changes()
            render()

        def start_add():
            container.config(state="normal")
            container.delete("1.0", "end")
            tags = mod.get(key, [])
            for i, tag in enumerate(tags):
                f = tk.Frame(container, bg="#3e3e42", pady=1, padx=2)
                lbl = tk.Label(f, text=tag, bg="#3e3e42", fg="#dcdcdc", font=("Segoe UI", 9))
                lbl.pack(side="left")
                x_btn = tk.Label(f, text="✕", bg="#3e3e42", fg="#ff5555", cursor="hand2", font=("Segoe UI", 7))
                x_btn.pack(side="left", padx=(2, 0))
                x_btn.bind("<Button-1>", lambda e, idx=i: delete_tag(idx))
                lbl.bind("<Double-Button-1>", lambda e, idx=i: start_edit(idx))
                f.bind("<Double-Button-1>", lambda e, idx=i: start_edit(idx))
                container.window_create("end", window=f, padx=2, pady=2)
            
            # New Entry
            e = tk.Entry(container, bg="#252526", fg="white", font=("Segoe UI", 9), width=8)
            e.bind("<Return>", lambda event, entry=e: finish_add(entry))
            e.bind("<FocusOut>", lambda event, entry=e: finish_add(entry))
            container.window_create("end", window=e, padx=2, pady=2)
            e.focus_set()
            
            container.config(state="disabled")

        def finish_add(entry):
            entry.unbind("<Return>")
            entry.unbind("<FocusOut>")
            new_text = entry.get().strip()
            
            if new_text:
                tags = mod.get(key, [])
                if key not in mod: mod[key] = []
                if new_text not in mod[key]:
                    mod[key].append(new_text)
                    save_changes()
            render()

        def check_focus(event):
            # If focus moved to something that is NOT a child of editor_win, close
            focused = self.focus_get()
            if not focused or str(self.editor_win) not in str(focused):
                self.editor_win.destroy()
                self.editor_win = None

        self.editor_win.bind("<FocusOut>", check_focus)
        self.editor_win.bind("<Escape>", lambda e: self.editor_win.destroy())
        
        render()
        self.editor_win.focus_set()

    def fetch_tags(self):
        if not messagebox.askyesno("获取标签", "这将联网获取所有工坊模组的标签，可能需要几分钟。\n是否继续？"):
            return
            
        self.status.set("正在获取标签...")
        self.update()
        
        count = 0
        total = len(self.mods_data)
        
        for i, mod in enumerate(self.mods_data):
            wid = mod.get('workshop_item_id', '0')
            if wid != '0':
                self.status.set(f"正在获取 ({i+1}/{total}): {mod.get('_display_name', '')}")
                self.update()
                
                try:
                    url = f"https://steamcommunity.com/sharedfiles/filedetails/?id={wid}"
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req, timeout=10) as response:
                        html = response.read().decode('utf-8', errors='ignore')
                        
                        tags = set()
                        
                        # Method 1: Regex for requiredtags parameter
                        # Matches: requiredtags[]=Tag (and url encoded versions)
                        found_tags = re.findall(r'requiredtags(?:%5B|\[)(?:%5D|\])=([^"&]+)', html)
                        for t in found_tags:
                            decoded = urllib.request.unquote(t).replace('+', ' ')
                            tags.add(decoded)
                        
                        if tags:
                            mod_name = mod['name']
                            if mod_name not in TAGS_DATA: TAGS_DATA[mod_name] = {}
                            
                            # Merge with existing workshop tags
                            existing = set([t.strip() for t in TAGS_DATA[mod_name].get('workshop_tags', []) if t.strip()])
                            existing.update([t.strip() for t in tags if t.strip()])
                            TAGS_DATA[mod_name]['workshop_tags'] = list(existing)
                            mod['workshop_tags'] = list(existing)
                            count += 1
                except Exception as e:
                    print(f"Failed to fetch {wid}: {e}")
        
        save_tags(TAGS_DATA)
        self.populate_tree()
        self.update_tag_cloud()
        self.status.set(f"标签获取完成，更新了 {count} 个模组")
        messagebox.showinfo("完成", f"已更新 {count} 个模组的标签")

    def handle_click(self, item_id, event):
        col = self.tree.identify_column(event.x)
        
        # Column #1: Toggle Checkbox
        if col == "#1":
            mod = self.filtered_data[int(item_id)]
            curr = mod.get('enabled', '0')
            new_state = '1' if curr == '0' else '0'
            mod['enabled'] = new_state
            self.populate_tree()
            self.save_config()
            self.status.set(f"已{'启用' if new_state=='1' else '禁用'}: {mod.get('_display_name', mod['name'])}")
            
        # Column #5: Steam Link
        elif col == "#5":
            mod = self.filtered_data[int(item_id)]
            if mod.get('workshop_item_id', '0') != '0':
                webbrowser.open(f"https://steamcommunity.com/sharedfiles/filedetails/?id={mod['workshop_item_id']}")

    def set_all_enabled(self, state):
        val = '1' if state else '0'
        for m in self.filtered_data: m['enabled'] = val
        self.populate_tree()
        self.save_config()

    def save_config(self):
        # Save to mod_config.xml
        xml_bytes = generate_xml_content(self.mods_data)
        try:
            with open(MOD_CONFIG_PATH, "wb") as f:
                f.write(b'<?xml version="1.0" encoding="utf-8"?>\n')
                f.write(xml_bytes)
                f.flush()
                os.fsync(f.fileno())
            self.status.set("配置已保存 (立即生效)")
        except Exception as e:
            self.status.set(f"保存失败: {e}")

    def sync_mods(self):
        self.status.set("正在同步...")
        if not os.path.exists(WORKSHOP_PATH): return messagebox.showerror("错误", "找不到创意工坊目录")
        
        # Ask user if they want to convert existing copies to links
        convert_copies = messagebox.askyesno("同步选项", "是否将已存在的'本地副本'转换为'软链接'?\n(推荐：可以节省空间并保持自动更新)")
        
        count = 0
        converted = 0
        local_mods = os.path.join(STEAM_NOITA_PATH, "mods")
        
        for item in os.listdir(WORKSHOP_PATH):
            src = os.path.join(WORKSHOP_PATH, item)
            if os.path.isdir(src):
                target_name = item
                mid = os.path.join(src, "mod_id.txt")
                if os.path.exists(mid):
                    try: target_name = open(mid).read().strip() or item
                    except: pass
                
                dst = os.path.join(local_mods, target_name)
                
                # Case 1: Destination does not exist -> Create Link
                if not os.path.exists(dst):
                    try:
                        self.create_junction(src, dst)
                        count += 1
                    except: pass
                
                # Case 2: Destination exists and is NOT a link (Copy) -> Convert if requested
                elif convert_copies and not os.path.islink(dst):
                    try:
                        # Backup? No, just remove and link.
                        # Use rmdir /s /q for directory
                        subprocess.run(f'rmdir /s /q "{dst}"', shell=True, check=True, creationflags=0x08000000)
                        self.create_junction(src, dst)
                        converted += 1
                    except Exception as e:
                        print(f"Failed to convert {dst}: {e}")

        self.status.set(f"同步完成: 新增 {count} 个, 转换 {converted} 个")
        self.load_data()

    def create_junction(self, src, dst):
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        subprocess.run(f'mklink /J "{dst}" "{src}"', shell=True, check=True, startupinfo=si, creationflags=0x08000000)

    def get_preset_list(self):
        return [f.replace(".json", "") for f in os.listdir(PRESETS_DIR) if f.endswith(".json")]

    def save_preset_dialog(self):
        name = simpledialog.askstring("保存预设", "输入预设名称:")
        if name:
            # 1. Save JSON (for Manager)
            json_path = os.path.join(PRESETS_DIR, f"{name}.json")
            with open(json_path, "w") as f: json.dump(self.mods_data, f, indent=2)
            
            # 2. Save XML (for Launcher)
            xml_path = os.path.join(PRESETS_DIR, f"{name}.xml")
            with open(xml_path, "wb") as f:
                f.write(b'<?xml version="1.0" encoding="utf-8"?>\n')
                f.write(generate_xml_content(self.mods_data))

            self.combo_presets['values'] = self.get_preset_list()
            self.combo_presets.set(name)
            messagebox.showinfo("成功", f"预设 '{name}' 已保存 (JSON + XML)")

    def load_preset(self, event=None):
        name = self.combo_presets.get()
        if not name: return
        path = os.path.join(PRESETS_DIR, f"{name}.json")
        if os.path.exists(path):
            try:
                with open(path) as f: self.mods_data = json.load(f)
                
                # Re-apply global tags to the loaded preset data
                for mod in self.mods_data:
                    key = mod['name']
                    if key in TAGS_DATA:
                        mod['user_tags'] = [t.strip() for t in TAGS_DATA[key].get('user_tags', []) if t.strip()]
                        mod['workshop_tags'] = [t.strip() for t in TAGS_DATA[key].get('workshop_tags', []) if t.strip()]
                    else:
                        mod['user_tags'] = []
                        mod['workshop_tags'] = []

                self.filtered_data = list(self.mods_data)
                self.populate_tree()
                self.update_tag_cloud()
                self.save_config()
                self.status.set(f"已加载预设: {name}")
            except Exception as e: messagebox.showerror("错误", str(e))

    def delete_preset(self):
        name = self.combo_presets.get()
        if confirm := messagebox.askyesno("确认", f"删除预设 '{name}'?"):
            try: os.remove(os.path.join(PRESETS_DIR, f"{name}.json"))
            except: pass
            try: os.remove(os.path.join(PRESETS_DIR, f"{name}.xml"))
            except: pass
            
            self.combo_presets['values'] = self.get_preset_list()
            self.combo_presets.set("")

    def create_shortcut(self, dev=False):
        name = self.combo_presets.get()
        if not name: return messagebox.showwarning("警告", "请先选择一个预设")
        
        # 1. Ensure Preset XML Exists
        xml_path = os.path.join(PRESETS_DIR, f"{name}.xml")
        if not os.path.exists(xml_path):
             # Regenerate if missing
             with open(xml_path, "wb") as f:
                f.write(b'<?xml version="1.0" encoding="utf-8"?>\n')
                f.write(generate_xml_content(self.mods_data))

        # 2. Generate Batch Launcher
        suffix = "_Dev" if dev else ""
        exe_name = "noita_dev.exe" if dev else "noita.exe"
        
        # Determine Target Config Path
        if dev:
            # Dev uses save00 inside game folder
            target_config = os.path.join(STEAM_NOITA_PATH, "save00", "mod_config.xml")
            # Ensure save00 exists
            os.makedirs(os.path.dirname(target_config), exist_ok=True)
        else:
            target_config = MOD_CONFIG_PATH

        bat_name = f"Launch_{name}{suffix}.bat"
        bat_path = os.path.join(PRESETS_DIR, bat_name)
        
        noita_exe = os.path.join(STEAM_NOITA_PATH, exe_name)
        
        bat_content = f"""@echo off
copy /y "{xml_path}" "{target_config}" >nul
start "" "{noita_exe}"
exit
"""
        with open(bat_path, "w") as f:
            f.write(bat_content)
            
        # 3. Create Shortcut to the BATCH file
        desktop = os.path.expanduser("~/Desktop")
        lnk_name = f"Noita{suffix} - {name}.lnk"
        lnk_path = os.path.join(desktop, lnk_name)
        
        ps_script = f"""
        $w = New-Object -ComObject WScript.Shell
        $s = $w.CreateShortcut('{lnk_path}')
        $s.TargetPath = '{bat_path}'
        $s.WorkingDirectory = '{STEAM_NOITA_PATH}'
        $s.WindowStyle = 7
        $s.Save()
        """
        
        try:
            subprocess.run(["powershell", "-Command", ps_script], check=True, creationflags=0x08000000)
            messagebox.showinfo("成功", f"快捷方式已创建:\n{lnk_path}")
        except Exception as e: messagebox.showerror("错误", str(e))

    def launch_game(self, dev=False):
        exe_name = "noita_dev.exe" if dev else "noita.exe"
        exe = os.path.join(STEAM_NOITA_PATH, exe_name)
        
        # Save config to the appropriate location before launching
        if dev:
            target_config = os.path.join(STEAM_NOITA_PATH, "save00", "mod_config.xml")
            os.makedirs(os.path.dirname(target_config), exist_ok=True)
        else:
            target_config = MOD_CONFIG_PATH
            
        # Write current mods_data to target config
        try:
            xml_bytes = generate_xml_content(self.mods_data)
            with open(target_config, "wb") as f:
                f.write(b'<?xml version="1.0" encoding="utf-8"?>\n')
                f.write(xml_bytes)
                f.flush()
                os.fsync(f.fileno())
        except Exception as e:
            messagebox.showerror("错误", f"保存配置失败: {e}")
            return

        if os.path.exists(exe):
            # For Dev build, we want the console (CREATE_NEW_CONSOLE = 0x00000010)
            # For Normal build, we want to detach/hide console (DETACHED_PROCESS = 0x00000008)
            flags = 0x00000010 if dev else 0x00000008
            subprocess.Popen([exe], cwd=STEAM_NOITA_PATH, creationflags=flags)
        else:
            messagebox.showerror("错误", f"找不到 {exe_name}")

def main():
    sock = get_single_instance_lock()
    if not sock: sys.exit(0)
    hide_console()
    app = NoitaLoader()
    app.mainloop()

def get_single_instance_lock():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('127.0.0.1', 49152)) 
        return s
    except socket.error: return None

if __name__ == "__main__":
    main()
