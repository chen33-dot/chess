"""Run with python main.py. No third-party runtime dependencies."""
import tkinter as tk
from tkinter import messagebox, scrolledtext
from concurrent.futures import ThreadPoolExecutor
from engine import Game, Action, RED, BLACK, SIDES, can_move, choose_action

BG = '#171e1c'
PANEL = '#222c28'
TEXT = '#eee5d2'
MUTED = '#a9b3a5'
GOLD = '#dfbc75'

RULES = '''每回合三选一：翻开、移动、质变。红方先手，完成一个动作后立即换手。

翻开
点击任意暗棋即可翻开。30 枚非将棋子混合随机放置；翻出谁的棋，就归谁，与翻开者和所在半场无关。暗棋不能移动、质变或被吃，但会阻挡走法，也能作为炮架。

移动
点击己方明棋，再点绿色落点。带红圈的落点表示可以吃子。
帅／将：各自九宫内横竖一格。
士／仕：全盘斜走一格，不受九宫限制。
象／相：全盘斜走两格，可过河，保留塞象眼。
马：走日，保留蹩马腿。
车：横竖任意距离，不可越子。
炮：不吃时同车；吃子恰好隔一枚棋子，暗棋可作炮架。
兵／卒：全盘上下左右一格，可后退，不升变。

质变
选中己方已翻开的非将帅棋子，点击「质变」。80% 保持归属，20% 立即叛变；再随机决定兵种：车、马、象、士、炮各 2/15，兵卒 5/15。即使结果不变也消耗回合。没有库存限制。

胜负
实际吃掉将帅立即获胜。没有将军、应将、飞将规则，允许将帅照面和送将。轮到一方时无任何合法动作则判负；任何暗棋可翻，任何己方非将明棋可质变。

和棋
连续 120 完整回合只有移动（无吃、翻、质变）；或总计 300 完整回合；或同一真实局面且同一方行棋第三次出现。完整回合为双方各行动一次。优先级：吃将 > 无动作 > 和棋。

人机模式
你执红，电脑执黑。电脑只读取公开局面，不知道暗棋身份。AI 为轻量战术策略，并非专业象棋引擎。

键盘
方向键移动棋盘光标，Enter／空格选择或行动，M 质变，Esc 取消选择。鼠标点击与键盘操作等效。'''


class App:
    def __init__(self, root):
        self.root = root
        root.title('弈变 · 肉鸽象棋')
        root.geometry('1180x820')
        root.minsize(980, 720)
        root.configure(bg=BG)
        self.game = Game()
        self.selected = None
        self.cursor = (4, 9)
        self.keyboard = False
        self.busy = False
        self.generation = 0
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.mode = tk.StringVar(value='人机对弈')
        header = tk.Frame(root, bg=BG)
        header.pack(fill='x', padx=28, pady=(20, 12))
        tk.Label(header, text='弈 变', font=('Microsoft YaHei', 28, 'bold'), bg=BG, fg=TEXT).pack(side='left')
        tk.Label(header, text='  /  肉鸽象棋\n  翻开未知，落子成局。', justify='left', font=('Microsoft YaHei', 10), bg=BG, fg=MUTED).pack(side='left', padx=12)
        self.button(header, '玩法说明', self.help).pack(side='right', padx=5)
        self.button(header, '新的一局', self.new_game).pack(side='right', padx=5)
        body = tk.Frame(root, bg=BG)
        body.pack(fill='both', expand=True, padx=28)
        left = tk.Frame(body, bg=PANEL, width=190)
        left.pack(side='left', fill='y', pady=4)
        left.pack_propagate(False)
        self.label(left, '对 弈', 11, GOLD).pack(anchor='w', padx=18, pady=(22, 12))
        for value in ('人机对弈', '本地双人'):
            tk.Radiobutton(left, text=value, value=value, variable=self.mode, command=self.change_mode,
                           bg=PANEL, fg=TEXT, selectcolor=BG, activebackground=PANEL,
                           activeforeground=GOLD, font=('Microsoft YaHei', 11)).pack(anchor='w', padx=14, pady=4)
        self.label(left, '局 势', 11, GOLD).pack(anchor='w', padx=18, pady=(26, 10))
        self.stats = self.label(left, '', 11)
        self.stats.pack(anchor='w', padx=18)
        self.label(left, '本局已吃', 11, GOLD).pack(anchor='w', padx=18, pady=(24, 8))
        self.grave = tk.Label(left, bg=PANEL, fg=MUTED, font=('Microsoft YaHei', 11), wraplength=150, justify='left')
        self.grave.pack(anchor='w', padx=18)
        self.label(left, '规则 v1.1', 10, MUTED).pack(side='bottom', anchor='w', padx=18, pady=20)
        center = tk.Frame(body, bg=BG)
        center.pack(side='left', fill='both', expand=True, padx=18)
        self.turn_label = tk.Label(center, text='', bg=BG, fg=GOLD, font=('Microsoft YaHei', 14, 'bold'))
        self.turn_label.pack(pady=(0, 8))
        self.canvas = tk.Canvas(center, bg='#d7bd8c', highlightthickness=0, takefocus=True)
        self.canvas.pack(fill='both', expand=True)
        self.canvas.bind('<Configure>', lambda e: self.draw())
        self.canvas.bind('<Button-1>', self.click)
        self.canvas.bind('<Key>', self.key)
        self.notice = tk.Label(center, text='点击任意暗棋翻开，开启这场对局。', bg=BG, fg=MUTED,
                               font=('Microsoft YaHei', 10), wraplength=500, height=3)
        self.notice.pack(fill='x')
        right = tk.Frame(body, bg=PANEL, width=250)
        right.pack(side='right', fill='y', pady=4)
        right.pack_propagate(False)
        self.label(right, '落 子 与 质 变', 11, GOLD).pack(anchor='w', padx=18, pady=(22, 12))
        self.selection = self.label(right, '未选择棋子', 16)
        self.selection.pack(anchor='w', padx=18)
        self.desc = tk.Label(right, text='选择自己的明棋查看走法。\n点击暗棋将直接翻开并换手。', bg=PANEL, fg=MUTED,
                             font=('Microsoft YaHei', 10), justify='left', wraplength=212, height=4)
        self.desc.pack(anchor='w', padx=18, pady=8)
        self.mutate_button = self.button(right, '质变  ↗', self.mutate, gold=True)
        self.mutate_button.pack(fill='x', padx=18, pady=6)
        self.label(right, '80% 留阵  /  20% 叛变', 10, GOLD).pack(pady=4)
        self.label(right, '车马象士炮各 2/15 · 兵卒 5/15', 9, MUTED).pack(pady=(0, 16))
        self.label(right, '行 动 记 录', 11, GOLD).pack(anchor='w', padx=18, pady=8)
        self.log = scrolledtext.ScrolledText(right, bg=PANEL, fg=TEXT, relief='flat', borderwidth=0,
                                            font=('Microsoft YaHei', 10), wrap='word', width=20, state='disabled')
        self.log.pack(fill='both', expand=True, padx=16, pady=(0, 18))
        tk.Label(root, text='九路十行 · 一步一变    |    吃将即胜 · 不设将军与飞将', bg=BG, fg=MUTED,
                 font=('Microsoft YaHei', 9)).pack(pady=10)
        root.protocol('WM_DELETE_WINDOW', self.close)
        self.refresh()

    def label(self, parent, text, size=11, color=TEXT):
        return tk.Label(parent, text=text, bg=PANEL, fg=color, font=('Microsoft YaHei', size), justify='left')

    def button(self, parent, text, command, gold=False):
        return tk.Button(parent, text=text, command=command, bg=GOLD if gold else PANEL,
                         fg=BG if gold else TEXT, activebackground='#c9a45d', activeforeground=BG,
                         disabledforeground='#7d8578', font=('Microsoft YaHei', 11), relief='flat',
                         padx=18, pady=9, cursor='hand2')

    def refresh(self):
        g = self.game
        self.turn_label.config(text=g.result or (f'{SIDES[g.turn]}行动' + (' · 电脑思考中' if self.busy else ' · 翻开 / 移动 / 质变')))
        hidden = sum(not p.face for p in g.board.values())
        self.stats.config(text=f'第 {g.ply // 2 + 1} 回合\n\n行动 {g.ply} 次\n\n未翻开 {hidden} 枚\n\n静默 {g.quiet}/240 步')
        self.grave.config(text=' '.join(p.name for p in g.captured) or '尚无棋子离场')
        p = g.board.get(self.selected)
        self.selection.config(text=f'{SIDES[p.side]} · {p.name}' if p else '未选择棋子')
        hints = dict(K='九宫内横竖一格；不可质变。', R='横竖任意距离，路径不可越子。', H='日字移动，保留蹩马腿。',
                     E='全盘田字，保留塞象眼。', A='全盘斜走一格，不受九宫限制。', C='移动同车；吃子必须恰隔一个炮架。', P='上下左右一格，可后退，可横走。')
        self.desc.config(text=hints[p.kind] if p else '选择自己的明棋查看走法。\n点击暗棋将直接翻开并换手。')
        self.mutate_button.config(state='normal' if p and p.kind != 'K' and not self.busy and not g.result else 'disabled')
        self.log.config(state='normal')
        self.log.delete('1.0', 'end')
        self.log.insert('end', '\n\n'.join(g.history[-150:]))
        self.log.see('end')
        self.log.config(state='disabled')
        self.draw()

    def draw(self):
        c = self.canvas
        c.delete('all')
        w, h = c.winfo_width(), c.winfo_height()
        self.step = s = min((w - 80) / 8, (h - 80) / 9)
        if s < 1:
            return
        self.ox, self.oy = ox, oy = (w - s * 8) / 2, (h - s * 9) / 2
        xy = lambda x, y: (ox + x * s, oy + y * s)
        line = '#836b46'
        c.create_rectangle(ox-9, oy-9, ox+8*s+9, oy+9*s+9, outline=line, width=2)
        for y in range(10):
            c.create_line(*xy(0, y), *xy(8, y), fill=line)
        for x in range(9):
            if x in (0, 8):
                c.create_line(*xy(x, 0), *xy(x, 9), fill=line)
            else:
                for a, b in ((0, 4), (5, 9)):
                    c.create_line(*xy(x, a), *xy(x, b), fill=line)
        for y in (0, 7):
            c.create_line(*xy(3, y), *xy(5, y+2), fill=line)
            c.create_line(*xy(5, y), *xy(3, y+2), fill=line)
        for x, text in ((2, '楚 河'), (6, '汉 界')):
            c.create_text(*xy(x, 4.5), text=text, font=('KaiTi', max(14, int(s*.38))), fill=line)
        for x in range(9):
            c.create_text(ox+x*s, oy+9*s+s*.62, text=str(x+1), fill=line, font=('Segoe UI', 9))
        for y in range(10):
            c.create_text(ox-s*.65, oy+y*s, text=str(10-y), fill=line, font=('Segoe UI', 8))
        if self.game.last:
            for pos in (self.game.last.src, self.game.last.dst):
                if pos:
                    x, y = xy(*pos)
                    c.create_rectangle(x-s*.43, y-s*.43, x+s*.43, y+s*.43, outline='#a77b32', width=2)
        for pos, p in self.game.board.items():
            x, y = xy(*pos)
            r = s * .385
            c.create_oval(x-r+1, y-r+3, x+r+1, y+r+3, fill='#a0865e', outline='')
            fill = '#30443c' if not p.face else '#f4e4be'
            ink = '#b33f34' if p.side == RED and p.face else '#293b35'
            c.create_oval(x-r, y-r, x+r, y+r, fill=fill, outline='#23362e' if not p.face else '#b89860', width=2)
            c.create_oval(x-r+4, y-r+4, x+r-4, y+r-4, outline='#879482' if not p.face else ink)
            c.create_text(x, y, text=p.name if p.face else '弈', fill=ink if p.face else '#cbbd93',
                          font=('KaiTi', max(12, int(s*.4)), 'bold'))
            if pos == self.selected:
                c.create_oval(x-r-3, y-r-3, x+r+3, y+r+3, outline='#faf3dc', width=3)
        if self.selected and not self.game.result:
            for y in range(10):
                for x in range(9):
                    if can_move(self.game.board, self.selected, (x, y)):
                        px, py = xy(x, y)
                        r = s * (.43 if (x, y) in self.game.board else .10)
                        c.create_oval(px-r, py-r, px+r, py+r, fill='' if (x, y) in self.game.board else '#547b58',
                                      outline='#b33f34' if (x, y) in self.game.board else '#547b58', width=3)
        if self.keyboard:
            x, y = xy(*self.cursor)
            c.create_rectangle(x-s*.46, y-s*.46, x+s*.46, y+s*.46, outline='#faf3dc', dash=(3, 2), width=2)

    def click(self, event):
        self.canvas.focus_set()
        self.keyboard = False
        if self.step <= 0:
            return
        x = round((event.x - self.ox) / self.step)
        y = round((event.y - self.oy) / self.step)
        if 0 <= x < 9 and 0 <= y < 10:
            self.cursor = (x, y)
            self.select((x, y))

    def key(self, event):
        self.keyboard = True
        x, y = self.cursor
        directions = {'Left': (-1, 0), 'Right': (1, 0), 'Up': (0, -1), 'Down': (0, 1)}
        if event.keysym in directions:
            dx, dy = directions[event.keysym]
            self.cursor = (max(0, min(8, x+dx)), max(0, min(9, y+dy)))
        elif event.keysym in ('Return', 'space'):
            self.select(self.cursor)
        elif event.keysym.lower() == 'm':
            self.mutate()
        elif event.keysym == 'Escape':
            self.selected = None
            self.refresh()
        self.draw()

    def select(self, pos):
        if self.busy or self.game.result:
            return
        p = self.game.board.get(pos)
        if p and not p.face:
            self.perform(Action('flip', pos))
        elif p and p.side == self.game.turn:
            self.selected = None if self.selected == pos else pos
            self.refresh()
        elif self.selected and self.game.legal(Action('move', self.selected, pos)):
            self.perform(Action('move', self.selected, pos))
        else:
            self.notice.config(text='此处不能落子。请选择绿色落点，或翻开一枚暗棋。')

    def mutate(self):
        if not self.busy and self.selected and self.game.legal(Action('mutate', self.selected)):
            self.perform(Action('mutate', self.selected))

    def perform(self, action):
        self.game.play(action)
        self.selected = None
        self.notice.config(text=self.game.result or self.game.history[-1])
        self.refresh()
        self.schedule_ai()

    def schedule_ai(self):
        if self.mode.get() != '人机对弈' or self.game.turn != BLACK or self.game.result or self.busy:
            return
        self.busy = True
        self.refresh()
        token = self.generation
        future = self.executor.submit(choose_action, self.game.public_board(), BLACK)

        def poll():
            if token != self.generation:
                return
            if not future.done():
                self.root.after(70, poll)
                return
            self.busy = False
            try:
                action = future.result()
                if action:
                    self.perform(action)
            except Exception as exc:
                self.notice.config(text=f'电脑行动失败：{exc}；可切换到本地双人继续。')
                self.refresh()
        self.root.after(450, poll)

    def change_mode(self):
        self.generation += 1
        self.busy = False
        self.selected = None
        self.refresh()
        self.schedule_ai()

    def new_game(self):
        if self.game.ply and not self.game.result and not messagebox.askyesno('重新开局', '结束当前对局并随机生成新局？', parent=self.root):
            return
        self.generation += 1
        self.game = Game()
        self.selected = None
        self.busy = False
        self.notice.config(text='新局已就绪。红方先手，点击任意暗棋翻开。')
        self.refresh()

    def help(self):
        dialog = tk.Toplevel(self.root)
        dialog.title('弈变 · 玩法说明')
        dialog.geometry('650x680')
        dialog.configure(bg=BG)
        box = scrolledtext.ScrolledText(dialog, bg=PANEL, fg=TEXT, font=('Microsoft YaHei', 12),
                                        wrap='word', padx=22, pady=20, relief='flat')
        box.pack(fill='both', expand=True, padx=12, pady=12)
        box.insert('1.0', RULES)
        box.configure(state='disabled')

    def close(self):
        self.generation += 1
        self.executor.shutdown(wait=False, cancel_futures=True)
        self.root.destroy()


if __name__ == '__main__':
    root = tk.Tk()
    App(root)
    root.mainloop()
