from django.contrib import admin
from .models import JournalEntry


@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'mood', 'created_at')
    list_filter = ('mood', 'created_at')
    search_fields = ('title', 'content')
    readonly_fields = ('created_at', 'updated_at')
