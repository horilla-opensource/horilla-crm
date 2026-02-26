import json
import logging
import time
import hashlib
import requests
from decimal import Decimal
from django.conf import settings
from django.apps import apps
from django.db.models import Sum
from django.core.cache import cache
from django.utils.timezone import now
from .models import AIRequestLog

logger = logging.getLogger(__name__)

class AIIntents:
    TOP_LEADS = "top_leads"
    RECENT_LEADS = "recent_leads"
    HIGH_VALUE_DEALS = "high_value_deals"
    PIPELINE_SUMMARY = "pipeline_summary"
    GENERAL = "general"

class AIService:
    THROTTLE_LIMIT = 50 
    THROTTLE_TIMEOUT = 3600
    
    @staticmethod
    def _generate_cache_key(message, model_id):
        """Generates a stable cache key using SHA-256."""
        hash_obj = hashlib.sha256(f"{message}_{model_id}".encode())
        return f"ai_cache_{hash_obj.hexdigest()}"

    @staticmethod
    def detect_intent(message):
        msg = message.lower()
        if any(word in msg for word in ['top', 'score', 'best']) and 'lead' in msg:
            return AIIntents.TOP_LEADS
        if any(word in msg for word in ['recent', 'new', 'latest']) and 'lead' in msg:
            return AIIntents.RECENT_LEADS
        if any(word in msg for word in ['top', 'big', 'value', 'large']) and ('opportunity' in msg or 'deal' in msg):
            return AIIntents.HIGH_VALUE_DEALS
        if any(word in msg for word in ['pipeline', 'summary', 'revenue', 'forecast', 'stats']):
            return AIIntents.PIPELINE_SUMMARY
        return AIIntents.GENERAL

    @staticmethod
    def get_crm_context(message, user, intent):
        """
        Structured Context Builder with Decimal safety and size limits.
        """
        context = {'stats': {}, 'detailed_data': {}, 'intent': intent}
        
        if apps.is_installed('horilla_crm.leads'):
            context['stats']['leads_count'] = apps.get_model('leads', 'Lead').objects.count()
        
        if apps.is_installed('horilla_crm.opportunities'):
            Opportunity = apps.get_model('opportunities', 'Opportunity')
            context['stats']['opps_count'] = Opportunity.objects.count()
           
            pipeline_val = Opportunity.objects.aggregate(total=Sum('amount'))['total'] or 0
            context['stats']['pipeline_val'] = float(pipeline_val)

        
        limit = 5
        if intent == AIIntents.TOP_LEADS and apps.is_installed('horilla_crm.leads'):
            Lead = apps.get_model('leads', 'Lead')
            leads = Lead.objects.order_by('-lead_score')[:limit]
            context['detailed_data']['leads'] = [
                {'name': f"{l.first_name} {l.last_name}", 'score': l.lead_score, 'company': l.lead_company}
                for l in leads
            ]
        
        elif intent == AIIntents.RECENT_LEADS and apps.is_installed('horilla_crm.leads'):
            Lead = apps.get_model('leads', 'Lead')
            leads = Lead.objects.order_by('-created_at')[:limit]
            context['detailed_data']['leads'] = [
                {'name': f"{l.first_name} {l.last_name}", 'created': l.created_at.strftime('%Y-%m-%d')}
                for l in leads
            ]

        elif intent == AIIntents.HIGH_VALUE_DEALS and apps.is_installed('horilla_crm.opportunities'):
            Opportunity = apps.get_model('opportunities', 'Opportunity')
            opps = Opportunity.objects.order_by('-amount')[:limit]
            context['detailed_data']['deals'] = [
                {'name': o.name, 'amount': float(o.amount or 0), 'stage': o.stage.name if o.stage else 'N/A'}
                for o in opps
            ]

        context['stats']['summary'] = f"User has {context['stats'].get('leads_count', 0)} leads and {context['stats'].get('opps_count', 0)} opportunities."
        return context

    @staticmethod
    def check_throttle(user):
        if user.is_superuser:
            return True
        cache_key = f"ai_throttle_{user.id}"
        count = cache.get(cache_key, 0)
        if count >= AIService.THROTTLE_LIMIT:
            return False
        cache.set(cache_key, count + 1, AIService.THROTTLE_TIMEOUT)
        return True

    @classmethod
    def get_model_response(cls, message, user, model_id='gemini-3-flash-preview'):
        if not getattr(user, 'enable_ai', False):
            return "AI Assistant is disabled for your account. Please enable it in your User Profile settings."

        if not cls.check_throttle(user):
            return "Rate limit exceeded. Please try again later."

        cache_key = cls._generate_cache_key(message, model_id)
        cached = cache.get(cache_key)
        if cached:
            return cached

        intent = cls.detect_intent(message)
        context = cls.get_crm_context(message, user, intent)
        
        start_time = time.time()
        
        provider = GeminiProvider() if 'gemini' in model_id else None
        
        if not provider:
            return f"Model {model_id} is not supported or misconfigured."

        res_data = provider.call(message, context, model_id)
        latency = int((time.time() - start_time) * 1000)

        total_tokens = res_data['prompt_tokens'] + res_data['completion_tokens']
        pricing_map = getattr(settings, 'AI_MODEL_PRICING', {})
        pricing = pricing_map.get(model_id, pricing_map.get('default', 0.10))
        estimated_cost = (total_tokens / 1000000) * pricing

        AIRequestLog.objects.create(
            user=user,
            model_id=model_id,
            request_payload={'message': message, 'intent': intent, 'context_stats': context['stats']},
            response_payload={'text': res_data['text']},
            latency_ms=latency,
            prompt_tokens=res_data['prompt_tokens'],
            completion_tokens=res_data['completion_tokens'],
            total_tokens=total_tokens,
            estimated_cost=Decimal(str(round(estimated_cost, 6))),
            is_success=res_data.get('is_success', False),
            error_message=res_data.get('error_msg'),
        )

        if res_data.get('is_success'):
            cache.set(cache_key, res_data['text'], 300)
            
        return res_data['text']

class AIProvider:
    def call(self, message, context, model_id):
        raise NotImplementedError

class GeminiProvider(AIProvider):
    def call(self, message, context, model_id):
        res_template = {
            'text': "API Error",
            'is_success': False,
            'error_msg': None,
            'prompt_tokens': 0,
            'completion_tokens': 0
        }
        
        if not getattr(settings, 'GEMINI_API_KEY', None):
            res_template['text'] = "Gemini API Key missing in system settings."
            res_template['error_msg'] = "Config Error"
            return res_template
        
        safe_context = json.dumps(context)
        prompt = f"Role: Horilla CRM Assistant\nContext: {safe_context}\nQuestion: {message}\nFormat: Markdown tables if possible."
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={settings.GEMINI_API_KEY}"
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        
        try:
            res = requests.post(url, json=payload, timeout=25)
            data = res.json()
            if res.status_code == 200:
                candidate = data['candidates'][0]
                res_template['text'] = candidate['content']['parts'][0]['text']
                res_template['is_success'] = True
                
                usage = data.get('usageMetadata', {})
                res_template['prompt_tokens'] = usage.get('promptTokenCount', 0)
                res_template['completion_tokens'] = usage.get('candidatesTokenCount', 0)
                return res_template
            
            res_template['error_msg'] = f"Google API Error: {res.status_code} - {data.get('error', {}).get('message')}"
            return res_template
        except Exception as e:
            res_template['error_msg'] = str(e)
            return res_template
