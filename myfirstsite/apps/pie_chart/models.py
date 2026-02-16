from django.db import models

class Series(models.Model):
    name = models.CharField(max_length=100)
    def __str__(self):
        return self.name  # 正確：Series 有 name 欄位

class DeckCode(models.Model):
    code = models.CharField(max_length=10)  # 注意這裡是 code 不是 name！
    series = models.ForeignKey(Series, on_delete=models.PROTECT, related_name='deck_codes')
    def __str__(self):
        return self.code  # 修正：改為回傳 code 欄位

class Game(models.Model):
    name = models.CharField(max_length=100)
    date = models.DateField()
    participants = models.PositiveIntegerField()
    decks = models.ManyToManyField(DeckCode, related_name='games')
    pie_chart = models.ImageField(upload_to='pie_charts/', blank=True, null=True)
    def __str__(self):
        return self.name  # 正確：Game 有 name 欄位
