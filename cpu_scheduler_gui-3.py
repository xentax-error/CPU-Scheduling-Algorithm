import copy
import tkinter as tk
from tkinter import messagebox
from collections import deque
import customtkinter as ctk

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

C_SAGE_BG    = "#d6e8d6"   # soft sage green  — window background
C_MINT_PANEL = "#eaf3ea"   # light mint       — card / panel surface
C_SAGE_ROW   = "#c8ddc8"   # medium sage      — table rows / header fills
C_FOREST_BORDER = "#87ab87" # mid green        — borders and dividers
C_FOREST     = "#2d5a3d"   # dark forest green — primary accent, success labels
C_DEEP_GREEN = "#0c4532"   # deep green       — unused (kept for reference)
C_FOREST_MID = "#42654d"   # mid forest green  — averages highlight
C_RED        = "#b03020"   # deep red         — errors and preemptive warnings
C_DARK_TEXT  = "#1a2e1a"   # near-black green — main readable text
C_SAGE_DIM   = "#4a7a5a"   # muted sage       — secondary / hint text
C_IDLE       = "#a0baa0"   # dull sage        — idle Gantt blocks

# Process colors — soft pastels that complement the green UI without clashing.
# Each color is distinct enough to tell processes apart at a glance.
COLORS = ["#aec6e8","#f4b8a0","#c9b8e8","#a8d8c8","#f2b8b8",
          "#f5e0a0","#b8d8f0","#f0c8e0","#b8e8d8","#e0cbb8"]

# SECTION 1 – ALGORITHM INFO

ALGO_LIST = [
    {
        "key":           "FCFS",
        "name":          "First-Come, First-Served (FCFS)",
        "type":          "Non-Preemptive",
        "description":   "Processes are served in the order they arrive. "
                         "Once a process starts, it runs until it finishes. "
                         "Simple, but a slow process can hold up everyone behind it.",
        "show_quantum":  False,
        "show_priority": False,
        "show_preempt":  False,
    },
    {
        "key":           "SJF",
        "name":          "Shortest Job First (SJF)",
        "type":          "Non-Preemptive",
        "description":   "When the CPU is free, the process with the shortest "
                         "burst time runs next. Never interrupted once it starts. "
                         "Great average wait time, but long processes can be starved.",
        "show_quantum":  False,
        "show_priority": False,
        "show_preempt":  False,
    },
    {
        "key":           "SRT",
        "name":          "Shortest Remaining Time (SRT)",
        "type":          "Preemptive",
        "description":   "Like SJF but preemptive — at every moment the process "
                         "with the least time left runs. A new arrival with less "
                         "time can immediately take over. Best average wait time.",
        "show_quantum":  False,
        "show_priority": False,
        "show_preempt":  False,
    },
    {
        "key":           "RR",
        "name":          "Round Robin (RR)",
        "type":          "Preemptive",
        "description":   "Every process gets a fixed time slice called the quantum. "
                         "If it's not done, it goes to the back of the line. "
                         "Very fair — no process waits too long.",
        "show_quantum":  True,
        "show_priority": False,
        "show_preempt":  False,
    },
    {
        "key":           "Priority",
        "name":          "Priority Scheduling",
        "type":          "Non-Preemptive / Preemptive",
        "description":   "The highest-priority process runs next. "
                         "Non-Preemptive: the running process always finishes "
                         "before switching. Preemptive: a newly arrived "
                         "higher-priority process immediately kicks out the "
                         "current one mid-execution.",
        "show_quantum":  False,
        "show_priority": True,
        "show_preempt":  True,
    },
    {
        "key":           "Priority+RR",
        "name":          "Priority + Round Robin",
        "type":          "Non-Preemptive / Preemptive",
        "description":   "Processes are grouped by priority level. Within each "
                         "group, Round Robin is applied using the time quantum. "
                         "Non-Preemptive: current group finishes its quantum "
                         "before yielding to a higher-priority arrival. "
                         "Preemptive: a higher-priority arrival immediately "
                         "interrupts the current slice.",
        "show_quantum":  True,
        "show_priority": True,
        "show_preempt":  True,
    },
]

# SECTION 2 – PROCESS DATA

class Process:
    def __init__(self, pid, arrival, burst, priority=0):
        self.pid         = pid
        self.arrival     = arrival
        self.burst       = burst
        self.priority    = priority
        self.remaining   = burst
        self.start_time  = -1
        self.finish_time = 0
        self.waiting     = 0
        self.turnaround  = 0

    def calc_results(self):
        self.turnaround = self.finish_time - self.arrival
        self.waiting    = self.turnaround  - self.burst

# SECTION 3 – SCHEDULING ALGORITHMS

def best_first(process, mode):
    return process.priority if mode == "lower" else -process.priority


def run_fcfs(processes):
    procs    = sorted(copy.deepcopy(processes), key=lambda p: (p.arrival, p.pid))
    timeline = []
    clock    = 0
    for p in procs:
        if clock < p.arrival:
            timeline.append((clock, p.arrival, None))
            clock = p.arrival
        p.start_time  = clock
        clock        += p.burst
        p.finish_time = clock
        p.calc_results()
        timeline.append((p.start_time, p.finish_time, p.pid))
    return procs, timeline


def run_sjf(processes):
    procs    = copy.deepcopy(processes)
    todo     = list(procs)
    done     = []
    timeline = []
    clock    = 0
    while todo:
        ready = [p for p in todo if p.arrival <= clock]
        if not ready:
            nxt = min(p.arrival for p in todo)
            timeline.append((clock, nxt, None))
            clock = nxt
            continue
        chosen = min(ready, key=lambda p: (p.burst, p.arrival, p.pid))
        todo.remove(chosen)
        chosen.start_time  = clock
        clock             += chosen.burst
        chosen.finish_time = clock
        chosen.calc_results()
        timeline.append((chosen.start_time, chosen.finish_time, chosen.pid))
        done.append(chosen)
    return done, timeline


def run_srt(processes):
    procs     = copy.deepcopy(processes)
    n         = len(procs)
    finished  = 0
    timeline  = []
    clock     = 0
    current   = None
    seg_start = 0
    limit     = sum(p.burst for p in procs) + max(p.arrival for p in procs) + 1
    while finished < n and clock < limit:
        ready = [p for p in procs if p.arrival <= clock and p.remaining > 0]
        if not ready:
            if current:
                timeline.append((seg_start, clock, current))
                current = None
            nxt = min(p.arrival for p in procs if p.remaining > 0)
            timeline.append((clock, nxt, None))
            clock = nxt
            seg_start = clock
            continue
        chosen = min(ready, key=lambda p: (p.remaining, p.arrival, p.pid))
        if chosen.pid != current:
            if current:
                timeline.append((seg_start, clock, current))
            current   = chosen.pid
            seg_start = clock
            if chosen.start_time == -1:
                chosen.start_time = clock
        chosen.remaining -= 1
        clock            += 1
        if chosen.remaining == 0:
            timeline.append((seg_start, clock, chosen.pid))
            chosen.finish_time = clock
            chosen.calc_results()
            finished  += 1
            current    = None
            seg_start  = clock
    return procs, timeline


def run_rr(processes, quantum):
    procs    = copy.deepcopy(processes)
    by_arr   = sorted(procs, key=lambda p: (p.arrival, p.pid))
    queue    = deque()
    timeline = []
    clock    = 0
    idx      = 0
    n        = len(procs)
    finished = 0
    while idx < n and by_arr[idx].arrival <= clock:
        queue.append(by_arr[idx]); idx += 1
    while finished < n:
        if not queue:
            nxt = by_arr[idx].arrival
            timeline.append((clock, nxt, None))
            clock = nxt
            while idx < n and by_arr[idx].arrival <= clock:
                queue.append(by_arr[idx]); idx += 1
            continue
        p = queue.popleft()
        if p.start_time == -1:
            p.start_time = clock
        run = min(quantum, p.remaining)
        timeline.append((clock, clock + run, p.pid))
        clock       += run
        p.remaining -= run
        while idx < n and by_arr[idx].arrival <= clock:
            queue.append(by_arr[idx]); idx += 1
        if p.remaining == 0:
            p.finish_time = clock
            p.calc_results()
            finished += 1
        else:
            queue.append(p)
    return procs, timeline


def run_priority_np(processes, mode):
    # Non-Preemptive: once a process starts, it ALWAYS runs to completion.
    procs    = copy.deepcopy(processes)
    todo     = list(procs)
    done     = []
    timeline = []
    clock    = 0
    while todo:
        ready = [p for p in todo if p.arrival <= clock]
        if not ready:
            nxt = min(p.arrival for p in todo)
            timeline.append((clock, nxt, None))
            clock = nxt
            continue
        chosen = min(ready, key=lambda p: (best_first(p, mode), p.arrival, p.pid))
        todo.remove(chosen)
        chosen.start_time  = clock
        clock             += chosen.burst
        chosen.finish_time = clock
        chosen.calc_results()
        timeline.append((chosen.start_time, chosen.finish_time, chosen.pid))
        done.append(chosen)
    return done, timeline


def run_priority_p(processes, mode):
    # Preemptive: every tick we re-evaluate who should run.
    # If a higher-priority process arrives it IMMEDIATELY takes the CPU.
    procs     = copy.deepcopy(processes)
    n         = len(procs)
    finished  = 0
    timeline  = []
    clock     = 0
    current   = None
    seg_start = 0
    limit     = sum(p.burst for p in procs) + max(p.arrival for p in procs) + 1
    while finished < n and clock < limit:
        ready = [p for p in procs if p.arrival <= clock and p.remaining > 0]
        if not ready:
            if current:
                timeline.append((seg_start, clock, current))
                current = None
            nxt = min(p.arrival for p in procs if p.remaining > 0)
            timeline.append((clock, nxt, None))
            clock = nxt
            seg_start = clock
            continue
        chosen = min(ready, key=lambda p: (best_first(p, mode), p.arrival, p.pid))
        if chosen.pid != current:
            if current:
                timeline.append((seg_start, clock, current))
            current   = chosen.pid
            seg_start = clock
            if chosen.start_time == -1:
                chosen.start_time = clock
        chosen.remaining -= 1
        clock            += 1
        if chosen.remaining == 0:
            timeline.append((seg_start, clock, chosen.pid))
            chosen.finish_time = clock
            chosen.calc_results()
            finished  += 1
            current    = None
            seg_start  = clock
    return procs, timeline


def run_priority_rr_np(processes, mode, quantum):
    # Priority+RR Non-Preemptive:
    # Same as preemptive but a higher-priority arrival does NOT interrupt a
    # running quantum slice — it waits until the current slice finishes.
    procs    = copy.deepcopy(processes)
    n        = len(procs)
    by_arr   = sorted(procs, key=lambda p: (p.arrival, best_first(p, mode), p.pid))
    idx      = 0
    queues   = {}
    timeline = []
    clock    = 0
    finished = 0

    def load_arrivals(up_to):
        nonlocal idx
        while idx < n and by_arr[idx].arrival <= up_to:
            p   = by_arr[idx]
            key = best_first(p, mode)
            if key not in queues:
                queues[key] = deque()
            queues[key].append(p)
            idx += 1

    load_arrivals(clock)

    while finished < n:
        if not queues:
            nxt = by_arr[idx].arrival
            timeline.append((clock, nxt, None))
            clock = nxt
            load_arrivals(clock)
            continue

        best_key = min(queues.keys())
        q        = queues[best_key]
        if not q:
            del queues[best_key]
            continue

        p = q.popleft()
        if p.start_time == -1:
            p.start_time = clock

        # Run the full quantum (or to completion) — NO interruption check
        run   = min(quantum, p.remaining)
        end_t = clock + run
        timeline.append((clock, end_t, p.pid))
        p.remaining -= run
        clock        = end_t
        load_arrivals(clock)

        if p.remaining == 0:
            p.finish_time = clock
            p.calc_results()
            finished += 1
            if not q and best_key in queues:
                del queues[best_key]
        else:
            q.append(p)  # back of same-priority group

    return procs, timeline


def run_priority_rr(processes, mode, quantum):
    # Priority+RR Preemptive (original behaviour):
    # Priority groups + Round Robin within each group.
    # Within the same priority group, processes take equal turns (RR).
    procs    = copy.deepcopy(processes)
    n        = len(procs)
    by_arr   = sorted(procs, key=lambda p: (p.arrival, best_first(p, mode), p.pid))
    idx      = 0
    queues   = {}
    timeline = []
    clock    = 0
    finished = 0

    def load_arrivals(up_to):
        nonlocal idx
        while idx < n and by_arr[idx].arrival <= up_to:
            p   = by_arr[idx]
            key = best_first(p, mode)
            if key not in queues:
                queues[key] = deque()
            queues[key].append(p)
            idx += 1

    load_arrivals(clock)

    while finished < n:
        if not queues:
            nxt = by_arr[idx].arrival
            timeline.append((clock, nxt, None))
            clock = nxt
            load_arrivals(clock)
            continue

        best_key = min(queues.keys())
        q        = queues[best_key]
        if not q:
            del queues[best_key]
            continue

        p = q.popleft()
        if p.start_time == -1:
            p.start_time = clock

        run   = min(quantum, p.remaining)
        end_t = clock + run

        intr_at = None
        for future in by_arr[idx:]:
            if future.arrival >= end_t:
                break
            if best_first(future, mode) < best_key:
                intr_at = future.arrival
                break

        if intr_at is not None:
            actual = intr_at - clock
            if actual > 0:
                timeline.append((clock, intr_at, p.pid))
                p.remaining -= actual
                clock        = intr_at
            load_arrivals(clock)
            if p.remaining > 0:
                key = best_first(p, mode)
                if key not in queues:
                    queues[key] = deque()
                queues[key].appendleft(p)
        else:
            timeline.append((clock, end_t, p.pid))
            p.remaining -= run
            clock        = end_t
            load_arrivals(clock)
            if p.remaining == 0:
                p.finish_time = clock
                p.calc_results()
                finished += 1
                if not q and best_key in queues:
                    del queues[best_key]
            else:
                q.append(p)

    return procs, timeline


# =============================================================================
# SECTION 4 – GANTT CHART WIDGET
# =============================================================================
# Draws colored process blocks on a tk.Canvas.
# Each block is labeled with the process PID.
# Time labels appear below each block boundary on the axis.
# Idle CPU periods show as a dim "IDLE" block.

class GanttChart(ctk.CTkFrame):

    BLOCK_H = 44   # height of each process block in pixels
    PAD_X   = 16   # left/right padding inside the canvas
    PAD_TOP = 8    # space above the blocks

    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color=C_MINT_PANEL, corner_radius=10, **kwargs)
        # Plain tk.Canvas — CustomTkinter has no canvas widget
        self.canvas = tk.Canvas(self, bg=C_MINT_PANEL, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=4, pady=6)

    def draw(self, timeline, processes):
        self.canvas.delete("all")
        if not timeline or not processes:
            return

        # Assign each PID a color based on its order in the process list
        color_of = {p.pid: COLORS[i % len(COLORS)] for i, p in enumerate(processes)}
        color_of[None] = C_IDLE  # idle CPU slots use the dim idle color

        # Merge consecutive segments of the same PID into one block
        # (e.g. two adjacent P1 slots become a single wider P1 block)
        merged = []
        for start, end, pid in timeline:
            if merged and merged[-1][2] == pid:
                merged[-1] = (merged[-1][0], end, pid)  # extend previous block
            else:
                merged.append([start, end, pid])

        total_time = merged[-1][1] if merged else 1

        # Scale pixels-per-unit so the chart fits nicely regardless of length
        px = max(28, min(64, 620 // max(total_time, 1)))

        BLOCK_TOP = self.PAD_TOP
        BLOCK_BOT = BLOCK_TOP + self.BLOCK_H
        PAD_X     = self.PAD_X
        AXIS_Y    = BLOCK_BOT + 4   # y position for the time-axis number labels

        canvas_w = PAD_X * 2 + total_time * px + 10
        canvas_h = AXIS_Y + 14
        self.canvas.configure(width=canvas_w, height=canvas_h,
                              scrollregion=(0, 0, canvas_w, canvas_h))

        # --- Draw each block -------------------------------------------------
        shown_times = set()  # track which time labels we've already drawn

        for start, end, pid in merged:
            x0    = PAD_X + start * px
            x1    = PAD_X + end   * px
            color = color_of.get(pid, C_IDLE)
            label = pid if pid else "IDLE"

            # Colored filled rectangle
            self.canvas.create_rectangle(
                x0, BLOCK_TOP, x1, BLOCK_BOT,
                fill=color, outline="#111111", width=1)

            # PID label centered inside the block
            font_size = 9 if (x1 - x0) < 32 else 11
            self.canvas.create_text(
                (x0 + x1) / 2, (BLOCK_TOP + BLOCK_BOT) / 2,
                text=label,
                fill="#000000" if pid else C_SAGE_DIM,
                font=("Segoe UI", font_size, "bold"))

            # Time labels on the axis below — show start and end of each block
            for t in [start, end]:
                if t not in shown_times:
                    shown_times.add(t)
                    tx = PAD_X + t * px
                    self.canvas.create_text(
                        tx, AXIS_Y,
                        text=str(t), anchor="n",
                        fill=C_DARK_TEXT, font=("Segoe UI", 9))


# =============================================================================
# SECTION 5 – RESULTS TABLE
# =============================================================================

class ResultsTable(ctk.CTkFrame):

    # Completion Time added between Burst/Priority and Waiting Time
    COLS   = ["PID", "Arrival", "Burst", "Priority", "Completion", "Waiting Time", "Turnaround Time"]
    WIDTHS = [70,    80,        70,      80,          100,          110,            130]

    def __init__(self, parent):
        super().__init__(parent, fg_color=C_MINT_PANEL, corner_radius=10)

    def show(self, processes, show_priority):
        for w in self.winfo_children():
            w.destroy()

        header = ctk.CTkFrame(self, fg_color=C_SAGE_ROW, corner_radius=8)
        header.pack(fill="x", padx=8, pady=(8, 2))
        for name, width in zip(self.COLS, self.WIDTHS):
            if name == "Priority" and not show_priority:
                continue
            ctk.CTkLabel(header, text=name, width=width,
                         font=ctk.CTkFont(size=12, weight="bold"),
                         text_color=C_FOREST).pack(side="left", padx=4, pady=6)

        total_wt = total_tat = 0
        for i, p in enumerate(processes):
            row_color = COLORS[i % len(COLORS)]
            row = ctk.CTkFrame(self, fg_color=C_MINT_PANEL, corner_radius=6)
            row.pack(fill="x", padx=8, pady=2)
            # Completion Time = finish_time (when the process fully finished)
            values = [p.pid, p.arrival, p.burst, p.priority,
                      p.finish_time, p.waiting, p.turnaround]
            for name, val, width in zip(self.COLS, values, self.WIDTHS):
                if name == "Priority" and not show_priority:
                    continue
                color  = row_color if name == "PID" else C_DARK_TEXT
                weight = "bold"    if name == "PID" else "normal"
                ctk.CTkLabel(row, text=str(val), width=width,
                             font=ctk.CTkFont(size=13, weight=weight),
                             text_color=color).pack(side="left", padx=4, pady=5)
            total_wt  += p.waiting
            total_tat += p.turnaround

        n = len(processes)
        avg_row = ctk.CTkFrame(self, fg_color=C_SAGE_ROW, corner_radius=8)
        avg_row.pack(fill="x", padx=8, pady=(4, 8))
        # Centered average labels
        ctk.CTkLabel(avg_row,
                     text=f"Avg Waiting Time:  {total_wt / n:.2f}",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=C_FOREST,
                     anchor="center").pack(side="left", expand=True, pady=6)
        ctk.CTkLabel(avg_row,
                     text=f"Avg Turnaround Time:  {total_tat / n:.2f}",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=C_FOREST_MID,
                     anchor="center").pack(side="left", expand=True, pady=6)


# =============================================================================
# SECTION 6 – PROCESS INPUT ROW
# =============================================================================
# Each row: ● | PID | Arrival | Burst | [Priority]
#
# Arrival and Priority behave like placeholders:
#   - The field shows "0" dimmed as a hint when empty.
#   - Clicking clears it so the user can type freely.
#   - If left blank when Run is clicked, 0 is used automatically.
#   - Burst has no default and must always be filled in.

class ProcessRow(ctk.CTkFrame):

    def __init__(self, parent, number, show_priority, dot_color):
        super().__init__(parent, fg_color=C_SAGE_ROW, corner_radius=8)
        self.show_priority = show_priority

        # Colored dot
        ctk.CTkLabel(self, text="●", text_color=dot_color,
                     font=ctk.CTkFont(size=14), width=24
                     ).grid(row=0, column=0, padx=(10, 4), pady=8)

        # PID — pre-filled, starts at P0
        self.pid_box = ctk.CTkEntry(self, width=62, font=ctk.CTkFont(size=13),
                                     fg_color=C_MINT_PANEL, border_color=C_FOREST_BORDER,
                                     text_color=C_DARK_TEXT)
        self.pid_box.insert(0, f"P{number}")
        self.pid_box.grid(row=0, column=1, padx=6, pady=8)

        # Arrival — placeholder-style: shows dim "0", clears on focus
        self.arr_box = ctk.CTkEntry(self, width=72,
                                     font=ctk.CTkFont(size=13),
                                     fg_color=C_MINT_PANEL, border_color=C_FOREST_BORDER,
                                     text_color=C_SAGE_DIM,          # dim = placeholder state
                                     placeholder_text="0")
        self.arr_box.grid(row=0, column=2, padx=6, pady=8)
        self._setup_placeholder(self.arr_box, "0")

        # Burst — must be filled in; shows "e.g. 5" as true placeholder
        self.burst_box = ctk.CTkEntry(self, width=72,
                                       font=ctk.CTkFont(size=13),
                                       fg_color=C_MINT_PANEL, border_color=C_FOREST_BORDER,
                                       text_color=C_DARK_TEXT,
                                       placeholder_text="e.g. 5")
        self.burst_box.grid(row=0, column=3, padx=6, pady=8)

        # Priority — placeholder-style: shows dim "0", clears on focus
        self.pri_box = ctk.CTkEntry(self, width=72,
                                     font=ctk.CTkFont(size=13),
                                     fg_color=C_MINT_PANEL, border_color=C_FOREST_BORDER,
                                     text_color=C_SAGE_DIM,
                                     placeholder_text="0")
        if show_priority:
            self.pri_box.grid(row=0, column=4, padx=6, pady=8)
            self._setup_placeholder(self.pri_box, "0")

    def _setup_placeholder(self, entry, default_val):
        """
        Make an entry field behave like a smart placeholder:
        - Displays the default value in dim text when nothing has been typed.
        - Clears when the user clicks in (so they don't have to erase it).
        - Restores the dim default if the user leaves it empty.
        """
        # Mark this entry as being in "placeholder state"
        entry._is_placeholder = True
        entry.insert(0, default_val)

        def on_focus_in(event):
            if getattr(entry, "_is_placeholder", False):
                entry.delete(0, "end")
                entry.configure(text_color=C_DARK_TEXT)
                entry._is_placeholder = False

        def on_focus_out(event):
            if entry.get().strip() == "":
                entry.delete(0, "end")
                entry.insert(0, default_val)
                entry.configure(text_color=C_SAGE_DIM)
                entry._is_placeholder = True

        entry.bind("<FocusIn>",  on_focus_in)
        entry.bind("<FocusOut>", on_focus_out)

    def _get_value(self, entry):
        """Return the entry's real value, or '' if it's still in placeholder state."""
        if getattr(entry, "_is_placeholder", False):
            return ""
        return entry.get().strip()

    def clear_inputs(self):
        """Reset Arrival, Burst, Priority back to defaults. Keep PID."""
        # Arrival back to placeholder 0
        self.arr_box.delete(0, "end")
        self.arr_box.insert(0, "0")
        self.arr_box.configure(text_color=C_SAGE_DIM)
        self.arr_box._is_placeholder = True

        # Burst cleared completely
        self.burst_box.delete(0, "end")

        # Priority back to placeholder 0
        self.pri_box.delete(0, "end")
        self.pri_box.insert(0, "0")
        self.pri_box.configure(text_color=C_SAGE_DIM)
        self.pri_box._is_placeholder = True

    def read(self):
        """
        Read and validate all fields.
        Returns (pid, arrival, burst, priority).
        Raises ValueError with a clear message on any problem.
        Arrival and Priority default to 0 if left as placeholder.
        """
        pid = self.pid_box.get().strip()
        if not pid:
            raise ValueError(
                "One row is missing a process name (PID). "
                "Please fill in all PID fields.")

        # --- Arrival ---------------------------------------------------------
        arr_raw = self._get_value(self.arr_box)
        if arr_raw == "":
            # User left it blank → use 0
            arrival = 0
        else:
            # Validate: must be digits only (no letters, symbols, decimals)
            if not arr_raw.lstrip("-").isdigit():
                raise ValueError(
                    f"{pid} — Arrival Time: '{arr_raw}' is not valid.\n"
                    "Please enter a whole number like 0, 1, 3. "
                    "Symbols, letters, and decimals are not allowed.")
            arrival = int(arr_raw)
            if arrival < 0:
                raise ValueError(
                    f"{pid} — Arrival Time: cannot be negative. "
                    "Enter 0 or a positive whole number.")

        # --- Burst -----------------------------------------------------------
        burst_raw = self.burst_box.get().strip()
        if burst_raw == "":
            raise ValueError(
                f"{pid} — Burst Time is empty.\n"
                "Enter how many time units this process needs on the CPU (e.g. 5).")
        if not burst_raw.lstrip("-").isdigit():
            raise ValueError(
                f"{pid} — Burst Time: '{burst_raw}' is not valid.\n"
                "Please enter a positive whole number like 4 or 10. "
                "Symbols, letters, and decimals are not allowed.")
        burst = int(burst_raw)
        if burst < 1:
            raise ValueError(
                f"{pid} — Burst Time must be at least 1. "
                "A process must use at least one time unit.")

        # --- Priority --------------------------------------------------------
        priority = 0
        if self.show_priority:
            pri_raw = self._get_value(self.pri_box)
            if pri_raw == "":
                priority = 0
            else:
                if not pri_raw.lstrip("-").isdigit():
                    raise ValueError(
                        f"{pid} — Priority: '{pri_raw}' is not valid.\n"
                        "Please enter a whole number like 0, 1, 5. "
                        "Leave blank to use 0. "
                        "Symbols, letters, and decimals are not allowed.")
                priority = int(pri_raw)

        return pid, arrival, burst, priority


# =============================================================================
# SECTION 7 – MAIN WINDOW
# =============================================================================

class App(ctk.CTk):

    def __init__(self):
        super().__init__()
        self.title("CPU Scheduling Simulator")
        self.geometry("1260x900")
        self.minsize(1050, 700)
        self.configure(fg_color=C_SAGE_BG)

        self.algo_index    = 0
        self.process_rows  = []
        self.priority_mode = "lower"
        self.process_count = 3

        self.build_window()

    # =========================================================================
    # WINDOW LAYOUT
    # =========================================================================

    def build_window(self):
        bar = ctk.CTkFrame(self, fg_color=C_MINT_PANEL, height=54, corner_radius=0)
        bar.pack(fill="x")
        bar.pack_propagate(False)
        ctk.CTkLabel(bar, text=" .✦ ݁˖  CPU Scheduling Simulator",
                     font=ctk.CTkFont(size=18, weight="bold"),
                     text_color=C_FOREST).pack(side="left", padx=8)


        body = ctk.CTkFrame(self, fg_color=C_SAGE_BG)
        body.pack(fill="both", expand=True)

        left = ctk.CTkScrollableFrame(body, fg_color=C_SAGE_BG, width=455,
                                       scrollbar_button_color=C_FOREST_BORDER,
                                       scrollbar_button_hover_color=C_FOREST)
        left.pack(side="left", fill="y", padx=(10, 5), pady=10)

        right = ctk.CTkScrollableFrame(body, fg_color=C_SAGE_BG,
                                        scrollbar_button_color=C_FOREST_BORDER,
                                        scrollbar_button_hover_color=C_FOREST)
        right.pack(side="left", fill="both", expand=True, padx=(5, 10), pady=10)

        self.build_left_side(left)
        self.build_right_side(right)

    # =========================================================================
    # LEFT SIDE
    # =========================================================================

    def build_left_side(self, parent):

        # ----- Algorithm selector --------------------------------------------
        algo_panel = self.make_panel(parent, "Algorithm")
        algo_names = [f"  {a['name']}" for a in ALGO_LIST]
        self.algo_var = tk.StringVar(value=algo_names[0])
        ctk.CTkOptionMenu(
            algo_panel, values=algo_names, variable=self.algo_var,
            command=self.on_algo_changed,
            fg_color=C_FOREST, button_color=C_FOREST, button_hover_color="#4a8a62",
            text_color="#ffffff", font=ctk.CTkFont(size=13),
            dropdown_fg_color=C_MINT_PANEL, dropdown_text_color=C_DARK_TEXT,
            dropdown_hover_color=C_SAGE_ROW, corner_radius=8, width=420,
        ).pack(padx=12, pady=(0, 6))

        self.type_label = ctk.CTkLabel(algo_panel, text="",
                                        font=ctk.CTkFont(size=11, weight="bold"),
                                        text_color=C_FOREST, anchor="center")
        self.type_label.pack(fill="x", padx=12, pady=(0, 2))

        self.desc_label = ctk.CTkLabel(algo_panel, text="",
                                        font=ctk.CTkFont(size=11),
                                        text_color=C_SAGE_DIM,
                                        wraplength=405, justify="left")
        self.desc_label.pack(anchor="w", padx=12, pady=(0, 10))

        # ----- Process count: [ − ] [ typeable box ] [ + ] ------------------
        count_panel = self.make_panel(parent, "Number of Processes  (minimum 3)")
        count_row   = ctk.CTkFrame(count_panel, fg_color="transparent")
        count_row.pack(pady=(0, 10), anchor="center")

        ctk.CTkButton(count_row, text="−", width=34, height=34,
                      font=ctk.CTkFont(size=18, weight="bold"),
                      fg_color=C_SAGE_ROW, hover_color=C_FOREST_BORDER,
                      text_color=C_DARK_TEXT, corner_radius=8,
                      command=self.decrease_count).pack(side="left")

        # Single editable box — shows and lets you edit the current count
        # Pressing Enter or clicking away applies the typed number
        self.count_box = ctk.CTkEntry(count_row, width=54, height=34,
                                       font=ctk.CTkFont(size=15, weight="bold"),
                                       fg_color=C_MINT_PANEL, border_color=C_FOREST,
                                       text_color=C_FOREST,
                                       justify="center")
        self.count_box.insert(0, "3")
        self.count_box.pack(side="left", padx=6)
        self.count_box.bind("<Return>",   lambda e: self.apply_count_box())
        self.count_box.bind("<FocusOut>", lambda e: self.apply_count_box())

        ctk.CTkButton(count_row, text="+", width=34, height=34,
                      font=ctk.CTkFont(size=18, weight="bold"),
                      fg_color=C_SAGE_ROW, hover_color=C_FOREST_BORDER,
                      text_color=C_DARK_TEXT, corner_radius=8,
                      command=self.increase_count).pack(side="left")

        ctk.CTkLabel(count_row, text="  processes",
                     font=ctk.CTkFont(size=11), text_color=C_SAGE_DIM
                     ).pack(side="left")

        # ----- Process input table -------------------------------------------
        self.proc_panel = self.make_panel(parent, "Process Details")
        self.col_header = ctk.CTkFrame(self.proc_panel, fg_color=C_SAGE_ROW,
                                        corner_radius=6)
        self.col_header.pack(fill="x", padx=8, pady=(0, 4))
        self.rows_frame = ctk.CTkFrame(self.proc_panel, fg_color="transparent")
        self.rows_frame.pack(fill="x", padx=8, pady=(0, 8))

        # ----- Optional panels (packed BEFORE run button via show_hide) ------

        # Time Quantum
        self.quantum_panel = self.make_panel(parent, "Time Quantum")
        ctk.CTkLabel(self.quantum_panel,
                     text="How many time units each process gets per turn.\n"
                          "Used by Round Robin and Priority + Round Robin.",
                     font=ctk.CTkFont(size=11), text_color=C_SAGE_DIM,
                     wraplength=405, justify="center", anchor="center"
                     ).pack(fill="x", padx=12, pady=(0, 4))
        self.quantum_box = ctk.CTkEntry(self.quantum_panel, width=80,
                                         font=ctk.CTkFont(size=13),
                                         fg_color=C_SAGE_ROW, border_color=C_FOREST_BORDER,
                                         text_color=C_DARK_TEXT)
        self.quantum_box.insert(0, "2")
        self.quantum_box.pack(anchor="center", padx=12, pady=(0, 10))

        # Priority Mode
        self.primode_panel = self.make_panel(parent, "Priority Mode")
        ctk.CTkLabel(self.primode_panel,
                     text="Which number means HIGHER priority?",
                     font=ctk.CTkFont(size=12), text_color=C_DARK_TEXT,
                     anchor="center"
                     ).pack(fill="x", padx=12, pady=(0, 6))
        self.primode_menu = ctk.CTkOptionMenu(
            self.primode_panel,
            values=["Lower number  (e.g. 0 = most urgent)",
                    "Higher number  (e.g. 10 = most urgent)"],
            command=self.on_primode_changed,
            fg_color=C_FOREST, button_color=C_FOREST, button_hover_color="#4a8a62",
            text_color="#ffffff", font=ctk.CTkFont(size=12),
            dropdown_fg_color=C_MINT_PANEL, dropdown_text_color=C_DARK_TEXT,
            dropdown_hover_color=C_SAGE_ROW, corner_radius=6, width=420,
        )
        self.primode_menu.pack(anchor="w", padx=12, pady=(0, 10))

        # Preemption Mode
        self.preempt_panel = self.make_panel(parent, "Preemption Mode")

        # Two clearly separated explanation rows
        off_frame = ctk.CTkFrame(self.preempt_panel, fg_color=C_SAGE_ROW, corner_radius=8)
        off_frame.pack(fill="x", padx=12, pady=(0, 4))
        ctk.CTkLabel(off_frame, text="OFF",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=C_FOREST, width=36, anchor="center"
                     ).pack(side="left", padx=(10, 6), pady=8)
        ctk.CTkLabel(off_frame,
                     text="Non-Preemptive — the running process\n"
                          "always finishes before another one starts.",
                     font=ctk.CTkFont(size=11), text_color=C_SAGE_DIM,
                     justify="left"
                     ).pack(side="left", pady=8)

        on_frame = ctk.CTkFrame(self.preempt_panel, fg_color=C_SAGE_ROW, corner_radius=8)
        on_frame.pack(fill="x", padx=12, pady=(0, 10))
        ctk.CTkLabel(on_frame, text="ON",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=C_RED, width=36, anchor="center"
                     ).pack(side="left", padx=(10, 6), pady=8)
        ctk.CTkLabel(on_frame,
                     text="Preemptive — a higher-priority arrival\n"
                          "immediately interrupts the current process.",
                     font=ctk.CTkFont(size=11), text_color=C_SAGE_DIM,
                     justify="left"
                     ).pack(side="left", pady=8)

        self.preempt_var = tk.BooleanVar(value=False)
        switch_row = ctk.CTkFrame(self.preempt_panel, fg_color="transparent")
        switch_row.pack(anchor="w", padx=12, pady=(0, 10))

        ctk.CTkSwitch(switch_row, text="",
                      variable=self.preempt_var, onvalue=True, offvalue=False,
                      button_color=C_FOREST, progress_color=C_DEEP_GREEN,
                      fg_color=C_FOREST_BORDER).pack(side="left")

        # This label sits right next to the switch and is always fully visible
        self.preempt_status = ctk.CTkLabel(switch_row,
                                            text="OFF  (Non-Preemptive)",
                                            font=ctk.CTkFont(size=12, weight="bold"),
                                            text_color=C_FOREST)
        self.preempt_status.pack(side="left", padx=10)
        self.preempt_var.trace_add("write", self.on_preempt_toggled)

        # ----- Run button ----------------------------------------------------
        self.run_btn = ctk.CTkButton(parent, text="▶  Run Simulation",
                                      command=self.run_simulation,
                                      height=44,
                                      font=ctk.CTkFont(size=15, weight="bold"),
                                      fg_color=C_FOREST, hover_color="#4a8a62",
                                      text_color="#ffffff",
                                      corner_radius=10)
        self.run_btn.pack(fill="x", pady=(0, 6))

        # ----- Clear buttons -------------------------------------------------
        clear_row = ctk.CTkFrame(parent, fg_color="transparent")
        clear_row.pack(fill="x")

        ctk.CTkButton(clear_row, text="Clear Results",
                      command=self.clear_results,
                      height=34, font=ctk.CTkFont(size=12),
                      fg_color=C_SAGE_ROW, hover_color="#d6e8d6",
                      border_color=C_FOREST_BORDER, border_width=1,
                      text_color=C_DARK_TEXT, corner_radius=8
                      ).pack(side="left", fill="x", expand=True, padx=(0, 4))

        self._clear_all_btn = ctk.CTkButton(clear_row, text="Clear All",
                      command=self.clear_all,
                      height=34, font=ctk.CTkFont(size=12),
                      fg_color=C_SAGE_ROW, hover_color=C_RED,
                      border_color=C_RED, border_width=1,
                      text_color=C_RED, corner_radius=8)
        self._clear_all_btn.pack(side="left", fill="x", expand=True, padx=(4, 0))
        # On hover: red background (handled by CTk hover_color) + white text.
        # We bind to the inner CTkButton widget so our bind fires after CTk's.
        # Setting both fg_color and text_color on enter ensures the red bg
        # stays and the text is visible. On leave we restore the original look.
        def _btn_enter(e):
            self._clear_all_btn.configure(fg_color=C_RED, text_color="#ffffff")
        def _btn_leave(e):
            self._clear_all_btn.configure(fg_color=C_SAGE_ROW, text_color=C_RED)
        self._clear_all_btn.bind("<Enter>", _btn_enter)
        self._clear_all_btn.bind("<Leave>",  _btn_leave)

        # Initial layout
        self.on_algo_changed(self.algo_var.get())

    # =========================================================================
    # RIGHT SIDE
    # =========================================================================

    def build_right_side(self, parent):
        self.placeholder = ctk.CTkFrame(parent, fg_color=C_MINT_PANEL, corner_radius=14)
        self.placeholder.pack(fill="both", expand=True)
        ctk.CTkLabel(self.placeholder, text="✦",
                     font=ctk.CTkFont(size=52), text_color=C_FOREST_BORDER
                     ).pack(pady=(90, 8))
        ctk.CTkLabel(self.placeholder,
                     text="Configure and run a simulation",
                     font=ctk.CTkFont(size=17, weight="bold"),
                     text_color=C_SAGE_DIM).pack()
        ctk.CTkLabel(self.placeholder,
                     text="Pick an algorithm, fill in your processes, then click  ▶ Run",
                     font=ctk.CTkFont(size=12), text_color=C_FOREST_BORDER).pack(pady=4)

        self.results_frame = ctk.CTkFrame(parent, fg_color="transparent")

        ctk.CTkLabel(self.results_frame, text="Gantt Chart",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=C_DARK_TEXT, anchor="center"
                     ).pack(fill="x", pady=(0, 4))

        gantt_scroll = ctk.CTkScrollableFrame(
            self.results_frame, fg_color=C_MINT_PANEL,
            orientation="horizontal", height=96, corner_radius=10,
            scrollbar_button_color=C_FOREST_BORDER,
            scrollbar_button_hover_color=C_FOREST)
        gantt_scroll.pack(fill="x", pady=(0, 12))

        self.gantt = GanttChart(gantt_scroll, height=82)
        self.gantt.pack(fill="both", expand=True)

        ctk.CTkLabel(self.results_frame, text="Results Table",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=C_DARK_TEXT, anchor="center"
                     ).pack(fill="x", pady=(0, 4))

        self.table = ResultsTable(self.results_frame)
        self.table.pack(fill="x", pady=(0, 12))



    # =========================================================================
    # HELPER — titled panel card
    # =========================================================================

    def make_panel(self, parent, title):
        panel = ctk.CTkFrame(parent, fg_color=C_MINT_PANEL, corner_radius=12)
        panel.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(panel, text=title,
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=C_SAGE_DIM, anchor="center"
                     ).pack(fill="x", padx=12, pady=(10, 4))
        return panel

    # =========================================================================
    # CALLBACKS
    # =========================================================================

    def on_algo_changed(self, _value):
        label = self.algo_var.get().strip()
        new_index = next(
            (i for i, a in enumerate(ALGO_LIST) if a["name"] == label), 0)

        # On actual algorithm change (skip on first-time setup)
        if self.process_rows and new_index != self.algo_index:
            answer = messagebox.askyesnocancel(
                "Switch Algorithm",
                "You are switching to a different algorithm.\n\n"
                "Yes    → Reset process inputs and clear results\n"
                "No     → Keep current inputs and results as-is\n"
                "Cancel → Stay on the current algorithm"
            )
            if answer is None:
                # Cancel — revert the dropdown back to the previous algorithm
                self.algo_var.set(f"  {ALGO_LIST[self.algo_index]['name']}")
                return
            if answer:
                # Yes — mark that we want a full reset after rebuilding
                do_full_reset = True
            else:
                # No — keep existing inputs, only rebuild layout for new algo
                do_full_reset = False
        else:
            do_full_reset = False

        self.algo_index = new_index
        algo = ALGO_LIST[self.algo_index]

        self.desc_label.configure(text=algo["description"])
        is_pre = "Preemptive" in algo["type"] and "Non" not in algo["type"]
        self.type_label.configure(
            text=f"✦  {algo['type']}",
            text_color=C_RED if is_pre else C_FOREST)

        self.show_hide(self.quantum_panel,  algo["show_quantum"])
        self.show_hide(self.primode_panel,  algo["show_priority"])
        self.show_hide(self.preempt_panel,  algo["show_preempt"])

        self.preempt_var.set(False)
        self.on_preempt_toggled()

        if do_full_reset:
            # Reset count to 3, wipe all process inputs, reset quantum, clear results
            self.process_count = 3
            self._sync_count_box()
            self.rebuild_process_rows(algo["show_priority"])
            # Wipe every row's inputs (PID stays, rest cleared)
            for row in self.process_rows:
                row.clear_inputs()
            # Reset Time Quantum back to default
            self.quantum_box.delete(0, "end")
            self.quantum_box.insert(0, "2")
            self.clear_results()
        else:
            # Keep inputs but rebuild the layout (show/hide Priority column etc.)
            self.rebuild_process_rows(algo["show_priority"])
            self.clear_results()

    def show_hide(self, panel, should_show):
        if should_show:
            panel.pack(fill="x", pady=(0, 8), before=self.run_btn)
        else:
            panel.pack_forget()

    def on_primode_changed(self, value):
        self.priority_mode = "lower" if value.startswith("Lower") else "higher"

    def on_preempt_toggled(self, *_):
        if self.preempt_var.get():
            self.preempt_status.configure(
                text="ON  (Preemptive)", text_color=C_RED)
        else:
            self.preempt_status.configure(
                text="OFF  (Non-Preemptive)", text_color=C_FOREST)

    def decrease_count(self):
        if self.process_count > 3:
            self.process_count -= 1
            self._sync_count_box()
            self.rebuild_process_rows(ALGO_LIST[self.algo_index]["show_priority"])
            self.clear_results()   # reset results when count changes

    def increase_count(self):
        self.process_count += 1
        self._sync_count_box()
        self.rebuild_process_rows(ALGO_LIST[self.algo_index]["show_priority"])
        self.clear_results()   # reset results when count changes

    def _sync_count_box(self):
        """Update the count box to match self.process_count."""
        self.count_box.delete(0, "end")
        self.count_box.insert(0, str(self.process_count))

    def apply_count_box(self):
        """Read whatever is typed in the count box and apply it."""
        text = self.count_box.get().strip()
        if not text:
            self._sync_count_box()
            return
        if not text.isdigit():
            messagebox.showerror("Invalid Count",
                                 "Number of processes must be a whole number "
                                 "(e.g. 3, 5, 10). Letters and symbols are not allowed.")
            self._sync_count_box()
            return
        n = int(text)
        if n < 3:
            messagebox.showerror("Too Few",
                                 "You need at least 3 processes to run a simulation.")
            self._sync_count_box()
            return
        self.process_count = n
        self._sync_count_box()
        self.rebuild_process_rows(ALGO_LIST[self.algo_index]["show_priority"])
        self.clear_results()   # reset results when count changes

    def rebuild_process_rows(self, show_priority):
        # Save current input values before destroying rows so they can be
        # restored after rebuild (e.g. when the user adds/removes a process).
        saved = []
        for row in self.process_rows:
            saved.append({
                "pid":   row.pid_box.get().strip(),
                "arr":   row.arr_box.get().strip()   if not getattr(row.arr_box,   "_is_placeholder", False) else "",
                "burst": row.burst_box.get().strip(),
                "pri":   row.pri_box.get().strip()   if not getattr(row.pri_box,   "_is_placeholder", False) else "",
            })

        # Rebuild column headers
        for w in self.col_header.winfo_children():
            w.destroy()
        cols = [("", 28), ("PID", 62), ("Arrival", 72), ("Burst", 72)]
        if show_priority:
            cols.append(("Priority", 72))
        for text, width in cols:
            ctk.CTkLabel(self.col_header, text=text, width=width,
                         font=ctk.CTkFont(size=11, weight="bold"),
                         text_color=C_FOREST, anchor="center"
                         ).pack(side="left", padx=4, pady=4)

        # Rebuild rows (P0, P1, P2, ...)
        for w in self.rows_frame.winfo_children():
            w.destroy()
        self.process_rows.clear()

        for i in range(self.process_count):
            color = COLORS[i % len(COLORS)]
            row   = ProcessRow(self.rows_frame, i, show_priority, color)
            row.pack(fill="x", pady=3)
            self.process_rows.append(row)

            # Restore saved values if this row existed before the rebuild
            if i < len(saved):
                s = saved[i]

                # PID — restore if not empty
                if s["pid"]:
                    row.pid_box.delete(0, "end")
                    row.pid_box.insert(0, s["pid"])

                # Arrival — restore real value if user had typed one
                if s["arr"]:
                    row.arr_box.delete(0, "end")
                    row.arr_box.insert(0, s["arr"])
                    row.arr_box.configure(text_color=C_DARK_TEXT)
                    row.arr_box._is_placeholder = False

                # Burst — restore if user had typed one
                if s["burst"]:
                    row.burst_box.delete(0, "end")
                    row.burst_box.insert(0, s["burst"])

                # Priority — restore real value if user had typed one
                if s["pri"] and show_priority:
                    row.pri_box.delete(0, "end")
                    row.pri_box.insert(0, s["pri"])
                    row.pri_box.configure(text_color=C_DARK_TEXT)
                    row.pri_box._is_placeholder = False

    # =========================================================================
    # CLEAR ACTIONS
    # =========================================================================

    def clear_results(self):
        # Guard: results_frame may not exist yet on first startup
        # (build_left_side runs before build_right_side, and on_algo_changed
        #  is called at the end of build_left_side to set the initial state)
        if not hasattr(self, "results_frame"):
            return
        self.results_frame.pack_forget()
        self.placeholder.pack(fill="both", expand=True)

    def clear_all(self):
        for row in self.process_rows:
            row.clear_inputs()
        self.clear_results()

    # =========================================================================
    # RUN SIMULATION
    # =========================================================================

    def run_simulation(self):
        algo = ALGO_LIST[self.algo_index]

        # Validate Time Quantum
        quantum = 2
        if algo["show_quantum"]:
            q = self.quantum_box.get().strip()
            if not q.isdigit() or int(q) < 1:
                messagebox.showerror("Invalid Time Quantum",
                    "Time Quantum must be a positive whole number (e.g. 2, 3).\n"
                    "Letters, symbols, and zero are not allowed.")
                return
            quantum = int(q)

        # Collect and validate process rows
        processes = []
        used_pids = set()
        try:
            for row in self.process_rows:
                pid, arrival, burst, priority = row.read()
                if pid in used_pids:
                    raise ValueError(
                        f"Process name '{pid}' is used more than once.\n"
                        "Every process must have a unique name.")
                used_pids.add(pid)
                processes.append(Process(pid, arrival, burst, priority))
        except ValueError as err:
            messagebox.showerror("Input Error", str(err))
            return

        mode       = self.priority_mode
        preemptive = self.preempt_var.get()

        try:
            key = algo["key"]
            if   key == "FCFS":        result, tl = run_fcfs(processes)
            elif key == "SJF":         result, tl = run_sjf(processes)
            elif key == "SRT":         result, tl = run_srt(processes)
            elif key == "RR":          result, tl = run_rr(processes, quantum)
            elif key == "Priority":
                if preemptive:         result, tl = run_priority_p(processes, mode)
                else:                  result, tl = run_priority_np(processes, mode)
            elif key == "Priority+RR":
                if preemptive:         result, tl = run_priority_rr(processes, mode, quantum)
                else:                  result, tl = run_priority_rr_np(processes, mode, quantum)
            else: raise RuntimeError(f"Unknown algorithm: {key}")
        except Exception as err:
            messagebox.showerror("Simulation Error", str(err))
            return

        self.show_results(result, tl, algo)

    def show_results(self, processes, timeline, algo):
        self.placeholder.pack_forget()
        self.results_frame.pack(fill="both", expand=True)
        self.gantt.draw(timeline, processes)
        self.table.show(processes, algo["show_priority"])


# =============================================================================
# START THE APP
# =============================================================================

if __name__ == "__main__":
    app = App()
    app.mainloop()