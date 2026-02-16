from django.db import models


class JournalEntry(models.Model):
    MOOD_CHOICES = [
        ('happy', 'Happy'),
        ('thinking', 'Thinking'),
        ('inspired', 'Inspired'),
        ('tired', 'Tired'),
        ('calm', 'Calm'),
    ]
    MOOD_EMOJIS = {
        'happy': '😊',
        'thinking': '🤔',
        'inspired': '✨',
        'tired': '😴',
        'calm': '🌊',
    }

    title = models.CharField(max_length=200, blank=True)
    content = models.TextField()
    mood = models.CharField(max_length=20, choices=MOOD_CHOICES, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Journal entries'

    def __str__(self):
        if self.title:
            return self.title
        return f"Entry on {self.created_at:%Y-%m-%d %H:%M}"

    @property
    def mood_emoji(self):
        return self.MOOD_EMOJIS.get(self.mood, '')
