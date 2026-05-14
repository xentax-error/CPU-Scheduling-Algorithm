# ✦ CPU Scheduling Algorithm Simulator

> A desktop application that simulates six fundamental CPU scheduling algorithms, built with Python and CustomTkinter.
>
> **Allen Ferdinald Torres** · BSCS 3B · Operating Systems Case Study · Tarlac State University

---

## 📋 Table of Contents

- [About the Program](#about-the-program)
- [Algorithms Implemented](#algorithms-implemented)
- [Requirements](#requirements)
- [How to Run](#how-to-run)
  - [Option A — Run the Executable (Windows)](#option-a--run-the-executable-windows)
  - [Option B — Run with Python](#option-b--run-with-python)
- [How to Use the Program](#how-to-use-the-program)
- [Input Fields Reference](#input-fields-reference)
- [Repository Contents](#repository-contents)

---

## About the Program

This program simulates how an operating system decides which process gets CPU time and in what order. It accepts user-defined process data, runs the selected scheduling algorithm, and produces:

- A **Gantt chart** showing the execution timeline of all processes
- A **results table** with Completion Time, Waiting Time, and Turnaround Time per process
- **Average Waiting Time** and **Average Turnaround Time** across all processes

---

## Algorithms Implemented

| # | Algorithm | Type |
|---|-----------|------|
| 1 | First-Come, First-Served (FCFS) | Non-Preemptive |
| 2 | Shortest Job First (SJF) | Non-Preemptive |
| 3 | Shortest Remaining Time (SRT) | Preemptive |
| 4 | Round Robin (RR) | Preemptive |
| 5 | Priority Scheduling | Non-Preemptive **and** Preemptive |
| 6 | Priority Scheduling + Round Robin | Non-Preemptive **and** Preemptive |

---

## Requirements

### To run the executable (Option A)
- Windows 10 or later (64-bit)
- No Python installation needed

### To run with Python (Option B)
- Python **3.10 or higher** — [Download here](https://www.python.org/downloads/)
- `customtkinter` library

Install the required library with:

```bash
pip install customtkinter
```

---

## How to Run

### Option A — Run the Executable (Windows)

1. Go to the [Releases](https://github.com/xentax-error/CPU-Scheduling-Algorithm/releases) section of this repository
2. Download `CPU_Scheduling_Simulator.exe`
3. Double-click the `.exe` file to launch the program
4. If Windows Defender shows a warning, click **More info → Run anyway**
   *(This happens because the file is not signed — it is safe)*

---

### Option B — Run with Python

**Step 1 — Make sure Python is installed**

Open a terminal (Command Prompt, PowerShell, or Terminal) and type:

```bash
python --version
```

You should see something like `Python 3.11.x`. If not, [download Python here](https://www.python.org/downloads/) and check **"Add Python to PATH"** during installation.

---

**Step 2 — Install the required library**

```bash
pip install customtkinter
```

---

**Step 3 — Download the source code**

Clone the repository:

```bash
git clone https://github.com/xentax-error/CPU-Scheduling-Algorithm.git
```

Or click the green **Code** button on this page → **Download ZIP**, then extract it.

---

**Step 4 — Run the program**

Navigate into the project folder:

```bash
cd CPU-Scheduling-Algorithm
```

Then run:

```bash
python "OS_CASESTUDY_TORRES_ALLEN FERDINALD_BSCS3B.py"
```

The program window will open.

---

## How to Use the Program

### 1. Select an Algorithm

Use the **Algorithm** dropdown at the top-left to choose which scheduling algorithm to simulate. The interface will automatically show or hide the relevant input fields (e.g., Time Quantum only appears for Round Robin-based algorithms).

---

### 2. Set the Number of Processes

Use the **−** and **+** buttons to adjust the process count, or type a number directly into the box between the buttons. Minimum is **3 processes**. There is no upper limit.

> Changing the process count while keeping the same algorithm **retains** your existing input values for the processes that remain.

---

### 3. Fill in Process Details

For each process, fill in the fields in the **Process Details** panel:

| Field | Description |
|-------|-------------|
| **PID** | Process name (e.g. P0, P1). Pre-filled — rename freely. |
| **Arrival** | Time when the process becomes available. Defaults to `0` if left blank. |
| **Burst** | How many time units the process needs on the CPU. **Required.** |
| **Priority** | Only shown for Priority-based algorithms. Defaults to `0` if left blank. |

> **Tip:** Click into the Arrival or Priority field and it clears automatically so you can type. If you leave it blank, `0` is used.

---

### 4. Configure Additional Options (when visible)

**Time Quantum** *(shown for Round Robin and Priority+RR)*
- Enter how many time units each process gets per turn before being cycled out.
- Default is `2`.

**Priority Mode** *(shown for Priority-based algorithms)*
- Choose whether a **lower number** or a **higher number** means higher priority.

**Preemption Mode** *(shown for Priority Scheduling and Priority+RR)*
- **OFF (Non-Preemptive):** A running process always finishes before another can take over.
- **ON (Preemptive):** A higher-priority arrival immediately interrupts the current process.

---

### 5. Run the Simulation

Click **▶ Run Simulation**. The right side of the window will display:

- **Gantt Chart** — a color-coded timeline of process execution. Scroll horizontally if the schedule is long.
- **Results Table** — Completion Time, Waiting Time, and Turnaround Time per process, plus the averages at the bottom.

---

### 6. Clear and Reset

| Button | What it does |
|--------|-------------|
| **Clear Results** | Hides the output. Your input values are kept. |
| **Clear All** | Resets Arrival, Burst, and Priority fields to defaults. PID names are kept. |

> **Switching algorithms** will prompt you to reset or keep your inputs. Choosing **Yes** resets everything including the process count and Time Quantum. Choosing **No** keeps your current inputs.

---

## Input Fields Reference

| Field | Valid Input | Default if blank |
|-------|------------|-----------------|
| PID | Any text | P0, P1, P2… |
| Arrival Time | Whole number ≥ 0 | 0 |
| Burst Time | Whole number ≥ 1 | *(required, no default)* |
| Priority | Any whole number | 0 |
| Time Quantum | Whole number ≥ 1 | 2 |

All fields validate your input and show an error dialog if something is wrong (letters, symbols, negative numbers, etc.).

---

## Repository Contents

```
CPU-Scheduling-Algorithm/
│
├── OS_CASESTUDY_TORRES_ALLEN FERDINALD_BSCS3B.py   ← Main source code
├── CPU_Scheduling_Simulator.exe                     ← Windows executable
└── README.md                                        ← This file
```

---

> Built for the Operating Systems Case Study · BSCS 3B · Tarlac State University · 2026
