from django.contrib import admin



from django.contrib import admin
from .models import Series, DeckCode, Game  # 正確導入所有模型

admin.site.register(Series)
admin.site.register(DeckCode)
admin.site.register(Game)
