import tkinter as tk
from PIL import Image, ImageTk
import chess
from stockfish import Stockfish
import os

# --- Constants ---
SQUARE_SIZE = 64
BOARD_COLOR_1 = "#F1D9B5"
BOARD_COLOR_2 = "#B58863"
HIGHLIGHT_COLOR = "#90EE90"
LAST_MOVE_COLOR = "#FFD700"
HOVER_COLOR = "#00FFFF"

class ChessAnalyzerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Modern Chess Analyzer")

        self.board = chess.Board()
        self.selected_square = None
        self.last_move = None
        self.legal_moves = []
        self.hovered_square = None
        self.redo_stack = []

        # Stockfish setup
        stockfish_path = os.path.join(os.path.dirname(__file__), "stockfish-windows-x86-64-avx2.exe")
        self.stockfish = Stockfish(stockfish_path)
        self.stockfish.set_skill_level(15)
        self.stockfish.set_fen_position(self.board.fen())

        # GUI layout
        self.canvas = tk.Canvas(root, width=8*SQUARE_SIZE, height=8*SQUARE_SIZE)
        self.canvas.grid(row=0, column=0)
        self.canvas.bind("<Button-1>", self.click_square)
        self.canvas.bind("<Motion>", self.hover_square)

        right_frame = tk.Frame(root)
        right_frame.grid(row=0, column=1, padx=10, sticky="n")

        # Move list
        self.moves_text = tk.Text(right_frame, width=25, height=20, font=("Helvetica", 10))
        self.moves_text.pack(pady=10)

        # Undo / Redo buttons
        undo_btn = tk.Button(right_frame, text="Undo", command=self.undo_move, bg="#4CAF50", fg="white", font=("Helvetica",10,"bold"))
        undo_btn.pack(pady=5, fill="x")
        redo_btn = tk.Button(right_frame, text="Redo", command=self.redo_move, bg="#2196F3", fg="white", font=("Helvetica",10,"bold"))
        redo_btn.pack(pady=5, fill="x")

        # Evaluation bar
        self.eval_bar = tk.Canvas(root, width=20, height=8*SQUARE_SIZE)
        self.eval_bar.grid(row=0, column=2, padx=5)

        # Load piece images
        self.piece_images = {}
        self.load_images()
        self.draw_board()
        self.update_moves_text()

    def load_images(self):
        pieces = ['P','R','N','B','Q','K']
        colors = ['w','b']
        assets_path = os.path.join(os.path.dirname(__file__), "assets", "pieces")
        for color in colors:
            for piece in pieces:
                path = os.path.join(assets_path, f"{color}{piece}.png")
                img = Image.open(path).resize((SQUARE_SIZE, SQUARE_SIZE))
                self.piece_images[color+piece] = ImageTk.PhotoImage(img)

    def draw_board(self):
        self.canvas.delete("all")
        # Draw squares
        for row in range(8):
            for col in range(8):
                color = BOARD_COLOR_1 if (row+col)%2==0 else BOARD_COLOR_2
                x1 = col*SQUARE_SIZE
                y1 = row*SQUARE_SIZE
                x2 = x1 + SQUARE_SIZE
                y2 = y1 + SQUARE_SIZE
                self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="")

        # Highlight legal moves
        for lm_square in self.legal_moves:
            lm_row = 7 - chess.square_rank(lm_square)
            lm_col = chess.square_file(lm_square)
            self.canvas.create_rectangle(lm_col*SQUARE_SIZE, lm_row*SQUARE_SIZE,
                                         (lm_col+1)*SQUARE_SIZE, (lm_row+1)*SQUARE_SIZE,
                                         fill=HIGHLIGHT_COLOR, stipple="gray25")

        # Highlight last move
        if self.last_move:
            from_row = 7 - chess.square_rank(self.last_move.from_square)
            from_col = chess.square_file(self.last_move.from_square)
            to_row = 7 - chess.square_rank(self.last_move.to_square)
            to_col = chess.square_file(self.last_move.to_square)
            self.canvas.create_rectangle(from_col*SQUARE_SIZE, from_row*SQUARE_SIZE,
                                         (from_col+1)*SQUARE_SIZE, (from_row+1)*SQUARE_SIZE,
                                         fill=LAST_MOVE_COLOR, stipple="gray25")
            self.canvas.create_rectangle(to_col*SQUARE_SIZE, to_row*SQUARE_SIZE,
                                         (to_col+1)*SQUARE_SIZE, (to_row+1)*SQUARE_SIZE,
                                         fill=LAST_MOVE_COLOR, stipple="gray25")

        # Hover effect
        if self.hovered_square is not None:
            row = 7 - chess.square_rank(self.hovered_square)
            col = chess.square_file(self.hovered_square)
            self.canvas.create_rectangle(col*SQUARE_SIZE, row*SQUARE_SIZE,
                                         (col+1)*SQUARE_SIZE, (row+1)*SQUARE_SIZE,
                                         outline=HOVER_COLOR, width=2)

        # Draw pieces
        for square in chess.SQUARES:
            piece = self.board.piece_at(square)
            if piece:
                col = chess.square_file(square)
                row = 7 - chess.square_rank(square)
                img_key = 'w'+piece.symbol().upper() if piece.color else 'b'+piece.symbol().upper()
                self.canvas.create_image(col*SQUARE_SIZE, row*SQUARE_SIZE, anchor='nw',
                                         image=self.piece_images[img_key])

    def update_moves_text(self):
        self.moves_text.delete('1.0', tk.END)
        moves = list(self.board.move_stack)
        text = ""
        for i, move in enumerate(moves):
            if i % 2 == 0:
                text += f"{i//2 + 1}. "
            text += f"{move.uci()} "
            if i % 2 == 1:
                text += "\n"
        self.moves_text.insert(tk.END, text)

        # Stockfish evaluation text
        self.stockfish.set_fen_position(self.board.fen())
        eval_info = self.stockfish.get_evaluation()
        if eval_info["type"] == "cp":
            self.moves_text.insert(tk.END, f"\nEvaluation: {eval_info['value']/100:.2f} (centipawns)")
        elif eval_info["type"] == "mate":
            self.moves_text.insert(tk.END, f"\nMate in {eval_info['value']} moves")

        # Update evaluation bar
        self.draw_eval_bar()

    def draw_eval_bar(self):
        self.eval_bar.delete("all")
        self.stockfish.set_fen_position(self.board.fen())
        eval_info = self.stockfish.get_evaluation()
        height = 8*SQUARE_SIZE
        if eval_info["type"] == "cp":
            score = max(min(eval_info['value'], 1000), -1000)
            white_height = int((score + 1000)/2000 * height)
        elif eval_info["type"] == "mate":
            white_height = height if eval_info['value'] > 0 else 0
        else:
            white_height = height//2
        self.eval_bar.create_rectangle(0, 0, 20, height, fill="red")
        self.eval_bar.create_rectangle(0, height-white_height, 20, height, fill="green")

    def click_square(self, event):
        col = event.x // SQUARE_SIZE
        row = event.y // SQUARE_SIZE
        square = chess.square(col, 7-row)
        piece = self.board.piece_at(square)

        # Select piece
        if self.selected_square is None:
            if piece and ((piece.color and self.board.turn) or (not piece.color and not self.board.turn)):
                self.selected_square = square
                self.legal_moves = [move.to_square for move in self.board.legal_moves if move.from_square == square]
        else:
            move = chess.Move(self.selected_square, square)
            if move in self.board.legal_moves:
                self.board.push(move)
                self.last_move = move
                self.redo_stack.clear()
                self.stockfish.set_fen_position(self.board.fen())
                self.update_moves_text()
            self.selected_square = None
            self.legal_moves = []
        self.draw_board()

    def hover_square(self, event):
        col = event.x // SQUARE_SIZE
        row = event.y // SQUARE_SIZE
        square = chess.square(col, 7-row)
        if self.hovered_square != square:
            self.hovered_square = square
            self.draw_board()

    def undo_move(self):
        if self.board.move_stack:
            move = self.board.pop()
            self.last_move = self.board.move_stack[-1] if self.board.move_stack else None
            self.redo_stack.append(move)
            self.legal_moves = []
            self.stockfish.set_fen_position(self.board.fen())
            self.update_moves_text()
            self.draw_board()

    def redo_move(self):
        if self.redo_stack:
            move = self.redo_stack.pop()
            self.board.push(move)
            self.last_move = move
            self.stockfish.set_fen_position(self.board.fen())
            self.update_moves_text()
            self.draw_board()

if __name__ == "__main__":
    root = tk.Tk()
    gui = ChessAnalyzerGUI(root)
    root.mainloop()
