from __future__ import annotations

import argparse
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Iterable, Optional, Sequence

from .ai import SimpleAI
from .cards import Card
from .deck import DeckEmptyError
from .game import MAX_PLAYERS, MIN_PLAYERS, Game, GameResult, InvalidAction, build_player_names
from .rules import describe_waits, format_win_types


HUMAN_INDEX = 0

CARD_COLORS = {
    "Red": ("#ffd7dc", "#7a1724"),
    "Orange": ("#ffe0ad", "#744000"),
    "Green": ("#ccefd1", "#175823"),
    "Blue": ("#d6e6ff", "#173d74"),
    "Voice": ("#eadcff", "#4d2b7a"),
}


class RoseliaMahjongApp:
    def __init__(self, root: tk.Tk, player_count: int = 4, seed: Optional[int] = None) -> None:
        self.root = root
        self.root.title("Roselia Mahjong")
        self.root.geometry("980x720")
        self.root.minsize(820, 620)

        self.player_count = player_count
        self.seed = seed
        self.game: Game
        self.ai: SimpleAI
        self.stage = "setup"
        self.result_announced = False
        self.pending_ron_candidates: list[int] = []
        self.pending_discarder_index: Optional[int] = None
        self.pending_discarded_card: Optional[Card] = None

        self.deck_var = tk.StringVar()
        self.turn_var = tk.StringVar()
        self.status_var = tk.StringVar()

        self._build_ui()
        self.new_game()

    def _build_ui(self) -> None:
        self.root.configure(bg="#f6f2f7")

        top = ttk.Frame(self.root, padding=(12, 10, 12, 6))
        top.pack(fill=tk.X)

        ttk.Label(top, text="Roselia Mahjong", font=("Segoe UI", 18, "bold")).pack(side=tk.LEFT)
        ttk.Label(top, textvariable=self.turn_var, font=("Segoe UI", 11)).pack(side=tk.LEFT, padx=18)
        ttk.Label(top, textvariable=self.deck_var, font=("Segoe UI", 11)).pack(side=tk.LEFT)

        action_bar = ttk.Frame(self.root, padding=(12, 0, 12, 8))
        action_bar.pack(fill=tk.X)

        self.riichi_button = ttk.Button(action_bar, text="立直", command=self.on_riichi)
        self.riichi_button.pack(side=tk.LEFT, padx=(0, 8))

        self.skip_button = ttk.Button(action_bar, text="跳过", command=self.on_skip)
        self.skip_button.pack(side=tk.LEFT, padx=(0, 8))

        self.hu_button = ttk.Button(action_bar, text="胡牌", command=self.on_hu)
        self.hu_button.pack(side=tk.LEFT, padx=(0, 8))

        ttk.Button(action_bar, text="新游戏", command=self.new_game).pack(side=tk.RIGHT)

        ttk.Label(
            self.root,
            textvariable=self.status_var,
            font=("Segoe UI", 11),
            padding=(12, 0, 12, 8),
        ).pack(fill=tk.X)

        self.players_frame = ttk.LabelFrame(self.root, text="玩家状态", padding=10)
        self.players_frame.pack(fill=tk.X, padx=12, pady=(0, 8))

        self.rivers_frame = ttk.LabelFrame(self.root, text="牌河", padding=10)
        self.rivers_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 8))

        self.hand_frame = ttk.LabelFrame(self.root, text="你的手牌（双击出牌）", padding=10)
        self.hand_frame.pack(fill=tk.X, padx=12, pady=(0, 8))

        self.log_text = tk.Text(self.root, height=7, wrap=tk.WORD, state=tk.DISABLED)
        self.log_text.pack(fill=tk.X, padx=12, pady=(0, 12))

    def new_game(self) -> None:
        names = build_player_names(self.player_count, human_name="You", ai_only=False)
        self.game = Game(names, human_index=HUMAN_INDEX, seed=self.seed)
        self.game.setup()
        self.ai = SimpleAI(self.game.rng)
        self.stage = "setup"
        self.result_announced = False
        self.pending_ron_candidates = []
        self.pending_discarder_index = None
        self.pending_discarded_card = None
        self._clear_log()
        self._log("新游戏开始。双击手牌可以弃牌。")
        self.refresh()
        self.root.after(250, self.begin_turn)

    def begin_turn(self) -> None:
        if self.game.is_over:
            self.show_result()
            return

        player = self.game.current_player
        self.refresh()

        if not player.is_human:
            self.stage = "ai_turn"
            self._set_buttons()
            self.status_var.set(f"{player.name} 的回合。")
            self.root.after(450, self.run_ai_turn)
            return

        self.draw_for_human()

    def draw_for_human(self) -> None:
        try:
            drawn_card = self.game.draw_for_current_player()
        except DeckEmptyError:
            self.refresh()
            self.show_result()
            return

        self._log(f"你摸到：{drawn_card.label()}")
        self.refresh()

        if self.game.can_tsumo(HUMAN_INDEX):
            self.stage = "human_tsumo_choice"
            self._set_buttons(skip=True, hu=True)
            self.status_var.set("你可以自摸胡牌。点击“胡牌”，或点击“跳过”后弃牌。")
            return

        if not self.game.players[HUMAN_INDEX].riichi:
            options = self.game.riichi_options(HUMAN_INDEX)
            if options:
                self.stage = "human_after_draw_choice"
                self._set_buttons(riichi=True, skip=True)
                self.status_var.set(
                    "摸牌后可以立直。点击“立直”后双击宣言牌，"
                    "或点击“跳过”/直接双击手牌普通弃牌。"
                )
                return

        self.stage = "human_discard"
        self._set_buttons()
        if self.game.players[HUMAN_INDEX].riichi:
            self.status_var.set("你已立直，手牌结构锁定。请双击刚摸到的牌弃牌。")
        else:
            self.status_var.set("请双击一张手牌弃牌。")

    def run_ai_turn(self) -> None:
        if self.game.is_over:
            self.show_result()
            return

        player_index = self.game.current_player_index
        player = self.game.current_player

        try:
            drawn_card = self.game.draw_for_current_player()
        except DeckEmptyError:
            self.refresh()
            self.show_result()
            return

        self._log(f"{player.name} 摸牌。")
        if self.game.can_tsumo(player_index):
            self.game.finish_tsumo(player_index)
            self.refresh()
            self.show_result()
            return

        if not player.riichi:
            options = self.game.riichi_options(player_index)
            if options:
                discard_index = self.ai.choose_riichi_discard_index(options)
                discarded_card, waits = self.game.declare_riichi_and_discard(
                    player_index,
                    discard_index,
                )
                self._log(
                    f"{player.name} 立直，打出：{discarded_card.label()}。"
                    f"等待：{describe_waits(waits)}"
                )
                self.refresh()
                self.root.after(350, lambda: self.handle_after_discard(player_index, discarded_card))
                return

        discard_index = self.ai.choose_discard_index(player)
        discarded_card = self.game.discard_current_player(discard_index)
        self._log(f"{player.name} 弃牌：{discarded_card.label()}")
        self.refresh()
        self.root.after(350, lambda: self.handle_after_discard(player_index, discarded_card))

    def on_riichi(self) -> None:
        if self.stage != "human_after_draw_choice":
            return

        self.stage = "human_riichi_discard"
        self._set_buttons()
        self.status_var.set("已宣言立直。请双击一张可使剩余手牌听牌的牌作为立直宣言牌。")

    def on_skip(self) -> None:
        if self.stage == "human_after_draw_choice":
            self._log("你跳过立直。")
            self.stage = "human_discard"
            self._set_buttons()
            self._set_buttons()
            self.status_var.set("请双击一张手牌弃牌。")
            return

        if self.stage == "human_tsumo_choice":
            self._log("你跳过自摸。")
            self.stage = "human_discard"
            self._set_buttons()
            self.status_var.set("你已立直，手牌结构锁定。请双击刚摸到的牌弃牌。")
            return

        if self.stage == "human_ron_choice":
            self._log("你跳过荣和。")
            self.process_next_ron_candidate()

    def on_hu(self) -> None:
        if self.stage == "human_tsumo_choice":
            try:
                self.game.finish_tsumo(HUMAN_INDEX)
            except InvalidAction as exc:
                self.status_var.set(str(exc))
                return
            self.refresh()
            self.show_result()
            return

        if self.stage == "human_ron_choice":
            if self.pending_discarder_index is None or self.pending_discarded_card is None:
                return
            try:
                self.game.finish_ron(
                    HUMAN_INDEX,
                    self.pending_discarder_index,
                    self.pending_discarded_card,
                )
            except InvalidAction as exc:
                self.status_var.set(str(exc))
                return
            self.refresh()
            self.show_result()

    def on_card_double_click(self, card_index: int) -> None:
        if self.stage == "human_after_draw_choice":
            self._log("你跳过立直。")
            self.stage = "human_discard"

        if self.stage == "human_riichi_discard":
            try:
                discarded_card, waits = self.game.declare_riichi_and_discard(
                    HUMAN_INDEX,
                    card_index,
                )
            except InvalidAction as exc:
                self.status_var.set(str(exc))
                return

            self._log(f"你立直，打出：{discarded_card.label()}。等待：{describe_waits(waits)}")
            self.refresh()
            self.handle_after_discard(HUMAN_INDEX, discarded_card)
            return

        if self.stage != "human_discard":
            self.status_var.set("现在不能弃牌。")
            return

        try:
            discarded_card = self.game.discard_current_player(card_index)
        except InvalidAction as exc:
            self.status_var.set(str(exc))
            return

        self._log(f"你弃牌：{discarded_card.label()}")
        self.refresh()
        self.handle_after_discard(HUMAN_INDEX, discarded_card)

    def handle_after_discard(self, discarder_index: int, discarded_card: Card) -> None:
        if self.game.is_over:
            self.show_result()
            return

        self.pending_ron_candidates = self.game.ron_candidates(discarder_index, discarded_card)
        self.pending_discarder_index = discarder_index
        self.pending_discarded_card = discarded_card
        self.process_next_ron_candidate()

    def process_next_ron_candidate(self) -> None:
        while self.pending_ron_candidates:
            candidate_index = self.pending_ron_candidates.pop(0)
            player = self.game.players[candidate_index]

            if player.is_human:
                self.stage = "human_ron_choice"
                self._set_buttons(skip=True, hu=True)
                card = self.pending_discarded_card
                label = card.label() if card is not None else "这张牌"
                self.status_var.set(f"你可以对 {label} 荣和。点击“胡牌”或“跳过”。")
                self.refresh()
                return

            if self.pending_discarder_index is None or self.pending_discarded_card is None:
                return
            self.game.finish_ron(
                candidate_index,
                self.pending_discarder_index,
                self.pending_discarded_card,
            )
            self._log(f"{player.name} 荣和。")
            self.refresh()
            self.show_result()
            return

        self.pending_discarder_index = None
        self.pending_discarded_card = None
        self.game.advance_turn()
        self.refresh()
        self.root.after(350, self.begin_turn)

    def show_result(self) -> None:
        self.stage = "game_over"
        self._set_buttons()
        self.refresh()

        if self.result_announced or self.game.result is None:
            return
        self.result_announced = True

        summary = self._result_summary(self.game.result)
        self._log(summary)
        self.status_var.set(summary)
        messagebox.showinfo("游戏结束", summary)

    def refresh(self) -> None:
        self.deck_var.set(f"牌堆剩余：{self.game.deck.remaining()}")
        current = self.game.current_player
        self.turn_var.set(f"当前回合：{current.name}")
        self._render_players()
        self._render_rivers()
        self._render_hand()

    def _render_players(self) -> None:
        self._clear_frame(self.players_frame)
        for index, player in enumerate(self.game.players):
            text = f"{player.name} | 手牌 {len(player.hand)} | 牌河 {len(player.discards)}"
            if index == self.game.dealer_index:
                text += " | 庄家"
            if player.riichi:
                text += " | 立直"
            if index == self.game.current_player_index and not self.game.is_over:
                text += " | 当前"
            ttk.Label(self.players_frame, text=text, padding=(4, 2)).grid(
                row=0,
                column=index,
                sticky=tk.W,
                padx=(0, 16),
            )

    def _render_rivers(self) -> None:
        self._clear_frame(self.rivers_frame)
        for row, player in enumerate(self.game.players):
            ttk.Label(self.rivers_frame, text=f"{player.name}：", width=10).grid(
                row=row,
                column=0,
                sticky=tk.NW,
                pady=4,
            )
            river = ttk.Frame(self.rivers_frame)
            river.grid(row=row, column=1, sticky=tk.W, pady=4)
            if not player.discards:
                ttk.Label(river, text="暂无弃牌").pack(side=tk.LEFT)
                continue
            for card in player.discards:
                self._make_card_label(river, card, small=True).pack(side=tk.LEFT, padx=2, pady=2)

    def _render_hand(self) -> None:
        self._clear_frame(self.hand_frame)
        player = self.game.players[HUMAN_INDEX]
        for index, card in enumerate(player.hand):
            card_button = self._make_card_button(self.hand_frame, card)
            card_button.bind("<Double-Button-1>", lambda _event, i=index: self.on_card_double_click(i))
            card_button.pack(side=tk.LEFT, padx=5, pady=5)

    def _make_card_button(self, parent: tk.Widget, card: Card) -> tk.Button:
        background, foreground = self._card_palette(card)
        return tk.Button(
            parent,
            text=self._card_text(card),
            width=13,
            height=4,
            bg=background,
            fg=foreground,
            activebackground=background,
            relief=tk.RAISED,
            borderwidth=2,
            font=("Segoe UI", 10, "bold"),
        )

    def _make_card_label(self, parent: tk.Widget, card: Card, small: bool = False) -> tk.Label:
        background, foreground = self._card_palette(card)
        return tk.Label(
            parent,
            text=self._card_text(card, short=small),
            width=9 if small else 13,
            height=2 if small else 4,
            bg=background,
            fg=foreground,
            relief=tk.GROOVE,
            borderwidth=1,
            font=("Segoe UI", 8 if small else 10, "bold"),
        )

    def _card_palette(self, card: Card) -> tuple[str, str]:
        if card.is_voice_actor:
            return CARD_COLORS["Voice"]
        return CARD_COLORS.get(card.color or "Blue", CARD_COLORS["Blue"])

    def _card_text(self, card: Card, short: bool = False) -> str:
        if card.is_voice_actor:
            if short:
                return f"VA\n{card.character}"
            return f"{card.voice_actor}\n{card.character}\nAny Color"
        if short:
            return f"{card.character}\n{card.color}"
        return f"{card.character}\n{card.color}"

    def _set_buttons(self, riichi: bool = False, skip: bool = False, hu: bool = False) -> None:
        self.riichi_button.configure(state=tk.NORMAL if riichi else tk.DISABLED)
        self.skip_button.configure(state=tk.NORMAL if skip else tk.DISABLED)
        self.hu_button.configure(state=tk.NORMAL if hu else tk.DISABLED)

    def _result_summary(self, result: GameResult) -> str:
        if result.method == "Draw":
            return f"流局：{result.reason}"

        winner = self.game.players[result.winner_index] if result.winner_index is not None else None
        parts = [f"{result.method}：{winner.name if winner else 'Unknown'} 胜利"]
        if result.discarder_index is not None:
            parts.append(f"放铳：{self.game.players[result.discarder_index].name}")
        if result.winning_card is not None:
            parts.append(f"和牌：{result.winning_card.label()}")
        if result.win_types:
            parts.append(f"牌型：{format_win_types(result.win_types)}")
        return "；".join(parts)

    def _log(self, message: str) -> None:
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def _clear_log(self) -> None:
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def _clear_frame(self, frame: tk.Widget) -> None:
        for child in frame.winfo_children():
            child.destroy()


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Roselia Mahjong GUI prototype")
    parser.add_argument(
        "--players",
        type=int,
        default=4,
        choices=range(MIN_PLAYERS, MAX_PLAYERS + 1),
    )
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--smoke-test", action="store_true", help="Create and close the GUI.")
    args = parser.parse_args(argv)

    root = tk.Tk()
    RoseliaMahjongApp(root, player_count=args.players, seed=args.seed)
    if args.smoke_test:
        root.update_idletasks()
        root.destroy()
        return 0
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
