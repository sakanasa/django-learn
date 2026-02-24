from django.db import models


def avatar_upload_path(instance, filename):
    return f'profile/avatars/{filename}'


class Profile(models.Model):
    display_name = models.CharField(max_length=100, default='Sakanasa')
    role         = models.CharField(max_length=100, default='Full-Stack Developer')
    bio          = models.TextField(blank=True, default='熱愛用程式解決問題的開發者...')
    avatar       = models.ImageField(upload_to=avatar_upload_path, blank=True, null=True)

    def __str__(self):
        return self.display_name


class Skill(models.Model):
    GRADIENT_CHOICES = [
        ('lavender-blue', 'Lavender → Blue'),
        ('pink-lavender',  'Pink → Lavender'),
        ('blue-pink',      'Blue → Pink'),
        ('lavender-pink',  'Lavender → Pink'),
    ]
    COLOR_CHOICES = [
        ('cyrene-lavender', 'Lavender'),
        ('cyrene-pink',     'Pink'),
        ('cyrene-blue',     'Blue'),
    ]
    profile     = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='skills')
    name        = models.CharField(max_length=100)
    percentage  = models.PositiveSmallIntegerField(default=70)
    gradient    = models.CharField(max_length=30, choices=GRADIENT_CHOICES, default='lavender-blue')
    label_color = models.CharField(max_length=30, choices=COLOR_CHOICES, default='cyrene-lavender')
    order       = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']
