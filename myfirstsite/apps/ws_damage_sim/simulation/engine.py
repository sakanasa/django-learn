"""
WS Damage Simulator — Core engine
Handles deck state and all primitive Weiss Schwarz effects.
"""
from __future__ import annotations

import random


class WSEngine:
    """
    Holds game state for one simulation iteration and exposes all
    primitive WS damage effects as methods.

    Deck representation
    -------------------
    opp_deck  : list of "CX" | "L0" | "L0S" | "L1" | "L1S" | "L2" | "L2S"
                        | "L3" | "L3S" | "EV" | "EVS"   (index 0 = top)
    own_deck  : list of int  (0 = no trigger, 1 = soul, 2 = double-soul)

    Cards with 'S' suffix have a soul icon.
    All non-CX cards are treated as non-climax for cancel logic.
    """

    def __init__(
        self,
        opp_first_deck_size: int,
        opp_first_climaxes: int,
        opp_second_deck_size: int,
        opp_second_climaxes: int,
        own_total_cards: int = 25,
        own_soul_triggers: int = 8,
        own_2soul_triggers: int = 0,
    ):
        self.opp_first_deck_size = opp_first_deck_size
        self.opp_first_climaxes = opp_first_climaxes
        self.opp_second_deck_size = opp_second_deck_size
        self.opp_second_climaxes = opp_second_climaxes

        own_trigger_cards = own_soul_triggers + own_2soul_triggers
        self._own_deck_template: list[int] = (
            [1] * own_soul_triggers
            + [2] * own_2soul_triggers
            + [0] * (own_total_cards - own_trigger_cards)
        )

        self.opp_deck: list[str] = []
        self.own_deck: list[int] = []
        self.damage_canceled: bool = False

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Shuffle fresh decks for a new iteration."""
        opp_dmg = self.opp_first_deck_size - self.opp_first_climaxes
        self.opp_deck = ["CX"] * self.opp_first_climaxes + ["DMG"] * opp_dmg

        random.shuffle(self.opp_deck)

        self.own_deck = self._own_deck_template[:]
        random.shuffle(self.own_deck)

        self.damage_canceled = False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _refresh(self) -> int:
        """
        Opponent refreshes: second deck is shuffled in, top card burned.
        Returns 1 (refresh damage penalty).
        """
        opp2_dmg = self.opp_second_deck_size - self.opp_second_climaxes
        self.opp_deck += ["CX"] * self.opp_second_climaxes + ["DMG"] * opp2_dmg
        random.shuffle(self.opp_deck)
        self.opp_deck.pop(0)  # clock from refresh
        return 1

    def _ensure_deck(self) -> int:
        """Refresh if deck is empty. Returns penalty damage."""
        if not self.opp_deck:
            return self._refresh()
        return 0

    # ------------------------------------------------------------------
    # Primitive effects
    # ------------------------------------------------------------------

    def swing(self, soul: int) -> int:
        """
        Basic attack: reveal own trigger (adds 0/1/2 soul),
        then deal soul damage to opponent.
        Damage stops if a CX is flipped (cancel); sets damage_canceled.
        """
        damage = 0
        penalty = 0

        soul += self.own_deck.pop(0)  # trigger check

        for _ in range(soul):
            penalty += self._ensure_deck()
            if self.opp_deck[0] != "CX":
                damage += 1
                self.opp_deck.pop(0)
            else:
                damage = 0
                self.opp_deck.pop(0)
                self.damage_canceled = True
                break

        penalty += self._ensure_deck()
        return damage + penalty

    def burn(self, value: int) -> int:
        """
        Burn X: deal up to X damage that can be canceled by a CX.
        Resets to 0 and stops if canceled; sets damage_canceled.
        """
        damage = 0
        penalty = 0

        for _ in range(value):
            penalty += self._ensure_deck()
            if self.opp_deck[0] != "CX":
                damage += 1
                self.opp_deck.pop(0)
            else:
                self.opp_deck.pop(0)
                damage = 0
                self.damage_canceled = True
                break

        penalty += self._ensure_deck()
        return damage + penalty

    def icytail(self, value: int) -> int:
        """
        Look at bottom X cards of opponent deck.
        For each CX found, deal 1 damage (cancelable as a group).
        """
        penalty = 0
        cx_hits = 0

        for _ in range(value):
            penalty += self._ensure_deck()
            if self.opp_deck[-1] == "CX":
                cx_hits += 1
            self.opp_deck.pop(-1)

        icy_damage = 0
        for _ in range(cx_hits):
            penalty += self._ensure_deck()
            if self.opp_deck[0] != "CX":
                self.opp_deck.pop(0)
                icy_damage += 1
            else:
                self.opp_deck.pop(0)
                icy_damage = 0
                break

        penalty += self._ensure_deck()
        return icy_damage + penalty

    def ping_icytail(self, value: int, dmg_per_cx: int = 1) -> int:
        """
        Look at bottom X cards of opponent deck.
        Deal dmg_per_cx damage per CX found (each burn independent, no group cancel).
        """
        penalty = 0
        cx_hits = 0

        for _ in range(value):
            penalty += self._ensure_deck()
            if self.opp_deck[-1] == "CX":
                cx_hits += 1
            self.opp_deck.pop(-1)

        icy_damage = 0
        for _ in range(cx_hits):
            remaining = dmg_per_cx
            while remaining > 0:
                penalty += self._ensure_deck()
                if self.opp_deck[0] != "CX":
                    self.opp_deck.pop(0)
                    icy_damage += 1
                    remaining -= 1
                else:
                    self.opp_deck.pop(0)
                    break  # canceled, stop this burn

        penalty += self._ensure_deck()
        return icy_damage + penalty

    def shuffleback(self, value: int) -> int:
        """
        Add X non-CX cards into opponent deck and reshuffle.
        Used as a "guaranteed damage" setup after a cancel.
        """
        penalty = self._ensure_deck()
        self.opp_deck += ["DMG"] * value
        random.shuffle(self.opp_deck)
        return penalty

    def moca(self, value: int) -> int:
        """
        Look at top X cards of opponent deck; remove any CX found.
        """
        penalty = self._ensure_deck()
        value = min(value, len(self.opp_deck))

        i = value - 1
        while i >= 0:
            if self.opp_deck[i] == "CX":
                self.opp_deck.pop(i)
            i -= 1

        penalty += self._ensure_deck()
        return penalty

    def reveal_top_lv0_burn(self, burn_val: int) -> int:
        """
        Reveal top card; if it is Lv0 or Event, deal burn_val cancelable damage.
        """
        penalty = self._ensure_deck()
        if not self.opp_deck:
            return penalty
        card = self.opp_deck.pop(0)
        is_lv0_or_ev = card.startswith('L0') or card.startswith('EV')
        if is_lv0_or_ev:
            return penalty + self.burn(burn_val)
        return penalty

    def direct_soul_check(self, count: int) -> int:
        """
        Reveal top `count` cards; for each card with a soul icon ('S' suffix),
        deal 1 uncancelable damage. Does not use normal cancel mechanic.
        """
        penalty = 0
        direct_dmg = 0
        for _ in range(count):
            penalty += self._ensure_deck()
            if not self.opp_deck:
                break
            card = self.opp_deck.pop(0)
            if 'S' in card:
                direct_dmg += 1
        penalty += self._ensure_deck()
        return direct_dmg + penalty

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def insert_top(self, card: str = "DMG") -> None:
        """Insert a card at the top of the opponent deck."""
        self.opp_deck.insert(0, card)

    def opponent_draw(self) -> int:
        """
        Opponent draws 1 card at the start of their turn.
        Returns 1 if the deck becomes empty (refresh trigger).
        """
        if not self.opp_deck:
            return 0
        self.opp_deck.pop(0)
        return 1 if not self.opp_deck else 0
