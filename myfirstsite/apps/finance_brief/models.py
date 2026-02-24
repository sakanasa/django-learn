from django.db import models


class DailyBrief(models.Model):
    date           = models.DateField(unique=True, db_index=True)
    market_data    = models.JSONField(default=dict)   # {indices, fx, commodities}
    news_headlines = models.JSONField(default=list)   # [{title, url, source, published}]
    llm_summary    = models.TextField(blank=True)     # markdown
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f'Daily Brief {self.date}'
