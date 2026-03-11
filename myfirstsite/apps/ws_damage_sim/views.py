from __future__ import annotations

import json
import timeit
import uuid

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from .simulation.engine import WSEngine
from .simulation import finishers as _fin_module  # noqa: F401 — triggers all @finisher decorators
from .models import Combo


# ---------------------------------------------------------------------------
# Sequence interpreter (copied from server.py)
# ---------------------------------------------------------------------------

def run_sequence(e: WSEngine, steps: list) -> int:
    total = 0
    for step in steps:
        t = step["type"]
        if t == "swing":
            e.damage_canceled = False
            total += e.swing(int(step["value"]))
        elif t == "burn":
            e.damage_canceled = False
            total += e.burn(int(step["value"]))
        elif t == "icytail":
            e.damage_canceled = False
            total += e.icytail(int(step["value"]))
        elif t == "ping_icytail":
            e.damage_canceled = False
            total += e.ping_icytail(int(step["value"]), int(step.get("dmg", 1)))
        elif t == "shuffleback":
            total += e.shuffleback(int(step["value"]))
        elif t == "moca":
            total += e.moca(int(step["value"]))
        elif t == "insert_top":
            e.insert_top(step.get("card", "DMG"))
        elif t == "reset_canceled":
            e.damage_canceled = False
        elif t == "if_canceled":
            if e.damage_canceled:
                e.damage_canceled = False
                total += run_sequence(e, step["steps"])
        elif t == "reveal_top_lv0_burn":
            total += e.reveal_top_lv0_burn(int(step["value"]))
        elif t == "direct_soul_check":
            total += e.direct_soul_check(int(step["value"]))
    return total


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------

def index(request):
    return render(request, 'ws_damage_sim/index.html')


@csrf_exempt
def api_simulate(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        req = json.loads(request.body)
    except (json.JSONDecodeError, Exception):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    sequence = req.get('sequence', [])
    iterations = int(req.get('iterations', 100_000))
    opp_deck_configs = req.get('opp_deck_configs', [
        {'first_deck_size': 30, 'first_climaxes': 8},
        {'first_deck_size': 25, 'first_climaxes': 8},
        {'first_deck_size': 20, 'first_climaxes': 8},
        {'first_deck_size': 30, 'first_climaxes': 6},
        {'first_deck_size': 25, 'first_climaxes': 6},
        {'first_deck_size': 20, 'first_climaxes': 6},
    ])
    opp_second_deck = req.get('opp_second_deck', {'size': 30, 'climaxes': 8})
    own_deck = req.get('own_deck', {'total_cards': 25, 'soul_triggers': 8, 'two_soul_triggers': 0})
    max_damage = int(req.get('max_damage', 14))

    t_start = timeit.default_timer()
    results = []

    for cfg in opp_deck_configs:
        engine = WSEngine(
            opp_first_deck_size=cfg['first_deck_size'],
            opp_first_climaxes=cfg['first_climaxes'],
            opp_second_deck_size=opp_second_deck['size'],
            opp_second_climaxes=opp_second_deck['climaxes'],
            own_total_cards=own_deck['total_cards'],
            own_soul_triggers=own_deck['soul_triggers'],
            own_2soul_triggers=own_deck.get('two_soul_triggers', 0),
        )

        damage_totals: list[int] = []
        for _ in range(iterations):
            engine.reset()
            total = run_sequence(engine, sequence)
            total += engine.opponent_draw()
            damage_totals.append(total)

        n = len(damage_totals)
        rates = [
            round(sum(1 for d in damage_totals if d >= threshold) / n * 100, 1)
            for threshold in range(1, max_damage + 1)
        ]
        results.append({
            'label': f"{cfg['first_climaxes']} CX / {cfg['first_deck_size']}",
            'rates': rates,
        })

    elapsed = round(timeit.default_timer() - t_start, 2)
    return JsonResponse({
        'results': results,
        'damage_range': list(range(1, max_damage + 1)),
        'iterations': iterations,
        'elapsed_sec': elapsed,
    })


@csrf_exempt
def api_combos(request):
    if request.method == 'GET':
        combos = []
        for combo in Combo.objects.all():
            combos.append({
                'id': combo.id,
                'name': combo.name,
                'sequence': json.loads(combo.sequence),
                'images': json.loads(combo.images),
            })
        return JsonResponse({'combos': combos})

    elif request.method == 'POST':
        try:
            body = json.loads(request.body)
        except (json.JSONDecodeError, Exception):
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        combo_id = body.get('id') or str(uuid.uuid4())
        Combo.objects.update_or_create(
            id=combo_id,
            defaults={
                'name': body['name'],
                'sequence': json.dumps(body['sequence']),
                'images': json.dumps(body['images']),
            },
        )
        return JsonResponse({'id': combo_id})

    return JsonResponse({'error': 'Method not allowed'}, status=405)


@csrf_exempt
def api_combo_detail(request, combo_id):
    if request.method == 'DELETE':
        Combo.objects.filter(id=combo_id).delete()
        return JsonResponse({'ok': True})
    return JsonResponse({'error': 'Method not allowed'}, status=405)
