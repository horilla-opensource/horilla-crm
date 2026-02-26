from django.contrib import admin
from .models import AIChatHistory

@admin.register(AIChatHistory)
class AIChatHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'message_snippet', 'model_id', 'created_at')
    list_filter = ('user', 'model_id', 'created_at')
    search_fields = ('message', 'response', 'user__username')
    readonly_fields = ('created_at',)

    def message_snippet(self, obj):
        return obj.message[:50] + ("..." if len(obj.message) > 50 else "")
    message_snippet.short_description = 'Message'

from .models import AIRequestLog
@admin.register(AIRequestLog)
class AIRequestLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'model_id', 'intent_snippet', 'latency_ms', 'is_success', 'created_at')
    list_filter = ('model_id', 'is_success', 'created_at')
    readonly_fields = ('created_at',)

    def intent_snippet(self, obj):
        return obj.request_payload.get('intent', 'N/A')
    intent_snippet.short_description = 'Intent'
