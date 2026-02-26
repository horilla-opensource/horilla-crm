import json
from django.http import JsonResponse
from django.views.generic import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from horilla_generics.views import HorillaView
from django.contrib.auth.mixins import LoginRequiredMixin

from .services import AIService
from .models import AIChatHistory

class AskAIView(LoginRequiredMixin, HorillaView):
    template_name = "ask_ai.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["nav_title"] = "Horilla AI"
        context['available_models'] = [
            {'id': 'gemini-3-flash-preview', 'name': 'Gemini 3 Flash Preview', 'is_premium': False},
            {'id': 'gpt-4o', 'name': 'GPT-4o (Premium)', 'is_premium': True},
            {'id': 'claude-3-5-sonnet', 'name': 'Claude 3.5 Sonnet (Premium)', 'is_premium': True},
            {'id': 'gpt-4-turbo', 'name': 'GPT-4 Turbo (Premium)', 'is_premium': True},
        ]
        # Load last 20 messages for history
        history = AIChatHistory.objects.filter(user=self.request.user).order_by('created_at')[:20]
        context['chat_history'] = history
        return context

@method_decorator(csrf_exempt, name='dispatch')
class ChatAPIView(View):
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            message = data.get('message', '')
            model_id = data.get('model', 'gemini-3-flash-preview')
            
            response_text = AIService.get_model_response(message, request.user, model_id)

            # Save to history
            AIChatHistory.objects.create(
                user=request.user,
                message=message,
                response=response_text,
                model_id=model_id
            )

            return JsonResponse({
                'status': 'success', 
                'response': response_text, 
                'model': model_id
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

@method_decorator(csrf_exempt, name='dispatch')
class ClearChatAPIView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            AIChatHistory.objects.filter(user=request.user).delete()
            return JsonResponse({'status': 'success', 'message': 'Chat history cleared'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
