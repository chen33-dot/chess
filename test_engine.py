import random
import unittest
from collections import Counter
from engine import Game, Piece, Action, RED, BLACK, POOL, can_move, actions, choose_action


def piece(kind, side=RED, face=True):
    return Piece(side, kind, face)


def position(board, turn=RED, **kwargs):
    g = Game(random.Random(42), **kwargs)
    g.board = board
    g.turn = turn
    g.repetitions = Counter({g.key(): 1})
    return g


class RulesTest(unittest.TestCase):
    def test_setup(self):
        for seed in range(20):
            g = Game(random.Random(seed))
            self.assertEqual(len(g.board), 32)
            self.assertEqual(sum(not p.face for p in g.board.values()), 30)
            for side in (RED, BLACK):
                self.assertEqual(Counter(p.kind for p in g.board.values() if p.side == side and not p.face), Counter(POOL))
            self.assertEqual(g.board[(4, 9)], piece('K'))
            self.assertEqual(g.board[(4, 0)], piece('K', BLACK))
        self.assertTrue(any(p.side == RED and pos[1] < 5 for pos, p in g.board.items() if not p.face))

    def test_flip_opponent_anywhere_does_not_transfer(self):
        g = Game(random.Random(1))
        pos = next(pos for pos, p in g.board.items() if not p.face and p.side == BLACK)
        g.play(Action('flip', pos))
        self.assertEqual(g.board[pos].side, BLACK)
        self.assertEqual(g.turn, BLACK)
        self.assertFalse(g.legal(Action('flip', pos)))

    def test_hidden_actions_and_target_forbidden(self):
        b = {(4, 4): piece('R'), (4, 2): piece('P', BLACK, False)}
        self.assertFalse(can_move(b, (4, 4), (4, 2)))
        self.assertFalse(can_move(b, (4, 4), (4, 0)))
        g = position(b)
        self.assertFalse(g.legal(Action('mutate', (4, 2))))
        self.assertFalse(g.legal(Action('move', (4, 2), (5, 2))))

    def test_king_palaces_and_no_flying(self):
        b = {(4, 9): piece('K'), (4, 0): piece('K', BLACK)}
        self.assertTrue(can_move(b, (4, 9), (4, 8)))
        self.assertFalse(can_move(b, (4, 9), (4, 0)))
        self.assertFalse(can_move(b, (4, 9), (3, 8)))
        b = {(3, 7): piece('K')}
        self.assertFalse(can_move(b, (3, 7), (2, 7)))
        self.assertFalse(can_move(b, (3, 7), (3, 6)))

    def test_advisor_elephant_and_soldier_variant(self):
        self.assertTrue(can_move({(1, 4): piece('A')}, (1, 4), (2, 3)))
        self.assertTrue(can_move({(2, 5): piece('E')}, (2, 5), (4, 3)))
        for face in (False, True):
            self.assertFalse(can_move({(2, 5): piece('E'), (3, 4): piece('P', BLACK, face)}, (2, 5), (4, 3)))
        for side in (RED, BLACK):
            b = {(4, 4): piece('P', side)}
            for dst in ((4, 3), (4, 5), (3, 4), (5, 4)):
                self.assertTrue(can_move(b, (4, 4), dst))
            self.assertFalse(can_move(b, (4, 4), (5, 5)))

    def test_horse_all_directions_and_legs(self):
        for dx, dy in ((1, 2), (-1, 2), (1, -2), (-1, -2), (2, 1), (2, -1), (-2, 1), (-2, -1)):
            b = {(4, 4): piece('H')}
            dst = (4+dx, 4+dy)
            self.assertTrue(can_move(b, (4, 4), dst))
            leg = (4+dx//2, 4) if abs(dx) == 2 else (4, 4+dy//2)
            b[leg] = piece('P', BLACK, False)
            self.assertFalse(can_move(b, (4, 4), dst))

    def test_cannon_screen(self):
        b = {(4, 6): piece('C'), (4, 0): piece('K', BLACK)}
        self.assertFalse(can_move(b, (4, 6), (4, 0)))
        b[(4, 3)] = piece('P', RED, False)
        self.assertTrue(can_move(b, (4, 6), (4, 0)))
        self.assertFalse(can_move(b, (4, 6), (4, 1)))
        self.assertFalse(can_move(b, (4, 6), (4, 3)))
        self.assertTrue(can_move(b, (4, 6), (4, 4)))
        b[(4, 2)] = piece('P', BLACK)
        self.assertFalse(can_move(b, (4, 6), (4, 0)))

    def test_own_target_and_bounds(self):
        b = {(0, 0): piece('R'), (0, 1): piece('P')}
        for dst in ((0, 0), (-1, 0), (9, 0), (0, 10), (0, 1), (1, 1)):
            self.assertFalse(can_move(b, (0, 0), dst))

    def test_wrong_owner_and_empty_actions(self):
        g = Game()
        for action in (Action('move', (4, 0), (4, 1)), Action('mutate', (4, 0)), Action('flip', (4, 5)), Action('mutate', (4, 9))):
            before = g.key()
            with self.assertRaises(ValueError):
                g.play(action)
            self.assertEqual(g.key(), before)
            self.assertEqual(g.ply, 0)

    def test_mutation_order_weights_and_unchanged(self):
        class Fixed:
            def __init__(self, value, kind):
                self.value, self.kind = value, kind
                self.calls = []
            def random(self):
                self.calls.append('side')
                return self.value
            def choice(self, seq):
                self.calls.append('type')
                assert Counter(seq) == Counter(dict(R=2, H=2, E=2, A=2, C=2, P=5))
                return self.kind
        for value, expected in ((0, BLACK), (.199999, BLACK), (.2, RED), (.99, RED)):
            g = Game()
            g.board[(0, 5)] = piece('P')
            g.rng = Fixed(value, 'P')
            g.play(Action('mutate', (0, 5)))
            self.assertEqual(g.board[(0, 5)], piece('P', expected))
            self.assertEqual(g.rng.calls, ['side', 'type'])
            self.assertEqual(g.ply, 1)
            self.assertEqual(g.turn, BLACK)
            self.assertEqual(g.quiet, 0)

    def test_capture_king_priority_and_lock(self):
        g = position({(4, 1): piece('R'), (4, 0): piece('K', BLACK), (4, 9): piece('K'), (4, 8): piece('R', BLACK)}, max_rounds=1)
        g.ply = 1
        g.play(Action('move', (4, 1), (4, 0)))
        self.assertEqual(g.result, '红方获胜 · 吃将')
        self.assertEqual(g.turn, RED)
        self.assertFalse(g.legal(Action('move', (4, 0), (4, 1))))

    def test_no_action_priority(self):
        # No black pieces, no hidden pieces: black has no action, ahead of draw.
        g = position({(4, 9): piece('K'), (0, 0): piece('P')}, max_rounds=1)
        g.ply = 1
        g.play(Action('move', (0, 0), (0, 1)))
        self.assertEqual(g.result, '红方获胜 · 对方无合法动作')

    def test_mutation_and_hidden_prevent_no_action(self):
        self.assertIn(Action('mutate', (0, 0)), actions({(0, 0): piece('P')}, RED))
        self.assertEqual(actions({(0, 0): piece('P', BLACK, False)}, RED), [Action('flip', (0, 0))])

    def test_threefold_and_hidden_identity_in_key(self):
        g = position({(4, 9): piece('K'), (4, 0): piece('K', BLACK)})
        loop = [((4, 9), (3, 9)), ((4, 0), (3, 0)), ((3, 9), (4, 9)), ((3, 0), (4, 0))]
        for _ in range(2):
            for src, dst in loop:
                g.play(Action('move', src, dst))
        self.assertEqual(g.result, '和棋 · 同一局面第三次出现')
        g = Game()
        before = g.key()
        p = g.board[(0, 0)]
        g.board[(0, 0)] = Piece(p.side, 'P' if p.kind != 'P' else 'R', False)
        self.assertNotEqual(g.key(), before)

    def test_draw_thresholds_and_reset(self):
        for options, reason in ((dict(quiet_rounds=1), '仅移动'), (dict(max_rounds=1), '完整回合')):
            g = position({(4, 9): piece('K'), (4, 0): piece('K', BLACK)}, **options)
            g.play(Action('move', (4, 9), (3, 9)))
            self.assertIsNone(g.result)
            g.play(Action('move', (4, 0), (3, 0)))
            self.assertIn(reason, g.result)
        g = Game()
        g.quiet = 239
        g.play(Action('flip', (0, 0)))
        self.assertEqual(g.quiet, 0)
        self.assertIsNone(g.result)

    def test_public_view_and_ai(self):
        g = Game(random.Random(0))
        public = g.public_board()
        self.assertTrue(all(p.side == p.kind == '' for p in public.values() if not p.face))
        a = choose_action(public, RED, random.Random(2))
        self.assertTrue(g.legal(a))
        g.board = {(4, 9): piece('K'), (4, 0): piece('K', BLACK), (4, 1): piece('R')}
        self.assertEqual(choose_action(g.public_board(), RED), Action('move', (4, 1), (4, 0)))

    def test_random_legal_games_invariants(self):
        rng = random.Random(81)
        for _ in range(5):
            g = Game(rng)
            for _ in range(200):
                if g.result:
                    break
                a = rng.choice(actions(g.board, g.turn))
                count = len(g.board)
                capture = a.kind == 'move' and a.dst in g.board
                g.play(a)
                self.assertEqual(len(g.board), count - int(capture))
                self.assertEqual(len(g.history), g.ply)
                self.assertTrue(all(0 <= x <= 8 and 0 <= y <= 9 for x, y in g.board))


if __name__ == '__main__':
    unittest.main()
