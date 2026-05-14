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

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# --- Colors ------------------------------------------------------------------
C_BG     = "#0f1117"
C_PANEL  = "#1a1d27"
C_PANEL2 = "#20243a"
C_BORDER = "#2a2f45"
C_BLUE   = "#4f8ef7"
C_PURPLE = "#7c5ef5"
C_GREEN  = "#3ddc84"
C_YELLOW = "#f5c842"
C_RED    = "#f55e5e"
C_TEXT   = "#e8eaf6"
C_DIM    = "#7b82a0"
C_IDLE   = "#3a3f55"

COLORS = ["#4f8ef7","#3ddc84","#f5c842","#f55e5e","#c084fc",
          "#38bdf8","#fb923c","#f472b6","#a3e635","#34d399"]


# =============================================================================
# SECTION 1 – ALGORITHM INFO
# =============================================================================

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
        "type":          "Preemptive",
        "description":   "Processes are grouped by priority level. Within each "
                         "group, Round Robin is applied using the time quantum — "
                         "every process in the same priority group takes turns "
                         "with equal time slices. Higher-priority groups are "
                         "always served first.",
        "show_quantum":  True,
        "show_priority": True,
        "show_preempt":  False,
    },
]


# =============================================================================
# SECTION 2 – PROCESS DATA
# =============================================================================

class Process:
    def __init__(self, pid, arrival, burst, priority=0):
        self.pid         = pid
        self.arrival     = arrival
        self.burst       = burst
        self.priority    = priority
        self.remaining   = burst   # counts down during simulation
        self.start_time  = -1      # set on first CPU access
        self.finish_time = 0
        self.waiting     = 0
        self.turnaround  = 0

    def calc_results(self):
        self.turnaround = self.finish_time - self.arrival
        self.waiting    = self.turnaround  - self.burst


# =============================================================================
# SECTION 3 – SCHEDULING ALGORITHMS
# =============================================================================

def best_first(process, mode):
    # Returns a number used for sorting — smallest = highest priority.
    # "lower" mode: P0 = most urgent  → return priority as-is
    # "higher" mode: P10 = most urgent → negate so it sorts to the front
    return process.priority if mode == "lower" else -process.priority


# --- FCFS --------------------------------------------------------------------
def run_fcfs(processes):
    procs    = sorted(copy.deepcopy(processes), key=lambda p: (p.arrival, p.pid))
    timeline = []
    clock    = 0
    for p in procs:
        if clock < p.arrival:
            timeline.append((clock, p.arrival, None))  # idle
            clock = p.arrival
        p.start_time  = clock
        clock        += p.burst
        p.finish_time = clock
        p.calc_results()
        timeline.append((p.start_time, p.finish_time, p.pid))
    return procs, timeline


# --- SJF (Non-Preemptive) ----------------------------------------------------
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


# --- SRT (Preemptive SJF) ----------------------------------------------------
def run_srt(processes):
    # At every tick, the process with the LEAST remaining time runs.
    # A new arrival with less time will immediately preempt the current process.
    procs     = copy.deepcopy(processes)
    n         = len(procs)
    finished  = 0
    timeline  = []
    clock     = 0
    current   = None   # PID of what's running right now
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
            finished += 1
            current   = None
            seg_start = clock
    return procs, timeline


# --- Round Robin -------------------------------------------------------------
def run_rr(processes, quantum):
    # Each process gets `quantum` time units, then moves to the back of the queue.
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


# --- Priority (Non-Preemptive) -----------------------------------------------
def run_priority_np(processes, mode):
    # Pick the highest-priority ARRIVED process each time the CPU is free.
    # Once running, the process is NEVER interrupted — it runs to completion.
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


# --- Priority (Preemptive) ---------------------------------------------------
def run_priority_p(processes, mode):
    # At every single tick, we re-check which process has the best priority.
    # If a NEW process arrives with a BETTER priority than what's running NOW,
    # the current process is immediately kicked off the CPU (preempted).
    # This is the KEY difference from Non-Preemptive — the running process
    # is NOT safe from being interrupted.
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
        # Every tick: pick best priority among ALL currently arrived processes.
        # If a higher-priority process just arrived, it will win this comparison
        # and `chosen.pid != current` will be True → preemption happens.
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


# --- Priority + Round Robin --------------------------------------------------
def run_priority_rr(processes, mode, quantum):
    # HOW IT WORKS:
    # 1. Processes are separated into priority groups.
    # 2. The HIGHEST-priority group always runs first.
    # 3. WITHIN that group, Round Robin is applied — each process gets
    #    exactly `quantum` time units before the next process in the same
    #    group gets its turn.
    # 4. Round Robin continues within the group until ALL processes in that
    #    group finish. Only then does the next priority group start.
    # 5. If a higher-priority process arrives mid-slice, it preempts the
    #    current process and its group takes over.
    #
    # NOTE: Round Robin is NOT bypassed. It runs inside each priority group.
    # If all processes have the same priority, this behaves exactly like RR.

    procs    = copy.deepcopy(processes)
    n        = len(procs)
    # Sort by arrival so we can load them in order
    by_arr   = sorted(procs, key=lambda p: (p.arrival, best_first(p, mode), p.pid))
    idx      = 0
    # queues: dict mapping priority_key → deque of processes in that group
    queues   = {}
    timeline = []
    clock    = 0
    finished = 0

    def load_arrivals(up_to):
        # Add any newly arrived processes into their correct priority queue
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

        # Pick the highest-priority group (lowest sort key = best priority)
        best_key = min(queues.keys())
        q        = queues[best_key]

        if not q:
            del queues[best_key]
            continue

        # Take the next process from the front of this priority group's RR queue
        p = q.popleft()
        if p.start_time == -1:
            p.start_time = clock

        # This process will run for UP TO `quantum` units
        run    = min(quantum, p.remaining)
        end_t  = clock + run

        # Check if a HIGHER-priority process arrives before this slice finishes
        # (i.e., a process whose priority_key < best_key arrives before end_t)
        intr_at = None
        for future in by_arr[idx:]:
            if future.arrival >= end_t:
                break
            if best_first(future, mode) < best_key:
                intr_at = future.arrival
                break

        if intr_at is not None:
            # A higher-priority arrival interrupts this slice
            actual = intr_at - clock
            if actual > 0:
                timeline.append((clock, intr_at, p.pid))
                p.remaining -= actual
                clock        = intr_at
            load_arrivals(clock)
            if p.remaining > 0:
                # Put this process back at the FRONT of its group's RR queue
                # (it will continue its remaining slice later)
                key = best_first(p, mode)
                if key not in queues:
                    queues[key] = deque()
                queues[key].appendleft(p)
        else:
            # No interruption — run the full slice (or to completion)
            timeline.append((clock, end_t, p.pid))
            p.remaining -= run
            clock        = end_t
            load_arrivals(clock)
            if p.remaining == 0:
                # Process finished
                p.finish_time = clock
                p.calc_results()
                finished += 1
                if not q and best_key in queues:
                    del queues[best_key]
            else:
                # Not done — goes to the BACK of its group's RR queue
                # This is the Round Robin rotation within the priority group
                q.append(p)

    return procs, timeline


# =============================================================================
# SECTION 4 – GANTT CHART WIDGET
# =============================================================================

class GanttChart(ctk.CTkFrame):
    # Draws colored process blocks on a canvas.
    # Toggle "Detailed view" to see every individual time unit on the axis.

    BLOCK_TOP = 8     # pixels from top of canvas to top of block
    BLOCK_H   = 44    # height of each process block
    PAD_X     = 20    # left/right padding

    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color=C_PANEL, corner_radius=10, **kwargs)

        # --- Toggle row (top of the widget) ----------------------------------
        toggle_row = ctk.CTkFrame(self, fg_color="transparent")
        toggle_row.pack(fill="x", padx=10, pady=(6, 0))

        ctk.CTkLabel(toggle_row, text="Detailed view:",
                     font=ctk.CTkFont(size=10), text_color=C_DIM
                     ).pack(side="left", padx=(0, 4))

        self.detailed_var = tk.BooleanVar(value=False)
        ctk.CTkSwitch(toggle_row, text="",
                      variable=self.detailed_var,
                      onvalue=True, offvalue=False,
                      width=36, height=18,
                      button_color=C_BLUE, progress_color=C_PURPLE,
                      fg_color=C_BORDER,
                      command=self.redraw
                      ).pack(side="left")

        ctk.CTkLabel(toggle_row,
                     text="  Off = block labels only   |   On = full number line per unit",
                     font=ctk.CTkFont(size=9), text_color=C_DIM
                     ).pack(side="left", padx=6)

        # --- Canvas ----------------------------------------------------------
        self.canvas = tk.Canvas(self, bg=C_PANEL, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=4, pady=(2, 6))

        # Saved data so we can redraw when the toggle changes
        self._timeline  = []
        self._processes = []

    def draw(self, timeline, processes):
        self._timeline  = timeline
        self._processes = processes
        self.redraw()

    def redraw(self):
        self._render(self._timeline, self._processes, self.detailed_var.get())

    def _render(self, timeline, processes, detailed):
        self.canvas.delete("all")
        if not timeline or not processes:
            return

        # Map PID → color
        color_of = {p.pid: COLORS[i % len(COLORS)] for i, p in enumerate(processes)}
        color_of[None] = C_IDLE

        # Merge back-to-back same-pid segments (keeps the chart tidy)
        merged = []
        for start, end, pid in timeline:
            if merged and merged[-1][2] == pid:
                merged[-1] = (merged[-1][0], end, pid)
            else:
                merged.append([start, end, pid])

        total_time = merged[-1][1] if merged else 1

        # --- Calculate pixel width per time unit ----------------------------
        # In detailed mode we need enough room so every tick number is readable.
        # In simplified mode we just need the blocks to look reasonable.
        if detailed:
            # Each unit gets at least 28px so numbers don't overlap
            px = max(28, min(60, 700 // max(total_time, 1)))
        else:
            # Simplified: slightly wider blocks are fine
            px = max(30, min(60, 600 // max(total_time, 1)))

        BLOCK_TOP = self.BLOCK_TOP
        BLOCK_BOT = BLOCK_TOP + self.BLOCK_H
        PAD_X     = self.PAD_X

        # Axis sits below the blocks
        TICK_Y    = BLOCK_BOT + 2    # bottom of tick lines
        LABEL_Y   = BLOCK_BOT + 4   # top of axis number labels

        canvas_w  = PAD_X * 2 + total_time * px + 10
        # Extra vertical room in detailed mode for axis labels
        canvas_h  = BLOCK_BOT + (28 if detailed else 22)

        self.canvas.configure(width=canvas_w, height=canvas_h,
                              scrollregion=(0, 0, canvas_w, canvas_h))

        # --- Draw blocks -----------------------------------------------------
        for start, end, pid in merged:
            x0    = PAD_X + start * px
            x1    = PAD_X + end   * px
            color = color_of.get(pid, C_IDLE)
            label = pid if pid else "IDLE"

            # Main colored rectangle
            self.canvas.create_rectangle(
                x0, BLOCK_TOP, x1, BLOCK_BOT,
                fill=color, outline="#111111", width=1)

            # In detailed mode: draw a divider line for every single time unit
            # so you can visually see each unit boundary inside the block
            if detailed:
                for t in range(start + 1, end):
                    tx = PAD_X + t * px
                    self.canvas.create_line(
                        tx, BLOCK_TOP + 2, tx, BLOCK_BOT - 2,
                        fill="#00000040", width=1, dash=(2, 2))

            # Process name label centered inside the block
            font_size = 9 if (x1 - x0) < 30 else 11
            self.canvas.create_text(
                (x0 + x1) / 2, (BLOCK_TOP + BLOCK_BOT) / 2,
                text=label,
                fill="#000000" if pid else C_DIM,
                font=("Segoe UI", font_size, "bold"))

        # --- Draw axis -------------------------------------------------------
        if detailed:
            # Full number line: every time unit from 0 to total_time gets a
            # tick mark and its own number label directly below the blocks.
            for t in range(total_time + 1):
                tx = PAD_X + t * px
                # Short tick mark
                self.canvas.create_line(
                    tx, BLOCK_BOT, tx, TICK_Y + 3,
                    fill=C_DIM, width=1)
                # Number label
                self.canvas.create_text(
                    tx, LABEL_Y + 3,
                    text=str(t), anchor="n",
                    fill=C_DIM, font=("Segoe UI", 8))
        else:
            # Simplified: only show the start and end time of each distinct block.
            # e.g. if P1 runs from 0→5, show "0" and "5".
            shown = set()
            for start, end, _ in merged:
                for t in [start, end]:
                    if t not in shown:
                        shown.add(t)
                        tx = PAD_X + t * px
                        self.canvas.create_text(
                            tx, LABEL_Y,
                            text=str(t), anchor="n",
                            fill=C_DIM, font=("Segoe UI", 9))


# =============================================================================
# SECTION 5 – RESULTS TABLE
# =============================================================================

class ResultsTable(ctk.CTkFrame):

    COLS   = ["PID", "Arrival", "Burst", "Priority", "Waiting Time", "Turnaround Time"]
    WIDTHS = [70,    80,        70,      80,          110,            130]

    def __init__(self, parent):
        super().__init__(parent, fg_color=C_PANEL, corner_radius=10)

    def show(self, processes, show_priority):
        for w in self.winfo_children():
            w.destroy()

        # Header row
        header = ctk.CTkFrame(self, fg_color=C_PANEL2, corner_radius=8)
        header.pack(fill="x", padx=8, pady=(8, 2))
        for name, width in zip(self.COLS, self.WIDTHS):
            if name == "Priority" and not show_priority:
                continue
            ctk.CTkLabel(header, text=name, width=width,
                         font=ctk.CTkFont(size=12, weight="bold"),
                         text_color=C_BLUE).pack(side="left", padx=4, pady=6)

        total_wt = total_tat = 0
        for i, p in enumerate(processes):
            row_color = COLORS[i % len(COLORS)]
            row = ctk.CTkFrame(self, fg_color=C_PANEL, corner_radius=6)
            row.pack(fill="x", padx=8, pady=2)
            values = [p.pid, p.arrival, p.burst, p.priority, p.waiting, p.turnaround]
            for name, val, width in zip(self.COLS, values, self.WIDTHS):
                if name == "Priority" and not show_priority:
                    continue
                color  = row_color if name == "PID" else C_TEXT
                weight = "bold"    if name == "PID" else "normal"
                ctk.CTkLabel(row, text=str(val), width=width,
                             font=ctk.CTkFont(size=13, weight=weight),
                             text_color=color).pack(side="left", padx=4, pady=5)
            total_wt  += p.waiting
            total_tat += p.turnaround

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
# SECTION 6 – PROCESS INPUT ROW
# =============================================================================

class ProcessRow(ctk.CTkFrame):

    def __init__(self, parent, number, show_priority, dot_color):
        super().__init__(parent, fg_color=C_PANEL2, corner_radius=8)
        self.show_priority = show_priority

        ctk.CTkLabel(self, text="●", text_color=dot_color,
                     font=ctk.CTkFont(size=14), width=24
                     ).grid(row=0, column=0, padx=(10, 4), pady=8)

        self.pid_box = ctk.CTkEntry(self, width=62, font=ctk.CTkFont(size=13),
                                     fg_color=C_PANEL, border_color=C_BORDER,
                                     text_color=C_TEXT)
        self.pid_box.insert(0, f"P{number}")  # starts at P0
        self.pid_box.grid(row=0, column=1, padx=6, pady=8)

        self.arr_box = ctk.CTkEntry(self, width=72, placeholder_text="Arrival",
                                     font=ctk.CTkFont(size=13),
                                     fg_color=C_PANEL, border_color=C_BORDER,
                                     text_color=C_TEXT)
        self.arr_box.insert(0, "0")
        self.arr_box.grid(row=0, column=2, padx=6, pady=8)

        self.burst_box = ctk.CTkEntry(self, width=72, placeholder_text="e.g. 5",
                                       font=ctk.CTkFont(size=13),
                                       fg_color=C_PANEL, border_color=C_BORDER,
                                       text_color=C_TEXT)
        self.burst_box.grid(row=0, column=3, padx=6, pady=8)

        self.pri_box = ctk.CTkEntry(self, width=72, placeholder_text="0",
                                     font=ctk.CTkFont(size=13),
                                     fg_color=C_PANEL, border_color=C_BORDER,
                                     text_color=C_TEXT)
        self.pri_box.insert(0, "0")
        if show_priority:
            self.pri_box.grid(row=0, column=4, padx=6, pady=8)

    def clear_inputs(self):
        # Resets Arrival, Burst, Priority — PID name is kept
        self.arr_box.delete(0, "end")
        self.arr_box.insert(0, "0")
        self.burst_box.delete(0, "end")
        self.pri_box.delete(0, "end")
        self.pri_box.insert(0, "0")

    def read(self):
        pid = self.pid_box.get().strip()
        if not pid:
            raise ValueError("One row has an empty PID.")

        arr_text = self.arr_box.get().strip()
        if not arr_text:
            raise ValueError(f"{pid}: Arrival Time is empty.")
        if not arr_text.lstrip("-").isdigit():
            raise ValueError(f"{pid}: Arrival Time must be a whole number.")
        arrival = int(arr_text)
        if arrival < 0:
            raise ValueError(f"{pid}: Arrival Time cannot be negative.")

        burst_text = self.burst_box.get().strip()
        if not burst_text:
            raise ValueError(f"{pid}: Burst Time is empty — enter how long this process runs (e.g. 5).")
        if not burst_text.lstrip("-").isdigit():
            raise ValueError(f"{pid}: Burst Time must be a whole number.")
        burst = int(burst_text)
        if burst < 1:
            raise ValueError(f"{pid}: Burst Time must be at least 1.")

        priority = 0
        if self.show_priority:
            pri_text = self.pri_box.get().strip()
            if pri_text:
                if not pri_text.lstrip("-").isdigit():
                    raise ValueError(f"{pid}: Priority must be a number. Leave blank to use 0.")
                priority = int(pri_text)

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
        self.configure(fg_color=C_BG)

        self.algo_index    = 0
        self.process_rows  = []
        self.priority_mode = "lower"
        self.process_count = 3

        self.build_window()

    # =========================================================================
    # WINDOW LAYOUT
    # =========================================================================

    def build_window(self):
        # Title bar
        bar = ctk.CTkFrame(self, fg_color=C_PANEL, height=54, corner_radius=0)
        bar.pack(fill="x")
        bar.pack_propagate(False)
        ctk.CTkLabel(bar, text="  ⬡  CPU Scheduling Simulator",
                     font=ctk.CTkFont(size=18, weight="bold"),
                     text_color=C_BLUE).pack(side="left", padx=8)
        ctk.CTkLabel(bar,
                     text="FCFS · SJF · SRT · Round Robin · Priority · Priority+RR",
                     font=ctk.CTkFont(size=11), text_color=C_DIM).pack(side="left")

        body = ctk.CTkFrame(self, fg_color=C_BG)
        body.pack(fill="both", expand=True)

        # Left column — scrollable for many processes
        left = ctk.CTkScrollableFrame(body, fg_color=C_BG, width=450,
                                       scrollbar_button_color=C_BORDER,
                                       scrollbar_button_hover_color=C_BLUE)
        left.pack(side="left", fill="y", padx=(10, 5), pady=10)

        # Right column — results
        right = ctk.CTkScrollableFrame(body, fg_color=C_BG,
                                        scrollbar_button_color=C_BORDER,
                                        scrollbar_button_hover_color=C_BLUE)
        right.pack(side="left", fill="both", expand=True, padx=(5, 10), pady=10)

        self.build_left_side(left)
        self.build_right_side(right)

    # =========================================================================
    # LEFT SIDE — all configuration inputs
    # Order: Algorithm → (optional) options panels → Process Count →
    #        Process Table → (optional) options panels → Run / Clear
    # =========================================================================

    def build_left_side(self, parent):

        # ----- Algorithm selector --------------------------------------------
        algo_panel = self.make_panel(parent, "Algorithm")

        algo_names = [f"  {a['name']}" for a in ALGO_LIST]
        self.algo_var = tk.StringVar(value=algo_names[0])
        ctk.CTkOptionMenu(
            algo_panel, values=algo_names, variable=self.algo_var,
            command=self.on_algo_changed,
            fg_color=C_PANEL2, button_color=C_BLUE, button_hover_color=C_PURPLE,
            text_color=C_TEXT, font=ctk.CTkFont(size=13),
            dropdown_fg_color=C_PANEL2, dropdown_text_color=C_TEXT,
            dropdown_hover_color=C_BLUE, corner_radius=8, width=415,
        ).pack(padx=12, pady=(0, 6))

        self.type_label = ctk.CTkLabel(algo_panel, text="",
                                        font=ctk.CTkFont(size=11, weight="bold"),
                                        text_color=C_GREEN, anchor="center")
        self.type_label.pack(fill="x", padx=12, pady=(0, 2))

        self.desc_label = ctk.CTkLabel(algo_panel, text="",
                                        font=ctk.CTkFont(size=11),
                                        text_color=C_DIM,
                                        wraplength=400, justify="left")
        self.desc_label.pack(anchor="w", padx=12, pady=(0, 10))

        # ----- Process count -------------------------------------------------
        count_panel = self.make_panel(parent, "Number of Processes  (minimum 3)")
        count_row   = ctk.CTkFrame(count_panel, fg_color="transparent")
        count_row.pack(fill="x", padx=12, pady=(0, 10))

        ctk.CTkButton(count_row, text="−", width=32, height=32,
                      font=ctk.CTkFont(size=16, weight="bold"),
                      fg_color=C_PANEL2, hover_color=C_BORDER,
                      text_color=C_TEXT, corner_radius=6,
                      command=self.decrease_count).pack(side="left")

        self.count_display = ctk.CTkLabel(count_row, text="3",
                                           font=ctk.CTkFont(size=15, weight="bold"),
                                           text_color=C_BLUE, width=36)
        self.count_display.pack(side="left", padx=4)

        ctk.CTkButton(count_row, text="+", width=32, height=32,
                      font=ctk.CTkFont(size=16, weight="bold"),
                      fg_color=C_PANEL2, hover_color=C_BORDER,
                      text_color=C_TEXT, corner_radius=6,
                      command=self.increase_count).pack(side="left")

        # Manual entry box — type the number directly
        ctk.CTkLabel(count_row, text="   or type:",
                     font=ctk.CTkFont(size=11), text_color=C_DIM
                     ).pack(side="left", padx=(8, 4))

        self.count_entry = ctk.CTkEntry(count_row, width=52, height=30,
                                         font=ctk.CTkFont(size=13),
                                         fg_color=C_PANEL2, border_color=C_BORDER,
                                         text_color=C_TEXT)
        self.count_entry.pack(side="left")
        # Apply typed value on Enter or focus-out
        self.count_entry.bind("<Return>",    lambda e: self.apply_typed_count())
        self.count_entry.bind("<FocusOut>",  lambda e: self.apply_typed_count())

        # ----- Process input table -------------------------------------------
        self.proc_panel = self.make_panel(parent, "Process Details")

        self.col_header = ctk.CTkFrame(self.proc_panel, fg_color=C_PANEL2,
                                        corner_radius=6)
        self.col_header.pack(fill="x", padx=8, pady=(0, 4))

        self.rows_frame = ctk.CTkFrame(self.proc_panel, fg_color="transparent")
        self.rows_frame.pack(fill="x", padx=8, pady=(0, 8))

        # ----- Optional panels — appear ABOVE Run button ---------------------
        # These are created here but their position in layout is controlled
        # by show_hide() which calls pack() with the correct ordering.
        # They sit between Process Details and the Run button.

        self.quantum_panel = self.make_panel(parent, "Time Quantum")
        ctk.CTkLabel(self.quantum_panel,
                     text="Time units each process gets per turn (used by RR and Priority+RR):",
                     font=ctk.CTkFont(size=11), text_color=C_DIM,
                     wraplength=400, justify="left"
                     ).pack(anchor="w", padx=12, pady=(0, 4))
        self.quantum_box = ctk.CTkEntry(self.quantum_panel, width=80,
                                         font=ctk.CTkFont(size=13),
                                         fg_color=C_PANEL2, border_color=C_BORDER,
                                         text_color=C_TEXT)
        self.quantum_box.insert(0, "2")
        self.quantum_box.pack(anchor="w", padx=12, pady=(0, 10))

        self.primode_panel = self.make_panel(parent, "Priority Mode")
        ctk.CTkLabel(self.primode_panel,
                     text="Which number means HIGHER priority?",
                     font=ctk.CTkFont(size=12), text_color=C_TEXT,
                     anchor="center"
                     ).pack(fill="x", padx=12, pady=(0, 6))
        self.primode_menu = ctk.CTkOptionMenu(
            self.primode_panel,
            values=["Lower number  (e.g. 0 = most urgent)",
                    "Higher number  (e.g. 10 = most urgent)"],
            command=self.on_primode_changed,
            fg_color=C_PANEL2, button_color=C_BLUE, button_hover_color=C_PURPLE,
            text_color=C_TEXT, font=ctk.CTkFont(size=12),
            dropdown_fg_color=C_PANEL2, dropdown_text_color=C_TEXT,
            dropdown_hover_color=C_BLUE, corner_radius=6, width=415,
        )
        self.primode_menu.pack(anchor="w", padx=12, pady=(0, 10))

        self.preempt_panel = self.make_panel(parent, "Preemption Mode")
        ctk.CTkLabel(
            self.preempt_panel,
            text=(
                "OFF  →  Non-Preemptive: the running process finishes completely "
                "before any other process can run, even if a higher-priority "
                "process arrives.\n\n"
                "ON   →  Preemptive: if a higher-priority process arrives while "
                "another is running, it immediately interrupts it and takes the CPU."
            ),
            font=ctk.CTkFont(size=11),
            text_color=C_DIM,
            wraplength=400,
            justify="left"
        ).pack(anchor="w", padx=12, pady=(0, 8))

        self.preempt_var = tk.BooleanVar(value=False)
        switch_row = ctk.CTkFrame(self.preempt_panel, fg_color="transparent")
        switch_row.pack(anchor="w", padx=12, pady=(0, 10))
        ctk.CTkSwitch(switch_row, text="",
                      variable=self.preempt_var, onvalue=True, offvalue=False,
                      button_color=C_BLUE, progress_color=C_PURPLE,
                      fg_color=C_BORDER).pack(side="left")
        self.preempt_label = ctk.CTkLabel(switch_row, text="OFF — Non-Preemptive",
                                           font=ctk.CTkFont(size=12, weight="bold"),
                                           text_color=C_GREEN)
        self.preempt_label.pack(side="left", padx=8)
        self.preempt_var.trace_add("write", self.on_preempt_toggled)

        # ----- Run button ----------------------------------------------------
        self.run_btn = ctk.CTkButton(parent, text="▶  Run Simulation",
                                      command=self.run_simulation,
                                      height=44,
                                      font=ctk.CTkFont(size=15, weight="bold"),
                                      fg_color=C_BLUE, hover_color=C_PURPLE,
                                      corner_radius=10)
        self.run_btn.pack(fill="x", pady=(0, 6))

        # ----- Clear buttons (two separate buttons) --------------------------
        clear_row = ctk.CTkFrame(parent, fg_color="transparent")
        clear_row.pack(fill="x", pady=(0, 4))

        ctk.CTkButton(clear_row,
                      text="Clear Results",
                      command=self.clear_results,
                      height=34,
                      font=ctk.CTkFont(size=12),
                      fg_color=C_PANEL2, hover_color=C_BORDER,
                      border_color=C_BORDER, border_width=1,
                      text_color=C_DIM, corner_radius=8
                      ).pack(side="left", fill="x", expand=True, padx=(0, 4))

        ctk.CTkButton(clear_row,
                      text="Clear All",
                      command=self.clear_all,
                      height=34,
                      font=ctk.CTkFont(size=12),
                      fg_color=C_PANEL2, hover_color=C_RED,
                      border_color=C_RED, border_width=1,
                      text_color=C_RED, corner_radius=8
                      ).pack(side="left", fill="x", expand=True, padx=(4, 0))

        # Trigger initial layout
        self.on_algo_changed(self.algo_var.get())

    # =========================================================================
    # RIGHT SIDE — results
    # =========================================================================

    def build_right_side(self, parent):
        # Placeholder shown before any simulation runs
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

        # Results frame — hidden until simulation runs
        self.results_frame = ctk.CTkFrame(parent, fg_color="transparent")

        ctk.CTkLabel(self.results_frame, text="Gantt Chart",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=C_TEXT, anchor="center"
                     ).pack(fill="x", pady=(0, 4))

        gantt_scroll = ctk.CTkScrollableFrame(
            self.results_frame, fg_color=C_PANEL,
            orientation="horizontal", height=136, corner_radius=10,
            scrollbar_button_color=C_BORDER,
            scrollbar_button_hover_color=C_BLUE)
        gantt_scroll.pack(fill="x", pady=(0, 12))

        self.gantt = GanttChart(gantt_scroll, height=122)
        self.gantt.pack(fill="both", expand=True)

        ctk.CTkLabel(self.results_frame, text="Results Table",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=C_TEXT, anchor="center"
                     ).pack(fill="x", pady=(0, 4))

        self.table = ResultsTable(self.results_frame)
        self.table.pack(fill="x", pady=(0, 12))

        desc_card = ctk.CTkFrame(self.results_frame, fg_color=C_PANEL,
                                  corner_radius=10)
        desc_card.pack(fill="x")
        self.result_desc = ctk.CTkLabel(desc_card, text="",
                                         font=ctk.CTkFont(size=11),
                                         text_color=C_DIM,
                                         wraplength=560, justify="left")
        self.result_desc.pack(anchor="w", padx=12, pady=10)

    # =========================================================================
    # HELPER — create a titled dark panel card
    # =========================================================================

    def make_panel(self, parent, title):
        panel = ctk.CTkFrame(parent, fg_color=C_PANEL, corner_radius=12)
        panel.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(panel, text=title,
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=C_DIM, anchor="center"
                     ).pack(fill="x", padx=12, pady=(10, 4))
        return panel

    # =========================================================================
    # CALLBACKS
    # =========================================================================

    def on_algo_changed(self, _value):
        # Find which algorithm was just selected
        label = self.algo_var.get().strip()
        new_index = next(
            (i for i, a in enumerate(ALGO_LIST) if a["name"] == label), 0)

        # If the user is CHANGING (not initialising), ask if they want to reset
        if new_index != self.algo_index or not self.process_rows:
            if self.process_rows:   # skip the popup on first load
                answer = messagebox.askyesnocancel(
                    "Switch Algorithm",
                    "You switched to a different algorithm.\n\n"
                    "Yes   → Reset process inputs and clear results\n"
                    "No    → Keep current inputs and results\n"
                    "Cancel → Go back to the previous algorithm"
                )
                if answer is None:
                    # Cancel — revert the dropdown to the old algorithm
                    self.algo_var.set(f"  {ALGO_LIST[self.algo_index]['name']}")
                    return
                if answer:
                    # Yes — reset everything
                    self.clear_results()
                    # Rows will be rebuilt below which effectively resets them

        self.algo_index = new_index
        algo = ALGO_LIST[self.algo_index]

        # Update type badge and description
        self.desc_label.configure(text=algo["description"])
        is_pre = "Preemptive" in algo["type"] and "Non" not in algo["type"]
        self.type_label.configure(
            text=f"⬡  {algo['type']}",
            text_color=C_RED if is_pre else C_GREEN)

        # Show or hide option panels — they sit ABOVE the Run button
        # (pack order: proc_panel was packed first, so these pack after it)
        self.show_hide(self.quantum_panel,  algo["show_quantum"])
        self.show_hide(self.primode_panel,  algo["show_priority"])
        self.show_hide(self.preempt_panel,  algo["show_preempt"])

        # Reset preempt switch whenever algo changes
        self.preempt_var.set(False)
        self.on_preempt_toggled()

        # Rebuild process table (shows/hides Priority column)
        self.rebuild_process_rows(algo["show_priority"])

    def show_hide(self, panel, should_show):
        # Re-pack BEFORE the run button so option panels always appear
        # between Process Details and the Run button.
        if should_show:
            panel.pack(fill="x", pady=(0, 8), before=self.run_btn)
        else:
            panel.pack_forget()

    def on_primode_changed(self, value):
        self.priority_mode = "lower" if value.startswith("Lower") else "higher"

    def on_preempt_toggled(self, *_):
        # Update the label text and color to clearly show the current state
        if self.preempt_var.get():
            self.preempt_label.configure(
                text="ON  — Preemptive  (high-priority arrival interrupts)",
                text_color=C_RED)
        else:
            self.preempt_label.configure(
                text="OFF — Non-Preemptive  (running process finishes first)",
                text_color=C_GREEN)

    def decrease_count(self):
        if self.process_count > 3:
            self.process_count -= 1
            self.count_display.configure(text=str(self.process_count))
            self.count_entry.delete(0, "end")
            self.rebuild_process_rows(ALGO_LIST[self.algo_index]["show_priority"])

    def increase_count(self):
        self.process_count += 1
        self.count_display.configure(text=str(self.process_count))
        self.count_entry.delete(0, "end")
        self.rebuild_process_rows(ALGO_LIST[self.algo_index]["show_priority"])

    def apply_typed_count(self):
        # Read the manually typed count, validate it, and apply
        text = self.count_entry.get().strip()
        if not text:
            return
        if not text.isdigit():
            messagebox.showerror("Invalid Count",
                                 "Number of processes must be a whole number.")
            self.count_entry.delete(0, "end")
            return
        n = int(text)
        if n < 3:
            messagebox.showerror("Too Few",
                                 "Minimum number of processes is 3.")
            self.count_entry.delete(0, "end")
            return
        self.process_count = n
        self.count_display.configure(text=str(n))
        self.count_entry.delete(0, "end")
        self.rebuild_process_rows(ALGO_LIST[self.algo_index]["show_priority"])

    def rebuild_process_rows(self, show_priority):
        # Rebuild column header labels
        for w in self.col_header.winfo_children():
            w.destroy()
        cols = [("", 28), ("PID", 62), ("Arrival", 72), ("Burst", 72)]
        if show_priority:
            cols.append(("Priority", 72))
        for text, width in cols:
            ctk.CTkLabel(self.col_header, text=text, width=width,
                         font=ctk.CTkFont(size=11, weight="bold"),
                         text_color=C_BLUE, anchor="center"
                         ).pack(side="left", padx=4, pady=4)

        # Rebuild input rows
        for w in self.rows_frame.winfo_children():
            w.destroy()
        self.process_rows.clear()

        for i in range(self.process_count):
            color = COLORS[i % len(COLORS)]
            row   = ProcessRow(self.rows_frame, i, show_priority, color)
            row.pack(fill="x", pady=3)
            self.process_rows.append(row)

    # =========================================================================
    # CLEAR ACTIONS
    # =========================================================================

    def clear_results(self):
        # Hide results, return to placeholder
        self.results_frame.pack_forget()
        self.placeholder.pack(fill="both", expand=True)

    def clear_all(self):
        # Reset all process inputs (keep PIDs) AND clear results
        for row in self.process_rows:
            row.clear_inputs()
        self.clear_results()

    # =========================================================================
    # RUN SIMULATION
    # =========================================================================

    def run_simulation(self):
        algo = ALGO_LIST[self.algo_index]

        # Read Time Quantum if needed
        quantum = 2
        if algo["show_quantum"]:
            q = self.quantum_box.get().strip()
            if not q.isdigit() or int(q) < 1:
                messagebox.showerror("Bad Input",
                    "Time Quantum must be a positive number (e.g. 2).")
                return
            quantum = int(q)

        # Read all process rows
        processes = []
        used_pids = set()
        try:
            for row in self.process_rows:
                pid, arrival, burst, priority = row.read()
                if pid in used_pids:
                    raise ValueError(
                        f"'{pid}' appears more than once — all process names must be unique.")
                used_pids.add(pid)
                processes.append(Process(pid, arrival, burst, priority))
        except ValueError as err:
            messagebox.showerror("Input Error", str(err))
            return

        mode       = self.priority_mode
        preemptive = self.preempt_var.get()

        try:
            key = algo["key"]
            if   key == "FCFS":
                result, tl = run_fcfs(processes)
            elif key == "SJF":
                result, tl = run_sjf(processes)
            elif key == "SRT":
                result, tl = run_srt(processes)
            elif key == "RR":
                result, tl = run_rr(processes, quantum)
            elif key == "Priority":
                if preemptive:
                    result, tl = run_priority_p(processes, mode)
                else:
                    result, tl = run_priority_np(processes, mode)
            elif key == "Priority+RR":
                result, tl = run_priority_rr(processes, mode, quantum)
            else:
                raise RuntimeError(f"Unknown algorithm: {key}")
        except Exception as err:
            messagebox.showerror("Simulation Error", str(err))
            return

        self.show_results(result, tl, algo)

    def show_results(self, processes, timeline, algo):
        self.placeholder.pack_forget()
        self.results_frame.pack(fill="both", expand=True)
        self.gantt.draw(timeline, processes)
        self.table.show(processes, algo["show_priority"])
        mode_text = ""
        if algo["key"] == "Priority":
            mode_text = (" (Preemptive — running process can be interrupted)"
                         if self.preempt_var.get()
                         else " (Non-Preemptive — running process always finishes)")
        self.result_desc.configure(
            text=f"{algo['name']}{mode_text}\n{algo['type']} — {algo['description']}")


# =============================================================================
# START THE APP
# =============================================================================

if __name__ == "__main__":
    app = App()
    app.mainloop()