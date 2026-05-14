# =============================================================================
# CPU SCHEDULING SIMULATOR
# =============================================================================
# Simulates 6 CPU scheduling algorithms:
#   1. FCFS          – First-Come, First-Served
#   2. SJF           – Shortest Job First (Non-Preemptive)
#   3. SRT           – Shortest Remaining Time (Preemptive)
#   4. Round Robin   – Equal time slices for every process
#   5. Priority      – Higher-priority process runs first
#   6. Priority + RR – Priority groups with Round Robin inside each group
#
# Requirements:  pip install customtkinter
# Run:           python cpu_scheduler_gui.py
# =============================================================================

import copy
import tkinter as tk
from tkinter import messagebox
from collections import deque
import customtkinter as ctk

# --- App appearance -----------------------------------------------------------
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# --- Colors (change these if you want a different look) ----------------------
C_BG     = "#0f1117"   # window background
C_PANEL  = "#1a1d27"   # panel / card background
C_PANEL2 = "#20243a"   # table row / header background
C_BORDER = "#2a2f45"   # borders
C_BLUE   = "#4f8ef7"   # accent blue
C_PURPLE = "#7c5ef5"   # accent purple (hover)
C_GREEN  = "#3ddc84"   # success / non-preemptive label
C_YELLOW = "#f5c842"   # averages
C_RED    = "#f55e5e"   # preemptive label
C_TEXT   = "#e8eaf6"   # main text
C_DIM    = "#7b82a0"   # secondary / hint text
C_IDLE   = "#3a3f55"   # Gantt idle block

# Colors assigned to processes in order (cycles back if > 10 processes)
COLORS = ["#4f8ef7","#3ddc84","#f5c842","#f55e5e","#c084fc",
          "#38bdf8","#fb923c","#f472b6","#a3e635","#34d399"]


# =============================================================================
# SECTION 1 – ALGORITHM INFO
# =============================================================================
# This list describes every algorithm.
# The "show_*" keys tell the UI which input fields to show or hide.

ALGO_LIST = [
    {
        "key":          "FCFS",
        "name":         "First-Come, First-Served (FCFS)",
        "type":         "Non-Preemptive",
        "description":  "Processes are served in the order they arrive. "
                        "Once a process starts, it runs until it finishes. "
                        "Simple, but a slow process can hold up everyone behind it.",
        "show_quantum":   False,  # no Time Quantum field needed
        "show_priority":  False,  # no Priority field needed
        "show_preempt":   False,  # no Preemptive switch needed
    },
    {
        "key":          "SJF",
        "name":         "Shortest Job First (SJF)",
        "type":         "Non-Preemptive",
        "description":  "When the CPU is free, the process with the shortest "
                        "burst time runs next. Never interrupted once it starts. "
                        "Great average wait time, but long processes can be starved.",
        "show_quantum":   False,
        "show_priority":  False,
        "show_preempt":   False,
    },
    {
        "key":          "SRT",
        "name":         "Shortest Remaining Time (SRT)",
        "type":         "Preemptive",
        "description":  "Like SJF but preemptive — at every moment the process "
                        "with the least time left runs. A new arrival with less "
                        "time can immediately take over. Best average wait time.",
        "show_quantum":   False,
        "show_priority":  False,
        "show_preempt":   False,
    },
    {
        "key":          "RR",
        "name":         "Round Robin (RR)",
        "type":         "Preemptive",
        "description":  "Every process gets a fixed time slice called the quantum. "
                        "If it's not done, it goes to the back of the line. "
                        "Very fair — no process waits too long.",
        "show_quantum":   True,   # needs Time Quantum
        "show_priority":  False,
        "show_preempt":   False,
    },
    {
        "key":          "Priority",
        "name":         "Priority Scheduling",
        "type":         "Non-Preemptive / Preemptive",
        "description":  "The highest-priority process runs next. You choose "
                        "whether a new high-priority arrival can interrupt "
                        "the running process (Preemptive) or not.",
        "show_quantum":   False,
        "show_priority":  True,   # needs Priority column + mode selector
        "show_preempt":   True,   # needs Preemptive switch
    },
    {
        "key":          "Priority+RR",
        "name":         "Priority + Round Robin",
        "type":         "Preemptive",
        "description":  "Processes are grouped by priority. Inside each group "
                        "Round Robin is used. Higher-priority groups always "
                        "run before lower ones.",
        "show_quantum":   True,
        "show_priority":  True,
        "show_preempt":   False,
    },
]


# =============================================================================
# SECTION 2 – PROCESS DATA
# =============================================================================
# A simple class to hold one process and its results after scheduling.

class Process:
    def __init__(self, pid, arrival, burst, priority=0):
        # --- What the user enters ---
        self.pid      = pid       # e.g. "P1"
        self.arrival  = arrival   # time the process becomes available
        self.burst    = burst     # total CPU time it needs
        self.priority = priority  # lower or higher = better, depends on user setting

        # --- Filled in during simulation ---
        self.remaining   = burst  # how much time is still left to run
        self.start_time  = -1     # first moment this process used the CPU
        self.finish_time = 0      # moment it completely finished
        self.waiting     = 0      # result: how long it waited
        self.turnaround  = 0      # result: finish_time - arrival

    def calc_results(self):
        # Turnaround = total time from arrival to finish
        # Waiting    = turnaround minus the actual time it ran
        self.turnaround = self.finish_time - self.arrival
        self.waiting    = self.turnaround  - self.burst


# =============================================================================
# SECTION 3 – SCHEDULING ALGORITHMS
# =============================================================================
# Every function takes a list of Process objects and returns:
#   (processes_with_results, timeline)
#
# timeline is a list of (start_time, end_time, pid)
#   pid = None means the CPU was idle during that period


# --- Helper used by priority algorithms -------------------------------------
def best_first(process, mode):
    # Returns a sort key so the "best" priority always comes out smallest.
    # mode "lower"  → small number = high priority → use number as-is
    # mode "higher" → large number = high priority → negate it so it sorts first
    if mode == "lower":
        return process.priority
    else:
        return -process.priority


# --- 1. FCFS -----------------------------------------------------------------
def run_fcfs(processes):
    # Sort by arrival time so earliest-arriving process goes first.
    procs    = sorted(copy.deepcopy(processes), key=lambda p: (p.arrival, p.pid))
    timeline = []
    clock    = 0  # current time

    for p in procs:
        # If the CPU finished early and this process hasn't arrived yet,
        # the CPU sits idle until the process arrives.
        if clock < p.arrival:
            timeline.append((clock, p.arrival, None))  # idle slot
            clock = p.arrival

        # Run this process from start to finish without interruption.
        p.start_time  = clock
        clock        += p.burst
        p.finish_time = clock
        p.calc_results()
        timeline.append((p.start_time, p.finish_time, p.pid))

    return procs, timeline


# --- 2. SJF ------------------------------------------------------------------
def run_sjf(processes):
    procs    = copy.deepcopy(processes)
    todo     = list(procs)   # all processes still waiting to run
    done     = []
    timeline = []
    clock    = 0

    while todo:
        # Find all processes that have already arrived
        ready = [p for p in todo if p.arrival <= clock]

        if not ready:
            # Nothing is ready yet — jump the clock to the next arrival
            next_arrival = min(p.arrival for p in todo)
            timeline.append((clock, next_arrival, None))  # idle
            clock = next_arrival
            continue

        # Pick the one that takes the least time (ties: earlier arrival wins)
        chosen = min(ready, key=lambda p: (p.burst, p.arrival, p.pid))
        todo.remove(chosen)

        # Run chosen to completion
        chosen.start_time  = clock
        clock             += chosen.burst
        chosen.finish_time = clock
        chosen.calc_results()
        timeline.append((chosen.start_time, chosen.finish_time, chosen.pid))
        done.append(chosen)

    return done, timeline


# --- 3. SRT ------------------------------------------------------------------
def run_srt(processes):
    procs    = copy.deepcopy(processes)
    n        = len(procs)
    finished = 0
    timeline = []
    clock    = 0

    # We track which process is currently running so we can
    # group consecutive clock ticks into a single timeline block.
    current     = None   # PID of the process running right now
    seg_start   = 0      # when the current run segment started

    # Worst-case end time to avoid infinite loop
    limit = sum(p.burst for p in procs) + max(p.arrival for p in procs) + 1

    while finished < n and clock < limit:
        # All processes that have arrived and still have work left
        ready = [p for p in procs if p.arrival <= clock and p.remaining > 0]

        if not ready:
            # CPU is idle
            if current is not None:
                timeline.append((seg_start, clock, current))
                current = None
            next_t = min(p.arrival for p in procs if p.remaining > 0)
            timeline.append((clock, next_t, None))  # idle
            clock     = next_t
            seg_start = clock
            continue

        # Pick the process with least time remaining
        chosen = min(ready, key=lambda p: (p.remaining, p.arrival, p.pid))

        # If a different process takes over, save the old segment first
        if chosen.pid != current:
            if current is not None:
                timeline.append((seg_start, clock, current))
            current   = chosen.pid
            seg_start = clock
            if chosen.start_time == -1:
                chosen.start_time = clock

        # Run for exactly one time unit, then re-check
        chosen.remaining -= 1
        clock            += 1

        # Check if this process just finished
        if chosen.remaining == 0:
            timeline.append((seg_start, clock, chosen.pid))
            chosen.finish_time = clock
            chosen.calc_results()
            finished += 1
            current   = None
            seg_start = clock

    return procs, timeline


# --- 4. Round Robin ----------------------------------------------------------
def run_rr(processes, quantum):
    procs      = copy.deepcopy(processes)
    by_arrival = sorted(procs, key=lambda p: (p.arrival, p.pid))
    queue      = deque()   # ready queue
    timeline   = []
    clock      = 0
    idx        = 0         # index into by_arrival for new arrivals
    n          = len(procs)
    finished   = 0

    # Add any processes already available at time 0
    while idx < n and by_arrival[idx].arrival <= clock:
        queue.append(by_arrival[idx])
        idx += 1

    while finished < n:
        if not queue:
            # No one ready — idle until next arrival
            next_arrival = by_arrival[idx].arrival
            timeline.append((clock, next_arrival, None))  # idle
            clock = next_arrival
            while idx < n and by_arrival[idx].arrival <= clock:
                queue.append(by_arrival[idx])
                idx += 1
            continue

        p = queue.popleft()

        if p.start_time == -1:
            p.start_time = clock

        # Run for at most `quantum` units (less if it finishes sooner)
        run_time = min(quantum, p.remaining)
        timeline.append((clock, clock + run_time, p.pid))
        clock       += run_time
        p.remaining -= run_time

        # Enqueue any new arrivals that showed up during this slice
        while idx < n and by_arrival[idx].arrival <= clock:
            queue.append(by_arrival[idx])
            idx += 1

        if p.remaining == 0:
            # Done!
            p.finish_time = clock
            p.calc_results()
            finished += 1
        else:
            # Not done — goes to the back of the queue
            queue.append(p)

    return procs, timeline


# --- 5a. Priority (Non-Preemptive) ------------------------------------------
def run_priority_np(processes, mode):
    procs    = copy.deepcopy(processes)
    todo     = list(procs)
    done     = []
    timeline = []
    clock    = 0

    while todo:
        ready = [p for p in todo if p.arrival <= clock]

        if not ready:
            next_arrival = min(p.arrival for p in todo)
            timeline.append((clock, next_arrival, None))  # idle
            clock = next_arrival
            continue

        # Pick highest priority (ties: earlier arrival, then PID)
        chosen = min(ready, key=lambda p: (best_first(p, mode), p.arrival, p.pid))
        todo.remove(chosen)

        # Run to completion — no interruptions
        chosen.start_time  = clock
        clock             += chosen.burst
        chosen.finish_time = clock
        chosen.calc_results()
        timeline.append((chosen.start_time, chosen.finish_time, chosen.pid))
        done.append(chosen)

    return done, timeline


# --- 5b. Priority (Preemptive) -----------------------------------------------
def run_priority_p(processes, mode):
    procs    = copy.deepcopy(processes)
    n        = len(procs)
    finished = 0
    timeline = []
    clock    = 0
    current  = None   # PID currently running
    seg_start= 0

    limit = sum(p.burst for p in procs) + max(p.arrival for p in procs) + 1

    while finished < n and clock < limit:
        ready = [p for p in procs if p.arrival <= clock and p.remaining > 0]

        if not ready:
            if current is not None:
                timeline.append((seg_start, clock, current))
                current = None
            next_t = min(p.arrival for p in procs if p.remaining > 0)
            timeline.append((clock, next_t, None))  # idle
            clock     = next_t
            seg_start = clock
            continue

        chosen = min(ready, key=lambda p: (best_first(p, mode), p.arrival, p.pid))

        # If a higher-priority process arrived, switch to it
        if chosen.pid != current:
            if current is not None:
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
            finished += 1
            current   = None
            seg_start = clock

    return procs, timeline


# --- 6. Priority + Round Robin ------------------------------------------------
def run_priority_rr(processes, mode, quantum):
    procs = copy.deepcopy(processes)
    n     = len(procs)

    # Sort all processes by arrival for step-by-step loading
    by_arrival = sorted(procs, key=lambda p: (p.arrival, best_first(p, mode), p.pid))
    idx        = 0
    queues     = {}   # one deque per priority level: {priority_key: deque}
    timeline   = []
    clock      = 0
    finished   = 0

    def load_arrivals(up_to):
        # Move any newly arrived processes into their priority queue
        nonlocal idx
        while idx < n and by_arrival[idx].arrival <= up_to:
            p   = by_arrival[idx]
            key = best_first(p, mode)
            if key not in queues:
                queues[key] = deque()
            queues[key].append(p)
            idx += 1

    load_arrivals(clock)  # load anything arriving at time 0

    while finished < n:
        if not queues:
            # All queues empty — idle until next arrival
            next_arrival = by_arrival[idx].arrival
            timeline.append((clock, next_arrival, None))
            clock = next_arrival
            load_arrivals(clock)
            continue

        # Pick the highest-priority group (smallest key = highest priority)
        best_key = min(queues.keys())
        q        = queues[best_key]

        if not q:
            del queues[best_key]  # empty group, remove it
            continue

        p = q.popleft()
        if p.start_time == -1:
            p.start_time = clock

        run_time = min(quantum, p.remaining)
        end_time = clock + run_time

        # Check if a higher-priority process arrives during this slice
        interrupt_at = None
        for future in by_arrival[idx:]:
            if future.arrival >= end_time:
                break
            if best_first(future, mode) < best_key:
                interrupt_at = future.arrival
                break

        if interrupt_at is not None:
            # Run only up to the point where the higher-priority arrives
            actual = interrupt_at - clock
            if actual > 0:
                timeline.append((clock, interrupt_at, p.pid))
                p.remaining -= actual
                clock        = interrupt_at
            load_arrivals(clock)
            if p.remaining > 0:
                # Put interrupted process at the front of its queue
                key = best_first(p, mode)
                if key not in queues:
                    queues[key] = deque()
                queues[key].appendleft(p)
        else:
            # No interruption — run the full slice
            timeline.append((clock, end_time, p.pid))
            p.remaining -= run_time
            clock        = end_time
            load_arrivals(clock)
            if p.remaining == 0:
                p.finish_time = clock
                p.calc_results()
                finished += 1
                if not q and best_key in queues:
                    del queues[best_key]
            else:
                q.append(p)  # back of its priority group

    return procs, timeline


# =============================================================================
# SECTION 4 – GANTT CHART WIDGET
# =============================================================================
# Draws the schedule as colored blocks on a canvas.
# Each process gets a unique color. Idle periods show as dark "IDLE" blocks.

class GanttChart(ctk.CTkFrame):

    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color=C_PANEL, corner_radius=10, **kwargs)
        # We use a plain tk.Canvas because CTk doesn't have one
        self.canvas = tk.Canvas(self, bg=C_PANEL, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=2, pady=2)

    def draw(self, timeline, processes, show_grid=False):
        self.canvas.delete("all")

        color_of = {p.pid: COLORS[i % len(COLORS)] for i, p in enumerate(processes)}
        color_of[None] = C_IDLE

        merged = []
        for start, end, pid in timeline:
            if merged and merged[-1][2] == pid:
                merged[-1] = (merged[-1][0], end, pid)
            else:
                merged.append([start, end, pid])

        total_time = merged[-1][1] if merged else 1
        px = max(24, min(52, 600 // max(total_time, 1)))

        BLOCK_TOP = 10
        BLOCK_BOT = BLOCK_TOP + 46

        W = 16 * 2 + total_time * px + 20
        H = 10 + 46 + 30

        self.canvas.config(scrollregion=(0, 0, W, H), width=W, height=H)

        # GRID
        if show_grid:
            for t in range(total_time + 1):
                x = 16 + t * px
                self.canvas.create_line(x, BLOCK_TOP, x, BLOCK_BOT,
                                        fill="#2a2f45", dash=(2,2))
                self.canvas.create_text(x, BLOCK_BOT + 12,
                                        text=str(t),
                                        fill=C_DIM,
                                        font=("Segoe UI", 9))

        # BLOCKS
        for start, end, pid in merged:
            x0 = 16 + start * px
            x1 = 16 + end * px
            color = color_of.get(pid, C_IDLE)
            label = pid if pid else "IDLE"

            self.canvas.create_rectangle(x0, BLOCK_TOP, x1, BLOCK_BOT,
                                        fill=color, outline="#000", width=1)

            font_size = 10 if (x1 - x0) < 34 else 12
            self.canvas.create_text((x0 + x1) / 2, (BLOCK_TOP + BLOCK_BOT) / 2,
                                    text=label,
                                    fill="#000" if pid else C_DIM,
                                    font=("Segoe UI", font_size, "bold"))

            if not show_grid:
                self.canvas.create_text(x0, BLOCK_BOT + 4,
                                        text=str(start),
                                        anchor="n", fill=C_DIM,
                                        font=("Segoe UI", 9))

        # END LABEL
        self.canvas.create_text(16 + total_time * px, BLOCK_BOT + 4,
                                text=str(total_time),
                                anchor="n",
                                fill=C_DIM,
                                font=("Segoe UI", 9))

# =============================================================================
# SECTION 5 – RESULTS TABLE WIDGET
# =============================================================================
# Displays a table with one row per process showing WT and TAT,
# plus a bottom row with the averages.

class ResultsTable(ctk.CTkFrame):

    # Column names and pixel widths
    COLS   = ["PID", "Arrival", "Burst", "Priority", "Waiting Time", "Turnaround Time"]
    WIDTHS = [70,    80,        70,      80,          110,            130]

    def __init__(self, parent):
        super().__init__(parent, fg_color=C_PANEL, corner_radius=10)

    def show(self, processes, show_priority):
        # Remove everything from the previous run
        for w in self.winfo_children():
            w.destroy()

        # --- Header row -------------------------------------------------------
        header = ctk.CTkFrame(self, fg_color=C_PANEL2, corner_radius=8)
        header.pack(fill="x", padx=8, pady=(8, 2))

        for name, width in zip(self.COLS, self.WIDTHS):
            if name == "Priority" and not show_priority:
                continue  # hide Priority column if not needed
            ctk.CTkLabel(header, text=name, width=width,
                         font=ctk.CTkFont(size=12, weight="bold"),
                         text_color=C_BLUE).pack(side="left", padx=4, pady=6)

        # --- One data row per process -----------------------------------------
        total_wt = 0
        total_tat = 0

        for i, p in enumerate(processes):
            row_color = COLORS[i % len(COLORS)]

            row = ctk.CTkFrame(self, fg_color=C_PANEL, corner_radius=6)
            row.pack(fill="x", padx=8, pady=2)

            values = [p.pid, p.arrival, p.burst, p.priority, p.waiting, p.turnaround]

            for name, val, width in zip(self.COLS, values, self.WIDTHS):
                if name == "Priority" and not show_priority:
                    continue
                # PID gets the process color; other values are plain white
                color  = row_color if name == "PID" else C_TEXT
                weight = "bold"    if name == "PID" else "normal"
                ctk.CTkLabel(row, text=str(val), width=width,
                             font=ctk.CTkFont(size=13, weight=weight),
                             text_color=color).pack(side="left", padx=4, pady=5)

            total_wt  += p.waiting
            total_tat += p.turnaround

        # --- Averages row -----------------------------------------------------
        n = len(processes)
        avg_row = ctk.CTkFrame(self, fg_color=C_PANEL2, corner_radius=8)
        avg_row.pack(fill="x", padx=8, pady=(4, 8))

        ctk.CTkLabel(avg_row,
                     text=f"  Average Waiting Time:  {total_wt / n:.2f}",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=C_GREEN).pack(side="left", padx=12, pady=6)

        ctk.CTkLabel(avg_row,
                     text=f"Average Turnaround Time:  {total_tat / n:.2f}",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=C_YELLOW).pack(side="left", padx=12, pady=6)


# =============================================================================
# SECTION 6 – PROCESS INPUT ROW WIDGET
# =============================================================================
# One input row for a single process: ● | PID | Arrival | Burst | [Priority]
# Priority is only shown when the selected algorithm needs it.

class ProcessRow(ctk.CTkFrame):

    def __init__(self, parent, number, show_priority, dot_color):
        super().__init__(parent, fg_color=C_PANEL2, corner_radius=8)
        self.show_priority = show_priority

        # Colored dot so each process is easy to spot
        ctk.CTkLabel(self, text="●", text_color=dot_color,
                     font=ctk.CTkFont(size=14), width=24
                     ).grid(row=0, column=0, padx=(10, 4), pady=8)

        # PID field — pre-filled with "P1", "P2", etc.
        self.pid_box = ctk.CTkEntry(self, width=62, font=ctk.CTkFont(size=13),
                                     fg_color=C_PANEL, border_color=C_BORDER,
                                     text_color=C_TEXT)
        self.pid_box.insert(0, f"P{number}")
        self.pid_box.grid(row=0, column=1, padx=6, pady=8)

        # Arrival time — when does this process show up?
        self.arr_box = ctk.CTkEntry(self, width=72, placeholder_text="Arrival",
                                     font=ctk.CTkFont(size=13),
                                     fg_color=C_PANEL, border_color=C_BORDER,
                                     text_color=C_TEXT)
        self.arr_box.insert(0, "0")  # default: arrives at time 0
        self.arr_box.grid(row=0, column=2, padx=6, pady=8)

        # Burst time — how long does this process need on the CPU?
        self.burst_box = ctk.CTkEntry(self, width=72, placeholder_text="e.g. 5",
                                       font=ctk.CTkFont(size=13),
                                       fg_color=C_PANEL, border_color=C_BORDER,
                                       text_color=C_TEXT)
        self.burst_box.grid(row=0, column=3, padx=6, pady=8)

        # Priority — only shown for priority-based algorithms
        self.pri_box = ctk.CTkEntry(self, width=72, placeholder_text="0",
                                     font=ctk.CTkFont(size=13),
                                     fg_color=C_PANEL, border_color=C_BORDER,
                                     text_color=C_TEXT)
        self.pri_box.insert(0, "0")  # default priority is 0
        if show_priority:
            self.pri_box.grid(row=0, column=4, padx=6, pady=8)

    def read(self):
        # Read values directly from the entry widgets (not via StringVar —
        # that caused a bug in older versions of CustomTkinter).
        # Returns (pid, arrival, burst, priority) or raises ValueError.

        pid = self.pid_box.get().strip()
        if not pid:
            raise ValueError("One row has an empty PID. Please name every process.")

        # Arrival
        arr_text = self.arr_box.get().strip()
        if arr_text == "":
            raise ValueError(f"{pid}: Arrival Time is empty.")
        if not arr_text.lstrip("-").isdigit():
            raise ValueError(f"{pid}: Arrival Time must be a number like 0 or 3.")
        arrival = int(arr_text)
        if arrival < 0:
            raise ValueError(f"{pid}: Arrival Time can't be negative.")

        # Burst
        burst_text = self.burst_box.get().strip()
        if burst_text == "":
            raise ValueError(f"{pid}: Burst Time is empty. Enter how long this process runs (e.g. 5).")
        if not burst_text.lstrip("-").isdigit():
            raise ValueError(f"{pid}: Burst Time must be a number like 4 or 10.")
        burst = int(burst_text)
        if burst < 1:
            raise ValueError(f"{pid}: Burst Time must be at least 1.")

        # Priority (blank = 0, that's fine)
        priority = 0
        if self.show_priority:
            pri_text = self.pri_box.get().strip()
            if pri_text != "":
                if not pri_text.lstrip("-").isdigit():
                    raise ValueError(f"{pid}: Priority must be a number. Leave blank to use 0.")
                priority = int(pri_text)

        return pid, arrival, burst, priority

# =============================================================================
# SECTION 7 – MAIN WINDOW
# =============================================================================
# The window has two sides:
#   LEFT  — where you pick the algorithm and enter process data
#   RIGHT — where results (Gantt chart + table) appear after clicking Run

class App(ctk.CTk):

    def __init__(self):
        super().__init__()
        self.title("CPU Scheduling Simulator")
        self.geometry("1200x820")
        self.minsize(1000, 680)
        self.configure(fg_color=C_BG)

        self.algo_index    = 0        # which algorithm is selected (index into ALGO_LIST)
        self.process_rows  = []       # list of ProcessRow widgets currently on screen
        self.priority_mode = "lower"  # "lower" means lower number = higher priority

        self.build_window()

    # -------------------------------------------------------------------------
    # BUILD THE WINDOW
    # -------------------------------------------------------------------------

    def build_window(self):

        # --- Title bar at the top --------------------------------------------
        bar = ctk.CTkFrame(self, fg_color=C_PANEL, height=54, corner_radius=0)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        ctk.CTkLabel(bar, text="  ⬡  CPU Scheduling Simulator",
                     font=ctk.CTkFont(size=18, weight="bold"),
                     text_color=C_BLUE).pack(side="left", padx=8)

        ctk.CTkLabel(bar,
                     text="FCFS · SJF · SRT · Round Robin · Priority · Priority+RR",
                     font=ctk.CTkFont(size=11), text_color=C_DIM).pack(side="left")

        # --- Two-column layout -----------------------------------------------
        body = ctk.CTkFrame(self, fg_color=C_BG)
        body.pack(fill="both", expand=True)

        # Left side: fixed width, contains all the inputs
        left = ctk.CTkScrollableFrame(
            body,
            fg_color=C_BG,
            width=435,
            scrollbar_button_color=C_BORDER,
            scrollbar_button_hover_color=C_BLUE
        )
        left.pack(side="left", fill="y", padx=(10, 5), pady=10)

        # Right side: scrollable, shows results
        right = ctk.CTkScrollableFrame(body, fg_color=C_BG,
                                        scrollbar_button_color=C_BORDER,
                                        scrollbar_button_hover_color=C_BLUE)
        right.pack(side="left", fill="both", expand=True, padx=(5, 10), pady=10)

        self.build_left_side(left)
        self.build_right_side(right)

    # -------------------------------------------------------------------------
    # LEFT SIDE — inputs
    # -------------------------------------------------------------------------

    def build_left_side(self, parent):

        # =====================================================================
        # PART A: Algorithm selector
        # =====================================================================
        algo_panel = self.make_panel(parent, "Algorithm")

        algo_names = [f"  {a['name']}" for a in ALGO_LIST]
        self.algo_var = tk.StringVar(value=algo_names[0])

        ctk.CTkOptionMenu(
            algo_panel,
            values=algo_names,
            variable=self.algo_var,
            command=self.on_algo_changed,   # runs when user picks a different algo
            fg_color=C_PANEL2, button_color=C_BLUE, button_hover_color=C_PURPLE,
            text_color=C_TEXT, font=ctk.CTkFont(size=13),
            dropdown_fg_color=C_PANEL2, dropdown_text_color=C_TEXT,
            dropdown_hover_color=C_BLUE, corner_radius=8, width=400,
        ).pack(padx=12, pady=(0, 6))

        # Small label showing the algorithm type (e.g. "Preemptive")
        self.type_label = ctk.CTkLabel(algo_panel, text="",
                                        font=ctk.CTkFont(size=11),
                                        text_color=C_GREEN)
        self.type_label.pack(anchor="w", padx=12, pady=(0, 2))

        # Plain-English description of the selected algorithm
        self.desc_label = ctk.CTkLabel(algo_panel, text="",
                                        font=ctk.CTkFont(size=11),
                                        text_color=C_DIM,
                                        wraplength=390, justify="left")
        self.desc_label.pack(anchor="w", padx=12, pady=(0, 10))

        # =====================================================================
        # PART B: Time Quantum
        # Only visible for Round Robin and Priority+RR.
        # =====================================================================
        self.quantum_panel = self.make_panel(parent, "Time Quantum")

        ctk.CTkLabel(self.quantum_panel,
                     text="How many time units each process gets per turn:",
                     font=ctk.CTkFont(size=11), text_color=C_DIM
                     ).pack(anchor="w", padx=12, pady=(0, 4))

        self.quantum_box = ctk.CTkEntry(self.quantum_panel, width=80,
                                         font=ctk.CTkFont(size=13),
                                         fg_color=C_PANEL2, border_color=C_BORDER,
                                         text_color=C_TEXT)
        self.quantum_box.insert(0, "2")   # default quantum = 2
        self.quantum_box.pack(anchor="w", padx=12, pady=(0, 10))

        # =====================================================================
        # PART C: Priority Mode
        # Only visible for Priority and Priority+RR.
        # =====================================================================
        self.primode_panel = self.make_panel(parent, "Priority Mode")

        ctk.CTkLabel(self.primode_panel,
                     text="Which number means HIGHER priority?",
                     font=ctk.CTkFont(size=12), text_color=C_TEXT
                     ).pack(anchor="w", padx=12, pady=(0, 6))

        self.primode_menu = ctk.CTkOptionMenu(
            self.primode_panel,
            values=["Lower number  (e.g. 0 = most urgent)",
                    "Higher number  (e.g. 10 = most urgent)"],
            command=self.on_primode_changed,
            fg_color=C_PANEL2, button_color=C_BLUE, button_hover_color=C_PURPLE,
            text_color=C_TEXT, font=ctk.CTkFont(size=12),
            dropdown_fg_color=C_PANEL2, dropdown_text_color=C_TEXT,
            dropdown_hover_color=C_BLUE, corner_radius=6, width=380,
        )
        self.primode_menu.pack(anchor="w", padx=12, pady=(0, 10))

        # =====================================================================
        # PART D: Preemptive toggle
        # Only visible for Priority Scheduling.
        # =====================================================================
        self.preempt_panel = self.make_panel(parent, "Preemption Mode")

        ctk.CTkLabel(self.preempt_panel,
                     text="Can a higher-priority arrival interrupt the current process?",
                     font=ctk.CTkFont(size=11), text_color=C_DIM,
                     wraplength=390).pack(anchor="w", padx=12, pady=(0, 6))

        self.preempt_var = tk.BooleanVar(value=False)

        switch_row = ctk.CTkFrame(self.preempt_panel, fg_color="transparent")
        switch_row.pack(anchor="w", padx=12, pady=(0, 10))

        ctk.CTkSwitch(switch_row, text="",
                      variable=self.preempt_var,
                      onvalue=True, offvalue=False,
                      button_color=C_BLUE, progress_color=C_PURPLE,
                      fg_color=C_BORDER).pack(side="left")

        # This label updates when the switch is toggled
        self.preempt_label = ctk.CTkLabel(switch_row, text="Non-Preemptive",
                                           font=ctk.CTkFont(size=12, weight="bold"),
                                           text_color=C_GREEN)
        self.preempt_label.pack(side="left", padx=8)

        # Watch for switch changes and update the label accordingly
        self.preempt_var.trace_add("write", self.on_preempt_toggled)

        # =====================================================================
        # PART E: Process count slider
        # =====================================================================

        count_panel = self.make_panel(parent, "Number of Processes (min 3)")

        input_row = ctk.CTkFrame(count_panel, fg_color="transparent")
        input_row.pack(anchor="w", padx=12, pady=(0, 6))

        self.count_entry = ctk.CTkEntry(input_row, width=80)
        self.count_entry.insert(0, "3")
        self.count_entry.pack(side="left", padx=(0, 6))

        ctk.CTkButton(input_row, text="Apply", width=80,
                    command=self.apply_process_count).pack(side="left")

        self.count_label = ctk.CTkLabel(count_panel, text="3 processes",
                                        font=ctk.CTkFont(size=11),
                                        text_color=C_BLUE)
        self.count_label.pack(anchor="w", padx=12, pady=(0, 10))

        # =====================================================================
        # PART F: Process input table
        # =====================================================================
        self.proc_panel = self.make_panel(parent, "Process Details")

        # Column header (rebuilt when algo changes to show/hide Priority column)
        self.col_header = ctk.CTkFrame(self.proc_panel, fg_color=C_PANEL2,
                                        corner_radius=6)
        self.col_header.pack(fill="x", padx=8, pady=(0, 4))

        # Rows container (also rebuilt dynamically)
        self.rows_frame = ctk.CTkFrame(self.proc_panel, fg_color="transparent")
        self.rows_frame.pack(fill="x", padx=8, pady=(0, 8))

        # =====================================================================
        # PART G: Run and Clear buttons
        # =====================================================================
        ctk.CTkButton(parent, text="▶  Run Simulation",
                      command=self.run_simulation,
                      height=44, font=ctk.CTkFont(size=15, weight="bold"),
                      fg_color=C_BLUE, hover_color=C_PURPLE,
                      corner_radius=10).pack(fill="x", pady=(0, 4))

        ctk.CTkButton(parent, text="🧹 Clear Inputs (Keep PID)",
                    command=self.clear_inputs,
                    height=34).pack(fill="x", pady=(4,0))
        
        ctk.CTkButton(parent, text="✕  Clear Results",
                      command=self.clear_results,
                      height=34, font=ctk.CTkFont(size=12),
                      fg_color=C_PANEL, hover_color=C_PANEL2,
                      border_color=C_BORDER, border_width=1,
                      text_color=C_DIM, corner_radius=10).pack(fill="x")

        # Trigger the initial UI state
        self.on_algo_changed(self.algo_var.get())

    # -------------------------------------------------------------------------
    # RIGHT SIDE — results
    # -------------------------------------------------------------------------

    def build_right_side(self, parent):

        # --- Placeholder shown before any simulation runs -------------------
        self.placeholder = ctk.CTkFrame(parent, fg_color=C_PANEL, corner_radius=14)
        self.placeholder.pack(fill="both", expand=True)

        ctk.CTkLabel(self.placeholder, text="⬡",
                     font=ctk.CTkFont(size=52), text_color=C_BORDER
                     ).pack(pady=(90, 8))
        ctk.CTkLabel(self.placeholder,
                     text="Configure and run a simulation",
                     font=ctk.CTkFont(size=17, weight="bold"),
                     text_color=C_DIM).pack()
        ctk.CTkLabel(self.placeholder,
                     text="Pick an algorithm on the left, fill in your processes, then click  ▶ Run",
                     font=ctk.CTkFont(size=12), text_color=C_BORDER).pack(pady=4)

        # --- Results frame (hidden until simulation runs) --------------------
        # We create it now but only pack() it after the first Run click.
        self.results_frame = ctk.CTkFrame(parent, fg_color="transparent")

        # Toggle for detailed grid
        self.show_grid = tk.BooleanVar(value=False)

        toggle_row = ctk.CTkFrame(self.results_frame, fg_color="transparent")
        toggle_row.pack(anchor="w", pady=(0,4))

        ctk.CTkSwitch(toggle_row,
                    text="Show Time Grid",
                    variable=self.show_grid).pack(side="left")

        # Gantt chart
        ctk.CTkLabel(self.results_frame, text="Gantt Chart",
             font=ctk.CTkFont(size=14, weight="bold"),
             text_color=C_TEXT).pack(anchor="w", pady=(0, 2))

        # Toggle here (correct placement)
        toggle_row = ctk.CTkFrame(self.results_frame, fg_color="transparent")
        toggle_row.pack(anchor="w", pady=(0,4))

        ctk.CTkSwitch(toggle_row,
                    text="Show Time Grid",
                    variable=self.show_grid).pack(side="left")

        # Horizontal scroll wrapper for the Gantt (in case it's wide)
        gantt_scroll = ctk.CTkScrollableFrame(self.results_frame,
                                               fg_color=C_PANEL,
                                               orientation="horizontal",
                                               height=106, corner_radius=10,
                                               scrollbar_button_color=C_BORDER,
                                               scrollbar_button_hover_color=C_BLUE)
        gantt_scroll.pack(fill="x", pady=(0, 12))

        self.gantt = GanttChart(gantt_scroll, height=92)
        self.gantt.pack(fill="both", expand=True)

        # Results table
        ctk.CTkLabel(self.results_frame, text="Results Table",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=C_TEXT).pack(anchor="w", pady=(0, 4))

        self.table = ResultsTable(self.results_frame)
        self.table.pack(fill="x", pady=(0, 12))

        # Description at the bottom (shows which algo was used and what it does)
        desc_card = ctk.CTkFrame(self.results_frame, fg_color=C_PANEL,
                                  corner_radius=10)
        desc_card.pack(fill="x")
        self.result_desc = ctk.CTkLabel(desc_card, text="",
                                         font=ctk.CTkFont(size=11),
                                         text_color=C_DIM,
                                         wraplength=560, justify="left")
        self.result_desc.pack(anchor="w", padx=12, pady=10)

    # -------------------------------------------------------------------------
    # HELPER: make a panel card with a title
    # -------------------------------------------------------------------------

    def make_panel(self, parent, title):
        # Creates a dark rounded panel with a small title label.
        # Returns the panel frame so we can add content inside it.
        panel = ctk.CTkFrame(parent, fg_color=C_PANEL, corner_radius=12)
        panel.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(panel, text=title,
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=C_DIM).pack(anchor="w", padx=12, pady=(10, 4))
        return panel

    # -------------------------------------------------------------------------
    # CALLBACKS — what happens when the user interacts with controls
    # -------------------------------------------------------------------------

    def on_algo_changed(self, _value):
        # Called when the user picks a different algorithm from the dropdown.

        # Find which algorithm matches the dropdown text
        label = self.algo_var.get().strip()
        self.algo_index = next(
            (i for i, a in enumerate(ALGO_LIST) if a["name"] == label), 0)
        algo = ALGO_LIST[self.algo_index]

        # Update the description text and type badge
        self.desc_label.configure(text=algo["description"])
        is_preemptive = "Preemptive" in algo["type"] and "Non" not in algo["type"]
        self.type_label.configure(
            text=f"⬡  {algo['type']}",
            text_color=C_RED if is_preemptive else C_GREEN)

        # Show or hide each option panel based on what this algorithm needs.
        # pack_forget() removes the panel completely — no grayed-out controls,
        # no empty space, no confusion about what's required.
        self.show_hide(self.quantum_panel,  algo["show_quantum"])
        self.show_hide(self.primode_panel,  algo["show_priority"])
        self.show_hide(self.preempt_panel,  algo["show_preempt"])

        # Rebuild the process rows so the Priority column shows or hides too
        self.rebuild_process_rows(algo["show_priority"])

        self.preempt_var.set(False)
        self.on_preempt_toggled()

    def show_hide(self, panel, should_show):
        # Puts a panel back into the layout or removes it entirely.
        if should_show:
            panel.pack(fill="x", pady=(0, 8))
        else:
            panel.pack_forget()

    def on_primode_changed(self, value):
        # Update which priority mode is active
        self.priority_mode = "lower" if value.startswith("Lower") else "higher"

    def on_preempt_toggled(self, *_):
        # Update the label next to the switch when it's toggled
        if self.preempt_var.get():
            self.preempt_label.configure(text="Preemptive", text_color=C_RED)
        else:
            self.preempt_label.configure(text="Non-Preemptive", text_color=C_GREEN)

    def apply_process_count(self):
        try:
            n = int(self.count_entry.get())
            if n < 3:
                raise ValueError
        except:
            messagebox.showerror("Invalid Input", "Enter a number ≥ 3")
            return

        self.count_var = tk.IntVar(value=n)
        self.count_label.configure(text=f"{n} processes")

        algo = ALGO_LIST[self.algo_index]
        self.rebuild_process_rows(algo["show_priority"])

    def rebuild_process_rows(self, show_priority):
        # Clear and recreate the column header and all input rows.
        # This is called whenever the algorithm or process count changes.

        # Rebuild header labels
        for w in self.col_header.winfo_children():
            w.destroy()

        cols = [("", 28), ("PID", 62), ("Arrival", 72), ("Burst", 72)]
        if show_priority:
            cols.append(("Priority", 72))

        for text, width in cols:
            ctk.CTkLabel(self.col_header, text=text, width=width,
                         font=ctk.CTkFont(size=11, weight="bold"),
                         text_color=C_BLUE).pack(side="left", padx=4, pady=4)

        # Rebuild input rows
        for w in self.rows_frame.winfo_children():
            w.destroy()
        self.process_rows.clear()

        n = int(float(self.count_var.get()))
        for i in range(n):
            color = COLORS[i % len(COLORS)]
            row   = ProcessRow(self.rows_frame, i, show_priority, color)
            row.pack(fill="x", pady=3)
            self.process_rows.append(row)

    # -------------------------------------------------------------------------
    # RUN SIMULATION — the main action
    # -------------------------------------------------------------------------

    def run_simulation(self):
        algo = ALGO_LIST[self.algo_index]

        # --- Step 1: Read the Time Quantum (if needed) -----------------------
        quantum = 2  # default; not used unless the algorithm needs it
        if algo["show_quantum"]:
            q = self.quantum_box.get().strip()
            if not q.isdigit() or int(q) < 1:
                messagebox.showerror("Bad Input",
                    "Time Quantum must be a positive number like 2 or 3.")
                return
            quantum = int(q)

        # --- Step 2: Read all process rows -----------------------------------
        processes = []
        used_pids = set()
        try:
            for row in self.process_rows:
                pid, arrival, burst, priority = row.read()
                if pid in used_pids:
                    raise ValueError(
                        f"'{pid}' is used more than once. Each process needs a unique name.")
                used_pids.add(pid)
                processes.append(Process(pid, arrival, burst, priority))
        except ValueError as err:
            messagebox.showerror("Input Error", str(err))
            return

        # --- Step 3: Run the chosen algorithm --------------------------------
        mode      = self.priority_mode        # "lower" or "higher"
        preemptive = self.preempt_var.get()   # True or False

        try:
            key = algo["key"]
            if   key == "FCFS":
                result, timeline = run_fcfs(processes)
            elif key == "SJF":
                result, timeline = run_sjf(processes)
            elif key == "SRT":
                result, timeline = run_srt(processes)
            elif key == "RR":
                result, timeline = run_rr(processes, quantum)
            elif key == "Priority":
                if preemptive:
                    result, timeline = run_priority_p(processes, mode)
                else:
                    result, timeline = run_priority_np(processes, mode)
            elif key == "Priority+RR":
                result, timeline = run_priority_rr(processes, mode, quantum)
            else:
                raise RuntimeError(f"Unknown algorithm: {key}")
        except Exception as err:
            messagebox.showerror("Error", str(err))
            return

        # --- Step 4: Show the results ----------------------------------------
        self.show_results(result, timeline, algo)

    def show_results(self, processes, timeline, algo):

        # CLEAR right side first (important)
        for widget in self.results_frame.winfo_children():
            widget.update()

        self.placeholder.pack_forget()

        # FORCE show results frame
        if not self.results_frame.winfo_ismapped():
            self.results_frame.pack(fill="both", expand=True)

        self.gantt.draw(timeline, processes, self.show_grid.get())
        self.table.show(processes, algo["show_priority"])

        mode_text = ""
        if algo["key"] == "Priority":
            mode_text = " (Preemptive)" if self.preempt_var.get() else " (Non-Preemptive)"

        self.result_desc.configure(
            text=f"{algo['name']}{mode_text} · {algo['type']} — {algo['description']}"
        )

    def clear_results(self):
        # Go back to the placeholder screen
        self.results_frame.pack_forget()
        self.placeholder.pack(fill="both", expand=True)

    def clear_inputs(self):
        for row in self.process_rows:
            row.arr_box.delete(0, "end")
            row.arr_box.insert(0, "0")

            row.burst_box.delete(0, "end")

            if row.show_priority:
                row.pri_box.delete(0, "end")
                row.pri_box.insert(0, "0")


# =============================================================================
# START THE APP
# =============================================================================

if __name__ == "__main__":
    app = App()
    app.mainloop()