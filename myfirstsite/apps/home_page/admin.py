from django.contrib import admin
from .models import Profile, Skill


class SkillInline(admin.TabularInline):
    model  = Skill
    extra  = 1
    fields = ['name', 'percentage', 'gradient', 'label_color', 'order']


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['display_name', 'role']
    inlines      = [SkillInline]
