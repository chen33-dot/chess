"""肉鸽象棋 v1.1. Coordinates: x=0..8, y=0..9, black at top."""
from dataclasses import dataclass
from collections import Counter
import random

RED, BLACK = 'red', 'black'
POOL = tuple('RRHHEEAACC' + 'PPPPP')
NAMES = {RED: dict(zip('KRHEACP', '帅车马相仕炮兵')),
         BLACK: dict(zip('KRHEACP', '将车马象士炮卒'))}
SIDES = {RED: '红方', BLACK: '黑方'}


def other(side):
    return BLACK if side == RED else RED


@dataclass(frozen=True)
class Piece:
    side: str
    kind: str
    face: bool = False

    @property
    def name(self):
        return NAMES[self.side][self.kind] if self.face else '暗'


@dataclass(frozen=True)
class Action:
    kind: str
    src: tuple
    dst: tuple = None


def initial_positions():
    return ([(x, y) for y in (0, 9) for x in range(9) if x != 4]
            + [(x, y) for y in (2, 7) for x in (1, 7)]
            + [(x, y) for y in (3, 6) for x in (0, 2, 4, 6, 8)])


def can_move(board, src, dst):
    p = board.get(src)
    if not p or not p.face or src == dst:
        return False
    x, y = dst
    if not (0 <= x < 9 and 0 <= y < 10):
        return False
    target = board.get(dst)
    if target and (not target.face or target.side == p.side):
        return False
    sx, sy = src
    dx, dy = x - sx, y - sy
    ax, ay = abs(dx), abs(dy)
    if p.kind == 'K':
        return ax + ay == 1 and 3 <= x <= 5 and (7 <= y <= 9 if p.side == RED else 0 <= y <= 2)
    if p.kind == 'A':
        return ax == ay == 1
    if p.kind == 'E':
        return ax == ay == 2 and (sx + dx // 2, sy + dy // 2) not in board
    if p.kind == 'H':
        if (ax, ay) not in ((1, 2), (2, 1)):
            return False
        leg = (sx + dx // 2, sy) if ax == 2 else (sx, sy + dy // 2)
        return leg not in board
    if p.kind == 'P':
        return ax + ay == 1
    if p.kind in ('R', 'C') and (dx == 0 or dy == 0):
        stepx, stepy = (dx > 0) - (dx < 0), (dy > 0) - (dy < 0)
        count = sum((sx + stepx * i, sy + stepy * i) in board for i in range(1, max(ax, ay)))
        return count == (1 if p.kind == 'C' and target else 0)
    return False


def actions(board, side):
    result = []
    for src, p in board.items():
        if not p.face:
            result.append(Action('flip', src))
        elif p.side == side:
            if p.kind != 'K':
                result.append(Action('mutate', src))
            result.extend(Action('move', src, (x, y)) for y in range(10) for x in range(9)
                          if can_move(board, src, (x, y)))
    return result


class Game:
    def __init__(self, rng=None, quiet_rounds=120, max_rounds=300):
        self.rng = rng or random.SystemRandom()
        pool = [Piece(side, kind) for side in (RED, BLACK) for kind in POOL]
        self.rng.shuffle(pool)
        self.board = dict(zip(initial_positions(), pool))
        self.board[(4, 9)] = Piece(RED, 'K', True)
        self.board[(4, 0)] = Piece(BLACK, 'K', True)
        self.turn = RED
        self.ply = self.quiet = 0
        self.quiet_rounds, self.max_rounds = quiet_rounds, max_rounds
        self.result = None
        self.history = []
        self.captured = []
        self.last = None
        self.repetitions = Counter({self.key(): 1})

    def key(self):
        return (self.turn, tuple(sorted((x, y, p.side, p.kind, p.face) for (x, y), p in self.board.items())))

    def public_board(self):
        # AI receives occupancy but never the identities of hidden pieces.
        return {pos: p if p.face else Piece('', '', False) for pos, p in self.board.items()}

    def legal(self, a):
        if self.result:
            return False
        p = self.board.get(a.src)
        if not p:
            return False
        if a.kind == 'flip':
            return not p.face
        if not p.face or p.side != self.turn:
            return False
        if a.kind == 'mutate':
            return p.kind != 'K'
        return a.kind == 'move' and a.dst is not None and can_move(self.board, a.src, a.dst)

    def play(self, a):
        if not self.legal(a):
            raise ValueError('当前动作不合法')
        p = self.board[a.src]
        actor = self.turn
        coord = lambda pos: f'{pos[0]+1}路{10-pos[1]}行'
        taken = None
        if a.kind == 'flip':
            self.board[a.src] = Piece(p.side, p.kind, True)
            detail = f'翻开 {coord(a.src)} → {SIDES[p.side]}{NAMES[p.side][p.kind]}'
        elif a.kind == 'mutate':
            side = other(p.side) if self.rng.random() < .2 else p.side
            new = Piece(side, self.rng.choice(POOL), True)
            self.board[a.src] = new
            detail = f'{coord(a.src)} {p.name}质变 → {SIDES[side]}{new.name}'
            if side != p.side:
                detail += ' · 叛变！'
        else:
            taken = self.board.get(a.dst)
            del self.board[a.src]
            self.board[a.dst] = p
            detail = f'{p.name} {coord(a.src)} → {coord(a.dst)}'
            if taken:
                self.captured.append(taken)
                detail += f' · 吃{taken.name}'
        self.ply += 1
        self.quiet = self.quiet + 1 if a.kind == 'move' and not taken else 0
        self.last = a
        self.history.append(f'{self.ply:03d}  {SIDES[actor]}  {detail}')
        if taken and taken.kind == 'K':
            self.result = f'{SIDES[actor]}获胜 · 吃将'
            return
        self.turn = other(actor)
        if not actions(self.board, self.turn):
            self.result = f'{SIDES[actor]}获胜 · 对方无合法动作'
            return
        key = self.key()
        self.repetitions[key] += 1
        if self.quiet >= 2 * self.quiet_rounds:
            self.result = f'和棋 · 连续{self.quiet_rounds}回合仅移动'
        elif self.ply >= 2 * self.max_rounds:
            self.result = f'和棋 · 达到{self.max_rounds}完整回合'
        elif self.repetitions[key] >= 3:
            self.result = '和棋 · 同一局面第三次出现'


VALUES = dict(K=100000, R=90, H=45, E=25, A=20, C=50, P=18)


def choose_action(board, side, rng=None):
    """One-ply tactical AI with opponent capture lookahead; public data only."""
    rng = rng or random.SystemRandom()
    candidates = actions(board, side)
    scored = []
    for a in candidates:
        if a.kind == 'flip':
            score = 10 + rng.random() * 5
        elif a.kind == 'mutate':
            score = (38 - VALUES[board[a.src].kind]) * .3 - 7 + rng.random() * 3
        else:
            target = board.get(a.dst)
            if target and target.kind == 'K':
                return a
            b = board.copy()
            p = b.pop(a.src)
            b[a.dst] = p
            # Penalize the best immediate enemy capture, particularly our king.
            danger = 0
            for pos, victim in b.items():
                if victim.face and victim.side == side:
                    if any(q.face and q.side != side and can_move(b, src, pos) for src, q in b.items()):
                        danger = max(danger, VALUES[victim.kind])
            enemy_king = next((pos for pos, q in b.items() if q.face and q.side != side and q.kind == 'K'), (4, 0))
            old_dist = sum(abs(a.src[i] - enemy_king[i]) for i in (0, 1))
            new_dist = sum(abs(a.dst[i] - enemy_king[i]) for i in (0, 1))
            score = (VALUES[target.kind] if target else 0) - danger * .85 + (old_dist - new_dist) * 1.5 + rng.random() * 5
        scored.append((score, a))
    return max(scored, key=lambda item: item[0])[1] if scored else None
