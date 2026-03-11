"""
WS Damage Simulator — Finisher registry
========================================
Each finisher is a plain function:  fn(e: WSEngine) -> int

Register a new finisher with the @finisher("name") decorator.
The function receives the engine instance and returns total damage dealt.

Adding a new card
-----------------
1. Define a function using e.burn(), e.swing(), e.icytail(), etc.
2. Decorate it with @finisher("your_card_name").
3. Use the name in config.py → FINISHING_SEQUENCE to simulate it.

Available primitives on WSEngine (e):
    e.swing(soul)          Basic attack + trigger
    e.burn(value)          Burn X (cancelable)
    e.icytail(value)       Bottom-X scan, grouped burn
    e.ping_icytail(value)  Bottom-X scan, independent burns
    e.shuffleback(value)   Add X DMGs into deck and reshuffle
    e.moca(value)          Remove CX from top X cards
    e.insert_top(card)     Put a card on top of opponent deck ("CX"/"DMG")
    e.damage_canceled      bool — True if the last effect was canceled
"""
from __future__ import annotations

from typing import Callable
from .engine import WSEngine


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_REGISTRY: dict[str, Callable[[WSEngine], int]] = {}


def finisher(name: str):
    """Decorator: register a function as a named finisher."""
    def decorator(fn: Callable[[WSEngine], int]):
        _REGISTRY[name] = fn
        return fn
    return decorator


def get_finisher(name: str) -> Callable[[WSEngine], int]:
    if name not in _REGISTRY:
        raise KeyError(f"Unknown finisher: '{name}'. Available: {list_finishers()}")
    return _REGISTRY[name]


def list_finishers() -> list[str]:
    return sorted(_REGISTRY.keys())


# ---------------------------------------------------------------------------
# Chainsaw Man
# ---------------------------------------------------------------------------

@finisher("csm_choice")
def csm_choice(e: WSEngine) -> int:
    """Burn 1, Swing 3, Burn 2 — then put a DMG on top of opponent deck."""
    dmg = e.burn(1) + e.swing(3) + e.burn(2)
    e.insert_top("DMG")
    return dmg


@finisher("csm_topdecker")
def csm_topdecker(e: WSEngine) -> int:
    """Put 2 DMGs on top, then Swing 4."""
    e.insert_top("DMG")
    e.insert_top("DMG")
    return e.swing(4)


@finisher("csm_aki")
def csm_aki(e: WSEngine) -> int:
    """Ping-icytail 4, Swing 3."""
    return e.ping_icytail(4) + e.swing(3)


# ---------------------------------------------------------------------------
# Sword Art Online
# ---------------------------------------------------------------------------

@finisher("sinon_icytail")
def sinon_icytail(e: WSEngine) -> int:
    """Icytail 7, Swing 3."""
    return e.icytail(7) + e.swing(3)


# ---------------------------------------------------------------------------
# Shakugan no Shana
# ---------------------------------------------------------------------------

@finisher("shana")
def shana(e: WSEngine) -> int:
    """Burn 4; if canceled, shuffleback 4. Then Swing 3."""
    e.damage_canceled = False
    dmg = e.burn(4)
    if e.damage_canceled:
        dmg += e.shuffleback(4)
    return dmg + e.swing(3)


# ---------------------------------------------------------------------------
# 86 / Kaguya-sama / Fate
# ---------------------------------------------------------------------------

@finisher("dark_sakura")
def dark_sakura(e: WSEngine) -> int:
    """Icytail 6, Swing 3."""
    return e.icytail(6) + e.swing(3)


@finisher("kaguya")
def kaguya(e: WSEngine) -> int:
    """Burn 1, Swing 3, Burn 1."""
    return e.burn(1) + e.swing(3) + e.burn(1)


# ---------------------------------------------------------------------------
# Hololive
# ---------------------------------------------------------------------------

@finisher("fubuki")
def fubuki(e: WSEngine) -> int:
    """Burn 2, shuffleback 2, Swing 3."""
    return e.burn(2) + e.shuffleback(2) + e.swing(3)


@finisher("marine")
def marine(e: WSEngine) -> int:
    """Burn 2, Swing 3."""
    return e.burn(2) + e.swing(3)


@finisher("aegis_anna")
def aegis_anna(e: WSEngine) -> int:
    """Ping-icytail 6, Swing 3."""
    return e.ping_icytail(6) + e.swing(3)


# ---------------------------------------------------------------------------
# Love Live Superstar
# ---------------------------------------------------------------------------

@finisher("lsp_ren")
def lsp_ren(e: WSEngine) -> int:
    """Burn 3, Swing 3."""
    return e.burn(3) + e.swing(3)


# ---------------------------------------------------------------------------
# 4th Gen event
# ---------------------------------------------------------------------------

@finisher("fourth_gen_event")
def fourth_gen_event(e: WSEngine) -> int:
    """Burn 4, Burn 4."""
    return e.burn(4) + e.burn(4)


# ---------------------------------------------------------------------------
# Quintessential Quintuplets (movie)
# ---------------------------------------------------------------------------

@finisher("movie_ichika")
def movie_ichika(e: WSEngine) -> int:
    """Swing 3; if canceled, shuffleback 4 + Burn 4."""
    e.damage_canceled = False
    dmg = e.swing(3)
    if e.damage_canceled:
        dmg += e.shuffleback(4) + e.burn(4)
    return dmg


@finisher("set1_ichika")
def set1_ichika(e: WSEngine) -> int:
    """Swing 3; if canceled, Burn 2 + Burn 2."""
    e.damage_canceled = False
    dmg = e.swing(3)
    if e.damage_canceled:
        dmg += e.burn(2) + e.burn(2)
    return dmg


@finisher("movie_itsuki")
def movie_itsuki(e: WSEngine) -> int:
    """Burn 3, moca 2, Swing 3."""
    return e.burn(3) + e.moca(2) + e.swing(3)


# ---------------------------------------------------------------------------
# BanG Dream
# ---------------------------------------------------------------------------

@finisher("bd_moca")
def bd_moca(e: WSEngine) -> int:
    """Moca 2, Swing 3."""
    return e.moca(2) + e.swing(3)


# ---------------------------------------------------------------------------
# Hololive (Laplus)
# ---------------------------------------------------------------------------

@finisher("laplus")
def laplus(e: WSEngine) -> int:
    """Swing 3; if canceled, Burn 1 + Burn 1."""
    e.damage_canceled = False
    dmg = e.swing(3)
    if e.damage_canceled:
        dmg += e.burn(1) + e.burn(1)
    return dmg
