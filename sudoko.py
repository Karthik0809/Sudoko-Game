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
        self.hints_used = 0
        self.max_hints = 3
        self.start_time = None
        self.leaderboard_file = "leaderboard.json"

        self.difficulty_levels = {"Easy": 30, "Medium": 40, "Hard": 50}
        self.level = self.ask_difficulty()
        self.solved_board = self.generate_full_solution()
        self.board = self.create_puzzle(self.solved_board, self.difficulty_levels[self.level])

        self.create_grid()
        self.create_buttons()
        self.start_timer()

    def ask_difficulty(self):
        level = simpledialog.askstring("Select Difficulty", "Choose difficulty: Easy, Medium, or Hard", parent=self.root)
        return level if level in self.difficulty_levels else "Medium"

    def create_grid(self):
        for row in range(self.grid_size):
            for col in range(self.grid_size):
                entry = tk.Entry(self.root, width=3, font=('Arial', 18), justify='center')
                entry.grid(row=row, column=col, padx=2, pady=2)
                value = self.board[row][col]
                if value != 0:
                    entry.insert(0, str(value))
                    entry.config(state='disabled')
                self.cells[(row, col)] = entry

    def create_buttons(self):
        solve_button = tk.Button(self.root, text='Solve', command=self.solve)
        solve_button.grid(row=self.grid_size, column=0, columnspan=3, pady=10)
        
        check_button = tk.Button(self.root, text='Check', command=self.check_solution)
        check_button.grid(row=self.grid_size, column=3, columnspan=3, pady=10)
        
        hint_button = tk.Button(self.root, text='Hint', command=self.give_hint)
        hint_button.grid(row=self.grid_size, column=6, columnspan=1, pady=10)
        
        reset_button = tk.Button(self.root, text='Reset', command=self.reset)
        reset_button.grid(row=self.grid_size, column=7, columnspan=2, pady=10)

        leaderboard_button = tk.Button(self.root, text="Leaderboard", command=self.show_leaderboard)
        leaderboard_button.grid(row=self.grid_size + 1, column=0, columnspan=9, pady=10)

    def start_timer(self):
        self.start_time = time.time()

    def check_solution(self):
        for row in range(self.grid_size):
            for col in range(self.grid_size):
                value = self.cells[(row, col)].get()
                if not value.isdigit() or int(value) != self.solved_board[row][col]:
                    messagebox.showerror("Error", "Incorrect Solution!")
                    return
        elapsed_time = int(time.time() - self.start_time)
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
        leaderboard.append(time_taken)
        leaderboard.sort()
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
        message = "Leaderboard:\n" + "\n".join([f"{i+1}. {time}s" for i, time in enumerate(leaderboard)])
        messagebox.showinfo("Leaderboard", message)

if __name__ == '__main__':
    root = tk.Tk()
    game = SudokuGame(root)
    root.mainloop()
