import tkinter as tk
import unittest
import time
from main import App
from engine import Piece, RED


class UITest(unittest.TestCase):
    def test_window_flip_select_move_and_mutate(self):
        root = tk.Tk()
        app = App(root)
        try:
            app.mode.set('本地双人')
            root.update()
            self.assertGreater(len(app.canvas.find_all()), 100)
            app.select((0, 0))
            self.assertEqual(app.game.ply, 1)
            self.assertTrue(app.game.board[(0, 0)].face)
            app.select((4, 0))
            self.assertEqual(app.selected, (4, 0))
            self.assertEqual(str(app.mutate_button['state']), 'disabled')
            app.select((4, 1))
            self.assertEqual(app.game.ply, 2)
            app.game.board[(4, 5)] = Piece(RED, 'P', True)
            app.select((4, 5))
            self.assertEqual(str(app.mutate_button['state']), 'normal')
            app.mutate()
            self.assertEqual(app.game.ply, 3)
            self.assertIsNone(app.selected)
            root.geometry('980x720')
            root.update()
            self.assertGreater(app.step, 30)
            app.help()
            root.update()
        finally:
            app.close()

    def test_ai_takes_exactly_one_turn(self):
        root = tk.Tk()
        app = App(root)
        try:
            root.update()
            app.select((0, 0))
            self.assertTrue(app.busy)
            app.select((8, 0))
            self.assertEqual(app.game.ply, 1)
            deadline = time.monotonic() + 6
            while app.busy and time.monotonic() < deadline:
                root.update()
                time.sleep(.01)
            self.assertFalse(app.busy)
            self.assertEqual(app.game.ply, 2)
            self.assertEqual(app.game.turn, RED)
        finally:
            app.close()


if __name__ == '__main__':
    unittest.main()
