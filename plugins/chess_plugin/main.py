import random

class SimpleChessGame:
    def __init__(self):
        self.reset()
        
    def reset(self):
        self.board = [
            ["r", "n", "b", "q", "k", "b", "n", "r"],
            ["p", "p", "p", "p", "p", "p", "p", "p"],
            [".", ".", ".", ".", ".", ".", ".", "."],
            [".", ".", ".", ".", ".", ".", ".", "."],
            [".", ".", ".", ".", ".", ".", ".", "."],
            [".", ".", ".", ".", ".", ".", ".", "."],
            ["P", "P", "P", "P", "P", "P", "P", "P"],
            ["R", "N", "B", "Q", "K", "B", "N", "R"]
        ]
        self.turn = "white"  # white = player, black = computer
        self.history = []
        self.game_over = False
        self.winner = None

    def get_board_ascii(self) -> str:
        res = "  a b c d e f g h\n"
        for i, row in enumerate(self.board):
            res += f"{8-i} " + " ".join(row) + f" {8-i}\n"
        res += "  a b c d e f g h\n\n"
        res += f"Lượt đi tiếp theo: {'Người chơi (Trắng)' if self.turn == 'white' else 'Máy (Đen)'}\n"
        if self.history:
            res += f"Lịch sử nước đi: {' '.join(self.history[-10:])}\n"
        if self.game_over:
            res += f"Trò chơi kết thúc! Người thắng: {self.winner or 'Hòa'}\n"
        return res

    def get_moves_for_piece(self, r, c):
        piece = self.board[r][c]
        if piece == ".":
            return []
        is_white = piece.isupper()
        color_sign = -1 if is_white else 1
        moves = []

        p_type = piece.lower()
        if p_type == "p": # Pawn
            nr = r + color_sign
            if 0 <= nr < 8 and self.board[nr][c] == ".":
                moves.append((nr, c))
                if (is_white and r == 6) or (not is_white and r == 1):
                    nnr = r + 2 * color_sign
                    if self.board[nnr][c] == ".":
                        moves.append((nnr, c))
            for dc in [-1, 1]:
                nc = c + dc
                nr = r + color_sign
                if 0 <= nr < 8 and 0 <= nc < 8:
                    target = self.board[nr][nc]
                    if target != "." and target.isupper() != is_white:
                        moves.append((nr, nc))
        elif p_type == "n": # Knight
            offsets = [(-2,-1), (-2,1), (-1,-2), (-1,2), (1,-2), (1,2), (2,-1), (2,1)]
            for dr, dc in offsets:
                nr, nc = r + dr, c + dc
                if 0 <= nr < 8 and 0 <= nc < 8:
                    target = self.board[nr][nc]
                    if target == "." or target.isupper() != is_white:
                        moves.append((nr, nc))
        elif p_type in ["b", "q"]: # Bishop/Queen
            dirs = [(-1,-1), (-1,1), (1,-1), (1,1)]
            for dr, dc in dirs:
                nr, nc = r + dr, c + dc
                while 0 <= nr < 8 and 0 <= nc < 8:
                    target = self.board[nr][nc]
                    if target == ".":
                        moves.append((nr, nc))
                    else:
                        if target.isupper() != is_white:
                            moves.append((nr, nc))
                        break
                    nr += dr
                    nc += dc
        if p_type in ["r", "q"]: # Rook/Queen
            dirs = [(-1,0), (1,0), (0,-1), (0,1)]
            for dr, dc in dirs:
                nr, nc = r + dr, c + dc
                while 0 <= nr < 8 and 0 <= nc < 8:
                    target = self.board[nr][nc]
                    if target == ".":
                        moves.append((nr, nc))
                    else:
                        if target.isupper() != is_white:
                            moves.append((nr, nc))
                        break
                    nr += dr
                    nc += dc
        elif p_type == "k": # King
            dirs = [(-1,-1), (-1,0), (-1,1), (0,-1), (0,1), (1,-1), (1,0), (1,1)]
            for dr, dc in dirs:
                nr, nc = r + dr, c + dc
                if 0 <= nr < 8 and 0 <= nc < 8:
                    target = self.board[nr][nc]
                    if target == "." or target.isupper() != is_white:
                        moves.append((nr, nc))
        return moves

    def move(self, uci_move: str) -> str:
        if self.game_over:
            return "Lỗi: Trò chơi đã kết thúc."
        if len(uci_move) != 4:
            return "Lỗi: Nước đi phải gồm 4 ký tự uci, ví dụ 'e2e4'."
        
        try:
            start_col = ord(uci_move[0].lower()) - ord('a')
            start_row = 8 - int(uci_move[1])
            end_col = ord(uci_move[2].lower()) - ord('a')
            end_row = 8 - int(uci_move[3])
        except Exception:
            return "Lỗi: Định dạng nước đi không hợp lệ."

        if not (0 <= start_col < 8 and 0 <= start_row < 8 and 0 <= end_col < 8 and 0 <= end_row < 8):
            return "Lỗi: Tọa độ ngoài bàn cờ."

        piece = self.board[start_row][start_col]
        if piece == ".":
            return "Lỗi: Không có quân cờ ở vị trí xuất phát."

        is_white_piece = piece.isupper()
        if (self.turn == "white" and not is_white_piece) or (self.turn == "black" and is_white_piece):
            return "Lỗi: Không phải lượt đi của bạn."

        # Verify move is valid
        valid_moves = self.get_moves_for_piece(start_row, start_col)
        if (end_row, end_col) not in valid_moves:
            return f"Lỗi: Nước đi không hợp lệ cho quân {piece}."

        # Make player move
        target_piece = self.board[end_row][end_col]
        if target_piece.lower() == "k":
            self.game_over = True
            self.winner = "Người chơi" if is_white_piece else "Máy"

        self.board[end_row][end_col] = piece
        self.board[start_row][start_col] = "."
        
        self.history.append(uci_move)
        self.turn = "black" if self.turn == "white" else "white"

        return "Thành công"

    def make_computer_move(self) -> str:
        if self.game_over:
            return "Trò chơi đã kết thúc."
        
        all_moves = []
        for r in range(8):
            for c in range(8):
                piece = self.board[r][c]
                if piece != "." and not piece.isupper():
                    moves = self.get_moves_for_piece(r, c)
                    for nr, nc in moves:
                        all_moves.append((r, c, nr, nc))
                        
        if not all_moves:
            self.game_over = True
            self.winner = "Người chơi"
            return "Máy không còn nước đi hợp lệ. Bạn thắng!"

        # Simple heuristic: prefer captures
        captures = []
        for start_row, start_col, end_row, end_col in all_moves:
            target = self.board[end_row][end_col]
            if target != "." and target.isupper():
                captures.append((start_row, start_col, end_row, end_col))

        if captures:
            start_row, start_col, end_row, end_col = random.choice(captures)
        else:
            start_row, start_col, end_row, end_col = random.choice(all_moves)
        
        piece = self.board[start_row][start_col]
        target_piece = self.board[end_row][end_col]
        
        if target_piece.lower() == "k":
            self.game_over = True
            self.winner = "Máy"

        self.board[end_row][end_col] = piece
        self.board[start_row][start_col] = "."
        
        uci_from = f"{chr(ord('a') + start_col)}{8 - start_row}"
        uci_to = f"{chr(ord('a') + end_col)}{8 - end_row}"
        move_str = uci_from + uci_to
        self.history.append(move_str)
        self.turn = "white"
        
        return f"Máy đi: {move_str}"

# Global game instance
_game = SimpleChessGame()

def chess_start_game() -> dict:
    global _game
    _game.reset()
    return {
        "message": "Trò chơi cờ vua mới đã bắt đầu! Bạn đi quân Trắng (ký tự in hoa), máy đi quân Đen (ký tự thường).",
        "board": _game.get_board_ascii()
    }

def chess_get_board() -> dict:
    global _game
    return {
        "board": _game.get_board_ascii()
    }

def chess_make_move(move: str) -> dict:
    global _game
    res = _game.move(move)
    if not res.startswith("Thành công"):
        return {"error": res, "board": _game.get_board_ascii()}
    
    # Run computer move
    comp_msg = ""
    if not _game.game_over:
        comp_msg = _game.make_computer_move()

    return {
        "player_move": move,
        "computer_move": comp_msg,
        "board": _game.get_board_ascii()
    }
