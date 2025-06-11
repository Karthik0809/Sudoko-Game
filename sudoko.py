import tkinter as tk
from tkinter import messagebox, simpledialog
from random import sample, shuffle
import time
import json
import os

class SudokuGame:
    def __init__(self, root):
        self.root = root
        self.root.title("Sudoku")
        self.grid_size = 9
        self.subgrid_size = 3
        self.cells = {}
        self.cell_vars = {}
        self.hints_used = 0
        self.max_hints = 3
        self.start_time = None
        self.paused = False
        self.pause_time = 0
        self.elapsed_paused = 0
        self.selected_cell = None
        self.notes_mode = False
        self.leaderboard_file = "leaderboard.json"
        self.player_name = self.ask_player_name()
        self.undo_stack = []
        self.redo_stack = []

        self.difficulty_levels = {"Easy": 30, "Medium": 40, "Hard": 50}
        self.level = self.ask_difficulty()
        self.solved_board = self.generate_full_solution()
        self.board = self.create_puzzle(self.solved_board, self.difficulty_levels[self.level])

        # --- UI Frames ---
        self.main_frame = tk.Frame(self.root, padx=10, pady=10)
        self.main_frame.pack(expand=True)
        self.grid_frame = tk.Frame(self.main_frame, bg='#f8f8f8', padx=8, pady=8, relief='groove', bd=2)
        self.grid_frame.grid(row=0, column=0, padx=10, pady=10)
        self.controls_frame = tk.Frame(self.main_frame)
        self.controls_frame.grid(row=1, column=0, pady=(0, 10))
        self.status_bar = tk.Label(self.root, text='', bd=1, relief='sunken', anchor='w', font=('Arial', 12))
        self.status_bar.pack(side='bottom', fill='x')

        self.create_grid()
        self.create_buttons()
        self.start_timer()
        self.update_status_bar()
        self.center_window()

    def center_window(self):
        self.root.update_idletasks()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (w // 2)
        y = (self.root.winfo_screenheight() // 2) - (h // 2)
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def update_status_bar(self):
        elapsed = int(time.time() - self.start_time - self.elapsed_paused) if self.start_time else 0
        hints_left = self.max_hints - self.hints_used
        notes = 'ON' if self.notes_mode else 'OFF'
        self.status_bar.config(text=f"Time: {elapsed}s    Hints left: {hints_left}    Notes: {notes}")
        if not self.paused:
            self.root.after(1000, self.update_status_bar)

    def ask_player_name(self):
        name = simpledialog.askstring("Player Name", "Enter your name:", parent=self.root)
        return name if name else "Player"

    def ask_difficulty(self):
        # Use a dialog with radio buttons instead of text input
        dialog = tk.Toplevel(self.root)
        dialog.title("Select Difficulty")
        dialog.grab_set()
        tk.Label(dialog, text="Choose difficulty:").pack(padx=10, pady=10)
        var = tk.StringVar(value="Medium")
        for level in self.difficulty_levels:
            tk.Radiobutton(dialog, text=level, variable=var, value=level).pack(anchor='w', padx=20)
        selected = []
        def on_ok():
            selected.append(var.get())
            dialog.destroy()
        tk.Button(dialog, text="OK", command=on_ok).pack(pady=10)
        dialog.wait_window()
        return selected[0] if selected else "Medium"

    def create_grid(self):
        for row in range(self.grid_size):
            for col in range(self.grid_size):
                var = tk.StringVar()
                # Determine border thickness for 3x3 subgrid lines
                top = 3 if row % 3 == 0 else 1
                left = 3 if col % 3 == 0 else 1
                right = 3 if col == 8 else 1
                bottom = 3 if row == 8 else 1
                # Create a Frame for each cell with per-side border
                cell_frame = tk.Frame(self.grid_frame, bg='#f8f8f8')
                cell_frame.grid(row=row, column=col, sticky='nsew')
                cell_frame.grid_propagate(False)
                # Set the frame size
                cell_frame.config(width=40, height=40)
                # Add borders using another frame for each side
                border_frame = tk.Frame(cell_frame, bg='#000')
                border_frame.place(x=0, y=0, relwidth=1, relheight=1)
                # Top border
                if top > 1:
                    tk.Frame(cell_frame, bg='#000', height=top).pack(side='top', fill='x')
                # Left border
                if left > 1:
                    tk.Frame(cell_frame, bg='#000', width=left).pack(side='left', fill='y')
                # Right border
                if right > 1:
                    tk.Frame(cell_frame, bg='#000', width=right).pack(side='right', fill='y')
                # Bottom border
                if bottom > 1:
                    tk.Frame(cell_frame, bg='#000', height=bottom).pack(side='bottom', fill='x')
                # Place the Entry inside the Frame
                entry = tk.Entry(cell_frame, width=3, font=('Arial', 18), justify='center', textvariable=var,
                                 highlightthickness=0, bd=0, relief='flat')
                entry.pack(expand=True, fill='both', padx=2, pady=2)
                value = self.board[row][col]
                if value != 0:
                    entry.insert(0, str(value))
                    entry.config(state='disabled', disabledbackground='#e0e0e0', disabledforeground='black')
                else:
                    entry.bind('<Button-1>', lambda e, r=row, c=col: self.select_cell(r, c))
                    entry.bind('<FocusIn>', lambda e, r=row, c=col: self.select_cell(r, c))
                    var.trace_add('write', lambda *args, r=row, c=col: self.track_move(r, c))
                self.cells[(row, col)] = entry
                self.cell_vars[(row, col)] = var

    def highlight_related(self, row, col):
        # Highlight row, col, and box
        for r in range(self.grid_size):
            for c in range(self.grid_size):
                entry = self.cells[(r, c)]
                if entry['state'] == 'normal':
                    entry.config(bg='white')
        for i in range(self.grid_size):
            if self.cells[(row, i)]['state'] == 'normal':
                self.cells[(row, i)].config(bg='#e3f2fd')
            if self.cells[(i, col)]['state'] == 'normal':
                self.cells[(i, col)].config(bg='#e3f2fd')
        box_x, box_y = (row // 3) * 3, (col // 3) * 3
        for r in range(box_x, box_x + 3):
            for c in range(box_y, box_y + 3):
                if self.cells[(r, c)]['state'] == 'normal':
                    self.cells[(r, c)].config(bg='#bbdefb')
        # Highlight selected cell
        entry = self.cells[(row, col)]
        if entry['state'] == 'normal':
            entry.config(bg='#90caf9')

    def select_cell(self, row, col):
        self.selected_cell = (row, col)
        self.highlight_related(row, col)

    def create_buttons(self):
        # Helper for tooltips
        def add_tooltip(widget, text):
            tooltip = tk.Toplevel(widget)
            tooltip.withdraw()
            tooltip.overrideredirect(True)
            label = tk.Label(tooltip, text=text, background='#ffffe0', relief='solid', borderwidth=1, font=('Arial', 10))
            label.pack()
            def enter(event):
                x = widget.winfo_rootx() + 20
                y = widget.winfo_rooty() + 20
                tooltip.geometry(f"+{x}+{y}")
                tooltip.deiconify()
            def leave(event):
                tooltip.withdraw()
            widget.bind('<Enter>', enter)
            widget.bind('<Leave>', leave)

        # Button style
        btn_opts = {'font': ('Arial', 14), 'width': 10, 'padx': 4, 'pady': 4, 'bg': '#1976d2', 'fg': 'white', 'activebackground': '#1565c0', 'activeforeground': 'white', 'relief': 'raised', 'bd': 2}
        # Row 0
        solve_button = tk.Button(self.controls_frame, text='Solve', command=self.solve, **btn_opts)
        solve_button.grid(row=0, column=0, padx=5, pady=5)
        add_tooltip(solve_button, 'Show the solution')
        check_button = tk.Button(self.controls_frame, text='Check', command=self.check_solution, **btn_opts)
        check_button.grid(row=0, column=1, padx=5, pady=5)
        add_tooltip(check_button, 'Check your solution')
        hint_button = tk.Button(self.controls_frame, text='Hint', command=self.give_hint, **btn_opts)
        hint_button.grid(row=0, column=2, padx=5, pady=5)
        add_tooltip(hint_button, 'Get a hint (max 3)')
        reset_button = tk.Button(self.controls_frame, text='Reset', command=self.reset, **btn_opts)
        reset_button.grid(row=0, column=3, padx=5, pady=5)
        add_tooltip(reset_button, 'Clear all your entries')
        newgame_button = tk.Button(self.controls_frame, text='New Game', command=self.new_game, **btn_opts)
        newgame_button.grid(row=0, column=4, padx=5, pady=5)
        add_tooltip(newgame_button, 'Start a new puzzle')
        notes_button = tk.Button(self.controls_frame, text='Notes', command=self.toggle_notes_mode, **btn_opts)
        notes_button.grid(row=0, column=5, padx=5, pady=5)
        add_tooltip(notes_button, 'Toggle notes mode')
        pause_button = tk.Button(self.controls_frame, text='Pause/Resume', command=self.toggle_pause, **btn_opts)
        pause_button.grid(row=0, column=6, padx=5, pady=5)
        add_tooltip(pause_button, 'Pause or resume the timer')
        leaderboard_button = tk.Button(self.controls_frame, text="Leaderboard", command=self.show_leaderboard, **btn_opts)
        leaderboard_button.grid(row=1, column=0, columnspan=3, padx=5, pady=5)
        add_tooltip(leaderboard_button, 'Show the leaderboard')
        undo_button = tk.Button(self.controls_frame, text='Undo', command=self.undo, **btn_opts)
        undo_button.grid(row=1, column=3, columnspan=2, padx=5, pady=5)
        add_tooltip(undo_button, 'Undo your last move')
        redo_button = tk.Button(self.controls_frame, text='Redo', command=self.redo, **btn_opts)
        redo_button.grid(row=1, column=5, columnspan=2, padx=5, pady=5)
        add_tooltip(redo_button, 'Redo your last undone move')

    def new_game(self):
        self.level = self.ask_difficulty()
        self.solved_board = self.generate_full_solution()
        self.board = self.create_puzzle(self.solved_board, self.difficulty_levels[self.level])
        self.hints_used = 0
        self.elapsed_paused = 0
        self.start_timer()
        for row in range(self.grid_size):
            for col in range(self.grid_size):
                entry = self.cells[(row, col)]
                entry.config(state='normal', bg='white')
                entry.delete(0, tk.END)
                value = self.board[row][col]
                if value != 0:
                    entry.insert(0, str(value))
                    entry.config(state='disabled', disabledbackground='#e0e0e0', disabledforeground='black')

    def toggle_notes_mode(self):
        self.notes_mode = not self.notes_mode
        msg = "Notes mode ON: Enter possible candidates." if self.notes_mode else "Notes mode OFF."
        messagebox.showinfo("Notes Mode", msg)

    def toggle_pause(self):
        if not self.paused:
            self.paused = True
            self.pause_time = time.time()
        else:
            self.paused = False
            self.elapsed_paused += time.time() - self.pause_time
            self.start_time += time.time() - self.pause_time

    def start_timer(self):
        self.start_time = time.time()
        self.paused = False
        self.elapsed_paused = 0

    def check_solution(self):
        for row in range(self.grid_size):
            for col in range(self.grid_size):
                value = self.cells[(row, col)].get()
                if not value.isdigit() or int(value) != self.solved_board[row][col]:
                    self.cells[(row, col)].config(bg='#ffcccc')
                    messagebox.showerror("Error", "Incorrect Solution!")
                    return
        elapsed_time = int(time.time() - self.start_time - self.elapsed_paused)
        messagebox.showinfo("Success", f"Correct Solution! Time taken: {elapsed_time} seconds")
        self.update_leaderboard(elapsed_time)

    def reset(self):
        for row in range(self.grid_size):
            for col in range(self.grid_size):
                if self.cells[(row, col)]['state'] == 'normal':
                    self.cells[(row, col)].delete(0, tk.END)
        self.start_timer()

    def solve(self):
        for row in range(self.grid_size):
            for col in range(self.grid_size):
                if self.cells[(row, col)]['state'] == 'normal':
                    self.cells[(row, col)].delete(0, tk.END)
                    self.cells[(row, col)].insert(0, str(self.solved_board[row][col]))

    def give_hint(self):
        if self.hints_used < self.max_hints:
            for row in range(self.grid_size):
                for col in range(self.grid_size):
                    if self.cells[(row, col)]['state'] == 'normal' and self.cells[(row, col)].get() == "":
                        self.cells[(row, col)].insert(0, str(self.solved_board[row][col]))  
                        self.hints_used += 1
                        return
        messagebox.showinfo("Hint", "No more hints available!")

    def generate_full_solution(self):
        def fill_grid(board):
            for i in range(81):
                row, col = divmod(i, 9)
                if board[row][col] == 0:
                    shuffle(numbers)
                    for num in numbers:
                        if self.is_valid(board, row, col, num):
                            board[row][col] = num
                            if not any(0 in row for row in board) or fill_grid(board):
                                return True
                            board[row][col] = 0
                    return False
            return True

        board = [[0] * 9 for _ in range(9)]
        numbers = list(range(1, 10))
        fill_grid(board)
        return board

    def create_puzzle(self, full_board, num_holes):
        puzzle = [row[:] for row in full_board]
        positions = [(r, c) for r in range(9) for c in range(9)]
        shuffle(positions)

        for _ in range(num_holes):
            row, col = positions.pop()
            temp = puzzle[row][col]
            puzzle[row][col] = 0
            test_board = [row[:] for row in puzzle]
            solutions = self.count_solutions(test_board)
            if solutions != 1:
                puzzle[row][col] = temp

        return puzzle

    def count_solutions(self, board):
        def solve(count=0):
            for i in range(81):
                row, col = divmod(i, 9)
                if board[row][col] == 0:
                    for num in range(1, 10):
                        if self.is_valid(board, row, col, num):
                            board[row][col] = num
                            count = solve(count)
                            board[row][col] = 0
                    return count
            return count + 1

        return solve()

    def is_valid(self, board, row, col, num):
        if num in board[row]:
            return False
        if num in [board[r][col] for r in range(9)]:
            return False
        box_x, box_y = (row // 3) * 3, (col // 3) * 3
        if num in [board[r][c] for r in range(box_x, box_x + 3) for c in range(box_y, box_y + 3)]:
            return False
        return True

    def update_leaderboard(self, time_taken):
        leaderboard = self.load_leaderboard()
        leaderboard.append({"name": self.player_name, "time": time_taken})
        leaderboard.sort(key=lambda x: x["time"])
        leaderboard = leaderboard[:5]  # Keep top 5 times
        with open(self.leaderboard_file, "w") as file:
            json.dump(leaderboard, file)

    def load_leaderboard(self):
        if os.path.exists(self.leaderboard_file):
            with open(self.leaderboard_file, "r") as file:
                return json.load(file)
        return []

    def show_leaderboard(self):
        leaderboard = self.load_leaderboard()
        message = "Leaderboard:\n" + "\n".join([f"{i+1}. {entry['name']} - {entry['time']}s" for i, entry in enumerate(leaderboard)])
        messagebox.showinfo("Leaderboard", message)

    def track_move(self, row, col):
        entry = self.cells[(row, col)]
        if entry['state'] == 'normal':
            value = entry.get()
            # Only track if the value actually changed
            if not self.undo_stack or self.undo_stack[-1][:3] != (row, col, value):
                prev_value = self.undo_stack[-1][2] if self.undo_stack and self.undo_stack[-1][:2] == (row, col) else ''
                self.undo_stack.append((row, col, value, prev_value))
                self.redo_stack.clear()

    def undo(self):
        if not self.undo_stack:
            return
        row, col, value, prev_value = self.undo_stack.pop()
        entry = self.cells[(row, col)]
        if entry['state'] == 'normal':
            self.redo_stack.append((row, col, entry.get(), value))
            entry.delete(0, tk.END)
            entry.insert(0, prev_value)

    def redo(self):
        if not self.redo_stack:
            return
        row, col, value, prev_value = self.redo_stack.pop()
        entry = self.cells[(row, col)]
        if entry['state'] == 'normal':
            self.undo_stack.append((row, col, entry.get(), value))
            entry.delete(0, tk.END)
            entry.insert(0, value)

if __name__ == '__main__':
    root = tk.Tk()
    game = SudokuGame(root)
    root.mainloop()
