
import os
import sys
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading

try:
    import matplotlib
    matplotlib.use("TkAgg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


INSTRUCTOR_COLORS = [
    "#4E79A7", "#F28E2B", "#E15759", "#76B7B2",
    "#59A14F", "#EDC948", "#B07AA1", "#FF9DA7",
    "#9C755F", "#BAB0AC",
]

EMPTY_COLOR  = "#2B2D42"
HEADER_COLOR = "#1A1B2E"
BG_COLOR     = "#0F111A"
FG_COLOR     = "#E0E0E0"
ACCENT       = "#7B68EE"
CARD_BG      = "#1E2030"


class TimetableGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("AI2002 — CSP Timetabling Visualiser")
        self.root.geometry("1280x800")
        self.root.configure(bg=BG_COLOR)

        self.input_dir   = tk.StringVar(value=os.path.join(os.path.dirname(__file__), "data"))
        self.algorithm   = tk.StringVar(value="mac")
        self.var_h       = tk.StringVar(value="mrv_degree")
        self.val_h       = tk.StringVar(value="lcv")
        self.status_text = tk.StringVar(value="Ready.")

        self.csp         = None
        self.meta        = None
        self.assignment  = None
        self.metrics     = None
        self.events      = []
        self.event_idx   = 0
        self.exp_thread  = None

        self._setup_style()
        self._build_ui()

    def _setup_style(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TNotebook",          background=BG_COLOR,  borderwidth=0)
        style.configure("TNotebook.Tab",      background=CARD_BG,   foreground=FG_COLOR,
                        padding=[12, 6],      font=("Segoe UI", 10, "bold"))
        style.map("TNotebook.Tab",
                  background=[("selected", ACCENT)],
                  foreground=[("selected", "white")])
        style.configure("TFrame",   background=BG_COLOR)
        style.configure("TLabel",   background=BG_COLOR,  foreground=FG_COLOR, font=("Segoe UI", 10))
        style.configure("TButton",  background=ACCENT,    foreground="white",
                        font=("Segoe UI", 10, "bold"), padding=[8, 4])
        style.map("TButton", background=[("active", "#9B8BFF")])
        style.configure("TCombobox", fieldbackground=CARD_BG, background=CARD_BG,
                        foreground=FG_COLOR,  selectbackground=ACCENT)

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        # Top control bar
        ctrl_frame = tk.Frame(self.root, bg=HEADER_COLOR, pady=8, padx=12)
        ctrl_frame.pack(fill=tk.X)

        tk.Label(ctrl_frame, text="📅 AI2002 Timetabling CSP",
                 bg=HEADER_COLOR, fg=ACCENT,
                 font=("Segoe UI", 14, "bold")).pack(side=tk.LEFT, padx=8)

        tk.Label(ctrl_frame, text="Dir:", bg=HEADER_COLOR, fg=FG_COLOR,
                 font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(20, 2))
        tk.Entry(ctrl_frame, textvariable=self.input_dir, width=28,
                 bg=CARD_BG, fg=FG_COLOR, insertbackground=FG_COLOR,
                 font=("Segoe UI", 10)).pack(side=tk.LEFT)
        ttk.Button(ctrl_frame, text="Browse", command=self._browse_dir).pack(side=tk.LEFT, padx=4)

        tk.Label(ctrl_frame, text="Algorithm:", bg=HEADER_COLOR, fg=FG_COLOR,
                 font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(12, 2))
        ttk.Combobox(ctrl_frame, textvariable=self.algorithm, width=16,
                     values=["backtrack", "forward_checking", "mac", "min_conflicts"],
                     state="readonly").pack(side=tk.LEFT)

        tk.Label(ctrl_frame, text="VarH:", bg=HEADER_COLOR, fg=FG_COLOR,
                 font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(8, 2))
        ttk.Combobox(ctrl_frame, textvariable=self.var_h, width=12,
                     values=["none", "mrv", "mrv_degree"],
                     state="readonly").pack(side=tk.LEFT)

        tk.Label(ctrl_frame, text="ValH:", bg=HEADER_COLOR, fg=FG_COLOR,
                 font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(8, 2))
        ttk.Combobox(ctrl_frame, textvariable=self.val_h, width=8,
                     values=["none", "lcv"],
                     state="readonly").pack(side=tk.LEFT)

        ttk.Button(ctrl_frame, text="▶  Solve", command=self._run_solve).pack(side=tk.LEFT, padx=16)

        # Status bar
        status_bar = tk.Label(self.root, textvariable=self.status_text,
                              bg=CARD_BG, fg="#88FF88", font=("Segoe UI", 9),
                              anchor="w", padx=10)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)

        # Notebook tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        self.tab_grid  = ttk.Frame(self.notebook)
        self.tab_anim  = ttk.Frame(self.notebook)
        self.tab_stats = ttk.Frame(self.notebook)
        self.tab_exps  = ttk.Frame(self.notebook)
        self.tab_edit  = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_grid,  text="📋  Schedule Grid")
        self.notebook.add(self.tab_anim,  text="🎬  Search Animation")
        self.notebook.add(self.tab_stats, text="📊  Statistics")
        self.notebook.add(self.tab_exps,  text="🧪  Experiments")
        self.notebook.add(self.tab_edit,  text="✏️   Data Editor")

        self._build_tab_grid()
        self._build_tab_animation()
        self._build_tab_stats()
        self._build_tab_experiments()
        self._build_tab_editor()

    # ------------------------------------------------------------------
    # Tab 1: Schedule Grid
    # ------------------------------------------------------------------

    def _build_tab_grid(self):
        self.grid_canvas_frame = tk.Frame(self.tab_grid, bg=BG_COLOR)
        self.grid_canvas_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(self.grid_canvas_frame,
                 text="Run 'Solve' to see the schedule grid.",
                 bg=BG_COLOR, fg="#888888", font=("Segoe UI", 12)).pack(expand=True)

    def _draw_grid(self):
        for w in self.grid_canvas_frame.winfo_children():
            w.destroy()

        if not self.assignment or not self.meta:
            tk.Label(self.grid_canvas_frame, text="No solution to display.",
                     bg=BG_COLOR, fg="#888888", font=("Segoe UI", 12)).pack(expand=True)
            return

        assignment = self.assignment
        meta       = self.meta
        slots_df   = meta['slots_df']
        rooms_df   = meta['rooms_df']
        courses_df = meta['courses_df']

        slot_ids = list(slots_df['SlotID'])
        room_ids = list(rooms_df['RoomID'])

        # Build lookup
        grid = {}
        for var, (slot_id, room_id) in assignment.items():
            grid[(slot_id, room_id)] = var

        # Instructor colour map
        instructors = list(courses_df['Instructor'].unique())
        instr_color = {instr: INSTRUCTOR_COLORS[i % len(INSTRUCTOR_COLORS)]
                       for i, instr in enumerate(instructors)}

        # Scrollable canvas
        container = tk.Frame(self.grid_canvas_frame, bg=BG_COLOR)
        container.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(container, bg=BG_COLOR, highlightthickness=0)
        vscroll = ttk.Scrollbar(container, orient="vertical",   command=canvas.yview)
        hscroll = ttk.Scrollbar(container, orient="horizontal", command=canvas.xview)
        canvas.configure(yscrollcommand=vscroll.set, xscrollcommand=hscroll.set)

        hscroll.pack(side=tk.BOTTOM, fill=tk.X)
        vscroll.pack(side=tk.RIGHT,  fill=tk.Y)
        canvas.pack(side=tk.LEFT,    fill=tk.BOTH, expand=True)

        inner = tk.Frame(canvas, bg=BG_COLOR)
        canvas.create_window((0, 0), window=inner, anchor="nw")

        CELL_W = 160
        CELL_H = 60
        HDR_H  = 40
        ROW_H  = 0

        def make_cell(parent, text, bg, fg="white", bold=False, row=0, col=0,
                      width=CELL_W, height=CELL_H, tooltip_text=None):
            font = ("Segoe UI", 9, "bold") if bold else ("Segoe UI", 8)
            f = tk.Frame(parent, bg=bg, width=width, height=height,
                         highlightbackground="#333355", highlightthickness=1)
            f.pack_propagate(False)
            f.grid(row=row, column=col, padx=1, pady=1)
            lbl = tk.Label(f, text=text, bg=bg, fg=fg, font=font,
                           wraplength=width - 10, justify="center")
            lbl.pack(expand=True)
            return f

        # Header row
        make_cell(inner, "Room \\ Slot", HEADER_COLOR, "#AAAAFF", bold=True,
                  row=0, col=0, width=100, height=HDR_H)
        for ci, sid in enumerate(slot_ids):
            make_cell(inner, sid, HEADER_COLOR, ACCENT, bold=True,
                      row=0, col=ci + 1, width=CELL_W, height=HDR_H)

        # Rows
        for ri, room_id in enumerate(room_ids):
            make_cell(inner, room_id, HEADER_COLOR, FG_COLOR, bold=True,
                      row=ri + 1, col=0, width=100, height=CELL_H)
            for ci, slot_id in enumerate(slot_ids):
                var = grid.get((slot_id, room_id))
                if var:
                    c_row = courses_df[courses_df['CourseID'] == var.name]
                    instr = c_row.iloc[0]['Instructor'] if not c_row.empty else ""
                    enroll = c_row.iloc[0]['Enrollment'] if not c_row.empty else ""
                    text = f"{var.name}\n{instr.split()[-1]}\n({enroll} students)"
                    color = instr_color.get(instr, ACCENT)
                    make_cell(inner, text, color, "white",
                              row=ri + 1, col=ci + 1)
                else:
                    make_cell(inner, "─", EMPTY_COLOR, "#444444",
                              row=ri + 1, col=ci + 1)

        # Legend
        legend_frame = tk.Frame(self.grid_canvas_frame, bg=CARD_BG, pady=6)
        legend_frame.pack(fill=tk.X)
        tk.Label(legend_frame, text="Instructors: ", bg=CARD_BG, fg=FG_COLOR,
                 font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=8)
        for instr, color in instr_color.items():
            tk.Label(legend_frame, text=f"■ {instr.split()[-1]}", bg=CARD_BG,
                     fg=color, font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=4)

        inner.update_idletasks()
        canvas.configure(scrollregion=canvas.bbox("all"))

    # ------------------------------------------------------------------
    # Tab 2: Search Animation
    # ------------------------------------------------------------------

    def _build_tab_animation(self):
        ctrl = tk.Frame(self.tab_anim, bg=CARD_BG, pady=6)
        ctrl.pack(fill=tk.X)

        ttk.Button(ctrl, text="|◀ Reset",  command=self._anim_reset).pack(side=tk.LEFT, padx=6)
        ttk.Button(ctrl, text="◀ Prev",   command=self._anim_prev).pack(side=tk.LEFT, padx=4)
        ttk.Button(ctrl, text="Next ▶",   command=self._anim_next).pack(side=tk.LEFT, padx=4)
        ttk.Button(ctrl, text="▶▶ Auto",  command=self._anim_auto).pack(side=tk.LEFT, padx=4)
        self.anim_speed = tk.Scale(ctrl, from_=50, to=1000, orient=tk.HORIZONTAL,
                                   label="Speed (ms/step)", bg=CARD_BG, fg=FG_COLOR,
                                   highlightthickness=0, length=180)
        self.anim_speed.set(200)
        self.anim_speed.pack(side=tk.LEFT, padx=12)

        self.anim_info = tk.Label(ctrl, text="Step 0 / 0", bg=CARD_BG, fg=ACCENT,
                                  font=("Segoe UI", 10, "bold"))
        self.anim_info.pack(side=tk.RIGHT, padx=12)

        self.anim_text = tk.Text(self.tab_anim, bg=CARD_BG, fg=FG_COLOR,
                                 font=("Courier New", 10), height=30, state=tk.DISABLED,
                                 insertbackground=FG_COLOR)
        scrollbar = ttk.Scrollbar(self.tab_anim, command=self.anim_text.yview)
        self.anim_text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.anim_text.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        self.anim_text.tag_configure("assign",    foreground="#88FF88")
        self.anim_text.tag_configure("backtrack", foreground="#FF6666")
        self.anim_text.tag_configure("prune",     foreground="#FFAA44")
        self.anim_text.tag_configure("header",    foreground=ACCENT, font=("Courier New", 10, "bold"))

    def _anim_update(self):
        self.anim_text.configure(state=tk.NORMAL)
        self.anim_text.delete("1.0", tk.END)
        self.anim_text.insert(tk.END, "SEARCH EVENT LOG\n", "header")
        self.anim_text.insert(tk.END, "=" * 50 + "\n", "header")

        for i, (etype, vname, value) in enumerate(self.events[:self.event_idx]):
            prefix = f"Step {i+1:4d} | "
            if etype == "assign":
                line = f"{prefix}ASSIGN    {vname} = {value}\n"
                self.anim_text.insert(tk.END, line, "assign")
            elif etype == "backtrack":
                line = f"{prefix}BACKTRACK {vname}\n"
                self.anim_text.insert(tk.END, line, "backtrack")
            elif etype == "prune":
                slot, room = value if isinstance(value, tuple) else (value, "")
                line = f"{prefix}PRUNE     {vname} ← removed ({slot},{room})\n"
                self.anim_text.insert(tk.END, line, "prune")

        self.anim_text.see(tk.END)
        self.anim_text.configure(state=tk.DISABLED)
        total = len(self.events)
        self.anim_info.configure(text=f"Step {self.event_idx} / {total}")

    def _anim_reset(self):
        self.event_idx = 0
        self._anim_update()

    def _anim_next(self):
        if self.event_idx < len(self.events):
            self.event_idx += 1
            self._anim_update()

    def _anim_prev(self):
        if self.event_idx > 0:
            self.event_idx -= 1
            self._anim_update()

    def _anim_auto(self):
        if self.event_idx >= len(self.events):
            self.event_idx = 0
        self._anim_step_auto()

    def _anim_step_auto(self):
        if self.event_idx < len(self.events):
            self._anim_next()
            delay = self.anim_speed.get()
            self.root.after(delay, self._anim_step_auto)

    # ------------------------------------------------------------------
    # Tab 3: Statistics Dashboard
    # ------------------------------------------------------------------

    def _build_tab_stats(self):
        self.stats_frame = tk.Frame(self.tab_stats, bg=BG_COLOR)
        self.stats_frame.pack(fill=tk.BOTH, expand=True)
        tk.Label(self.stats_frame, text="Run 'Solve' to see statistics.",
                 bg=BG_COLOR, fg="#888888", font=("Segoe UI", 12)).pack(expand=True)

    def _draw_stats(self):
        for w in self.stats_frame.winfo_children():
            w.destroy()

        if not HAS_MATPLOTLIB:
            tk.Label(self.stats_frame,
                     text="matplotlib not installed. Run: pip install matplotlib",
                     bg=BG_COLOR, fg="#FF6666", font=("Segoe UI", 11)).pack(expand=True)
            return

        if not self.metrics:
            return

        m = self.metrics.report()
        labels  = ["Assignments", "Backtracks", "Constraint Checks"]
        values  = [m["assignments"], m["backtracks"], m["constraint_checks"]]
        colors  = [INSTRUCTOR_COLORS[0], INSTRUCTOR_COLORS[2], INSTRUCTOR_COLORS[4]]

        fig = Figure(figsize=(10, 5), facecolor=CARD_BG)
        ax  = fig.add_subplot(121, facecolor=CARD_BG)
        bars = ax.bar(labels, values, color=colors, edgecolor="#333355", linewidth=1.2)
        ax.set_title("Search Metrics", color=FG_COLOR, fontsize=12, fontweight="bold")
        ax.set_ylabel("Count", color=FG_COLOR)
        ax.tick_params(colors=FG_COLOR)
        for spine in ax.spines.values():
            spine.set_edgecolor("#444466")
        for bar, val in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                    str(int(val)), ha='center', va='bottom', color=FG_COLOR, fontsize=9)

        # Pie chart for time distribution
        ax2 = fig.add_subplot(122, facecolor=CARD_BG)
        scheduled = len(self.assignment) if self.assignment else 0
        total     = len(self.csp.variables) if self.csp else 1
        unscheduled = max(0, total - scheduled)
        pie_vals   = [scheduled, unscheduled] if unscheduled > 0 else [scheduled]
        pie_labels = ["Scheduled", "Unscheduled"] if unscheduled > 0 else ["Scheduled"]
        pie_colors = ["#59A14F", "#E15759"] if unscheduled > 0 else ["#59A14F"]
        ax2.pie(pie_vals, labels=pie_labels, colors=pie_colors, autopct='%1.0f%%',
                textprops={'color': FG_COLOR}, startangle=90)
        ax2.set_title(f"Course Coverage\n({scheduled}/{total} scheduled)",
                      color=FG_COLOR, fontsize=12, fontweight="bold")

        fig.tight_layout(pad=2.0)
        canvas = FigureCanvasTkAgg(fig, master=self.stats_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # Text metrics panel
        info_frame = tk.Frame(self.stats_frame, bg=CARD_BG, pady=8)
        info_frame.pack(fill=tk.X, padx=8)
        metrics_text = (
            f"  Execution Time  : {m['elapsed']:.4f} seconds   |   "
            f"Assignments : {m['assignments']}   |   "
            f"Backtracks : {m['backtracks']}   |   "
            f"Constraint Checks : {m['constraint_checks']}"
        )
        tk.Label(info_frame, text=metrics_text, bg=CARD_BG, fg=ACCENT,
                 font=("Segoe UI", 9)).pack()

    # ------------------------------------------------------------------
    # Tab 4: Experiments
    # ------------------------------------------------------------------

    def _build_tab_experiments(self):
        # Control panel
        ctrl = tk.Frame(self.tab_exps, bg=CARD_BG, pady=10)
        ctrl.pack(fill=tk.X)

        tk.Label(ctrl, text="Experimental Suite", bg=CARD_BG, fg=ACCENT,
                 font=("Segoe UI", 12, "bold")).pack(side=tk.LEFT, padx=15)

        self.exp_runs = tk.IntVar(value=3)
        tk.Label(ctrl, text="Runs/Instance:", bg=CARD_BG, fg=FG_COLOR).pack(side=tk.LEFT, padx=(20, 5))
        tk.Entry(ctrl, textvariable=self.exp_runs, width=4, bg=BG_COLOR, fg=FG_COLOR).pack(side=tk.LEFT)

        btn_frame = tk.Frame(self.tab_exps, bg=BG_COLOR, pady=10)
        btn_frame.pack(fill=tk.X)

        exps = [
            ("1. Algorithm Comparison", 1),
            ("2. Heuristic Impact",    2),
            ("3. Phase Transition",    3),
            ("4. Systematic vs Local", 4),
        ]

        for label, num in exps:
            btn = tk.Button(btn_frame, text=label, bg=CARD_BG, fg=FG_COLOR,
                            activebackground=ACCENT, activeforeground="white",
                            font=("Segoe UI", 9, "bold"), padx=12, pady=6,
                            command=lambda n=num: self._run_exp(n))
            btn.pack(side=tk.LEFT, padx=8)

        ttk.Button(btn_frame, text="Clear Log", command=self._exp_clear).pack(side=tk.RIGHT, padx=15)

        # Output console
        console_frame = tk.Frame(self.tab_exps, bg=BG_COLOR)
        console_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        self.exp_console = tk.Text(console_frame, bg="#0A0B10", fg="#BBBBBB",
                                   font=("Consolas", 10), padx=10, pady=10,
                                   state=tk.DISABLED, insertbackground="white")
        scrollbar = ttk.Scrollbar(console_frame, command=self.exp_console.yview)
        self.exp_console.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.exp_console.pack(fill=tk.BOTH, expand=True)

        self.exp_console.tag_configure("highlight", foreground=ACCENT, font=("Consolas", 10, "bold"))
        self.exp_console.tag_configure("success",   foreground="#88FF88")
        self.exp_console.tag_configure("error",     foreground="#FF6666")

    def _exp_log(self, text, tag=None):
        self.exp_console.configure(state=tk.NORMAL)
        self.exp_console.insert(tk.END, text, tag)
        self.exp_console.see(tk.END)
        self.exp_console.configure(state=tk.DISABLED)
        self.root.update_idletasks()

    def _exp_clear(self):
        self.exp_console.configure(state=tk.NORMAL)
        self.exp_console.delete("1.0", tk.END)
        self.exp_console.configure(state=tk.DISABLED)

    def _run_exp(self, num):
        if self.exp_thread and self.exp_thread.is_alive():
            messagebox.showwarning("Busy", "An experiment is already running.")
            return

        self._exp_clear()
        self._exp_log(f">>> STARTING EXPERIMENT {num}\n", "highlight")
        self._exp_log(f"Time: {time.strftime('%H:%M:%S')} | Runs per instance: {self.exp_runs.get()}\n\n")
        
        self.exp_thread = threading.Thread(target=self._exp_worker, args=(num,), daemon=True)
        self.exp_thread.start()

    def _exp_worker(self, num):
        from experiments import run_experiment
        import sys
        
        class RedirectStdout:
            def __init__(self, callback):
                self.callback = callback
            def write(self, s):
                self.callback(s)
            def flush(self):
                pass

        old_stdout = sys.stdout
        sys.stdout = RedirectStdout(self._exp_log)
        
        try:
            run_experiment(num, n_runs=self.exp_runs.get())
            self._exp_log("\n>>> EXPERIMENT COMPLETE.\n", "success")
        except Exception as e:
            self._exp_log(f"\nFATAL ERROR: {e}\n", "error")
        finally:
            sys.stdout = old_stdout

    # ------------------------------------------------------------------
    # Tab 5: Data Editor
    # ------------------------------------------------------------------

    def _build_tab_editor(self):
        ctrl = tk.Frame(self.tab_edit, bg=CARD_BG, pady=6)
        ctrl.pack(fill=tk.X)

        self.edit_file = tk.StringVar(value="courses.csv")
        ttk.Combobox(ctrl, textvariable=self.edit_file, width=20,
                     values=["courses.csv", "rooms.csv", "timeslots.csv",
                             "students.csv", "instructor_availability.csv"],
                     state="readonly").pack(side=tk.LEFT, padx=8)
        ttk.Button(ctrl, text="Load",  command=self._editor_load).pack(side=tk.LEFT, padx=4)
        ttk.Button(ctrl, text="Save",  command=self._editor_save).pack(side=tk.LEFT, padx=4)

        self.editor_text = tk.Text(self.tab_edit, bg=CARD_BG, fg=FG_COLOR,
                                   font=("Courier New", 10), insertbackground=FG_COLOR)
        scrollbar = ttk.Scrollbar(self.tab_edit, command=self.editor_text.yview)
        self.editor_text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.editor_text.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

    def _editor_load(self):
        path = os.path.join(self.input_dir.get(), self.edit_file.get())
        if not os.path.exists(path):
            messagebox.showerror("File Not Found", f"Cannot find: {path}")
            return
        with open(path, 'r') as f:
            content = f.read()
        self.editor_text.delete("1.0", tk.END)
        self.editor_text.insert(tk.END, content)
        self.status_text.set(f"Loaded: {path}")

    def _editor_save(self):
        path = os.path.join(self.input_dir.get(), self.edit_file.get())
        content = self.editor_text.get("1.0", tk.END)
        with open(path, 'w') as f:
            f.write(content)
        messagebox.showinfo("Saved", f"Saved to: {path}")
        self.status_text.set(f"Saved: {path}")

    # ------------------------------------------------------------------
    # Solve
    # ------------------------------------------------------------------

    def _browse_dir(self):
        d = filedialog.askdirectory(title="Select instance directory")
        if d:
            self.input_dir.set(d)

    def _run_solve(self):
        self.status_text.set("Solving… please wait.")
        self.root.update()
        t = threading.Thread(target=self._solve_thread, daemon=True)
        t.start()

    def _solve_thread(self):
        try:
            from timetable  import build_timetabling_csp
            from algorithms import get_algorithm
            from heuristics import get_var_heuristic, get_val_heuristic
            from metrics    import Metrics

            csp, meta = build_timetabling_csp(self.input_dir.get())
            algo_fn   = get_algorithm(self.algorithm.get())
            var_h_fn  = get_var_heuristic(self.var_h.get())
            val_h_fn  = get_val_heuristic(self.val_h.get())
            m = Metrics()

            if self.algorithm.get() == "min_conflicts":
                assignment, m = algo_fn(csp, max_steps=10000, metrics=m)
            else:
                assignment, m = algo_fn(csp, var_h_fn, val_h_fn, metrics=m)

            self.csp        = csp
            self.meta       = meta
            self.assignment = assignment
            self.metrics    = m
            self.events     = m.events
            self.event_idx  = 0

            scheduled = len(assignment) if assignment else 0
            total     = len(csp.variables)

            self.root.after(0, self._update_all_tabs)
            status = (f"✔ Solution found: {scheduled}/{total} courses scheduled | "
                      f"Time: {m.elapsed:.3f}s | Backtracks: {m.backtracks}")
            if not assignment:
                status = "✘ No solution found (UNSATISFIABLE)"
            self.root.after(0, lambda: self.status_text.set(status))

        except Exception as e:
            import traceback
            err = traceback.format_exc()
            self.root.after(0, lambda: self.status_text.set(f"ERROR: {e}"))
            self.root.after(0, lambda: messagebox.showerror("Error", err))

    def _update_all_tabs(self):
        self._draw_grid()
        self._anim_update()
        self._draw_stats()


# ======================================================================
# Launch
# ======================================================================

def launch():
    root = tk.Tk()
    app  = TimetableGUI(root)
    root.mainloop()


if __name__ == "__main__":
    launch()
