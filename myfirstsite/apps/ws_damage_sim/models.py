from django.db import models


class Combo(models.Model):
    id = models.CharField(max_length=64, primary_key=True)
    name = models.CharField(max_length=100)
    sequence = models.TextField()   # JSON string
    images = models.TextField()     # JSON string (base64 array)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'ws_damage_sim'
        ordering = ['created_at']

    def __str__(self):
        return self.name
