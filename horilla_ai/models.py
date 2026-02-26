from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

class AIChatHistory(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ai_chat_history",
        verbose_name=_("User")
    )
    message = models.TextField(verbose_name=_("User Message"))
    response = models.TextField(verbose_name=_("AI Response"))
    model_id = models.CharField(max_length=100, verbose_name=_("Model ID"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))

    class Meta:
        verbose_name = _("AI Chat History")
        verbose_name_plural = _("AI Chat Histories")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} - {self.created_at}"

class AIRequestLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="ai_logs",
        verbose_name=_("User")
    )
    request_payload = models.JSONField(verbose_name=_("Request Payload"))
    response_payload = models.JSONField(null=True, blank=True, verbose_name=_("Response Payload"))
    model_id = models.CharField(max_length=100, verbose_name=_("Model ID"))
    
    # Performance & Cost
    latency_ms = models.IntegerField(default=0, verbose_name=_("Latency (ms)"))
    prompt_tokens = models.IntegerField(default=0, verbose_name=_("Prompt Tokens"))
    completion_tokens = models.IntegerField(default=0, verbose_name=_("Completion Tokens"))
    total_tokens = models.IntegerField(default=0, verbose_name=_("Total Tokens"))
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=6, default=0, verbose_name=_("Estimated Cost ($)"))
    
    status_code = models.IntegerField(null=True, blank=True)
    is_success = models.BooleanField(default=True)
    error_message = models.TextField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("AI Request Log")
        verbose_name_plural = _("AI Request Logs")
        ordering = ["-created_at"]
