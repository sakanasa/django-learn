from django.contrib import admin
from .models import DailyBrief


@admin.register(DailyBrief)
class DailyBriefAdmin(admin.ModelAdmin):
    list_display  = ['date', 'has_market_data', 'has_summary', 'updated_at']
    readonly_fields = ['date', 'created_at', 'updated_at']

    @admin.display(boolean=True, description='市場數據')
    def has_market_data(self, obj):
        return bool(obj.market_data)

    @admin.display(boolean=True, description='LLM 摘要')
    def has_summary(self, obj):
        return bool(obj.llm_summary)
