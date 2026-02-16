from itertools import groupby

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from .models import JournalEntry


def journal_list(request):
    entries = JournalEntry.objects.all()

    # Group entries by date
    grouped = []
    for date, group in groupby(entries, key=lambda e: e.created_at.date()):
        grouped.append((date, list(group)))

    return render(request, 'journal/list.html', {
        'grouped_entries': grouped,
        'mood_emojis': JournalEntry.MOOD_EMOJIS,
    })


@login_required
def journal_create(request):
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        content = request.POST.get('content', '').strip()
        mood = request.POST.get('mood', '')

        if content:
            JournalEntry.objects.create(
                title=title,
                content=content,
                mood=mood,
            )
            return redirect('journal:list')

        return render(request, 'journal/create.html', {
            'error': 'Content is required.',
            'mood_options': _mood_options(),
        })

    return render(request, 'journal/create.html', {
        'mood_options': _mood_options(),
    })


def _mood_options():
    """Return list of (value, label, emoji) tuples for template rendering."""
    return [(v, l, JournalEntry.MOOD_EMOJIS.get(v, '')) for v, l in JournalEntry.MOOD_CHOICES]


@login_required
@require_POST
def journal_delete(request, pk):
    entry = get_object_or_404(JournalEntry, pk=pk)
    entry.delete()
    return redirect('journal:list')
