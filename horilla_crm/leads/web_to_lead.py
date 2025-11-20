from django import forms
from django.views.generic import TemplateView, CreateView,UpdateView
from django.http import Http404, HttpResponseRedirect, HttpResponse
from django.shortcuts import render
from django.urls import reverse, reverse_lazy
from django.conf import settings
from django.contrib.auth import get_user_model

from horilla.exceptions import HorillaHttp404
from horilla_core.decorators import permission_required_or_denied
from .models import Lead, LeadCaptureForm, LeadStatus
from django.contrib.auth.mixins import LoginRequiredMixin
from django.template.loader import render_to_string
from django.views.decorators.clickjacking import xframe_options_exempt
from django.utils.decorators import method_decorator
from urllib.parse import urlparse
from django.views import View
from django.utils import translation
from django.views.decorators.csrf import csrf_exempt
import json

@method_decorator(
    permission_required_or_denied("leads.add_leadcaptureform"), name="dispatch"
)
class LeadFormBuilderView(LoginRequiredMixin, TemplateView):
    """View for building lead capture forms"""
    template_name = 'web_to_lead/lead_form_builder.html'
    action = None  # allow parameter

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get all Lead model fields
        lead_fields = []
        exclude_fields = [
            'id', 'is_active', 'created_at', 'updated_at', 'is_convert','additional_info','created_by','updated_by',
            'lead_score', 'email_message_id', 'lead_owner', 'lead_status','company','lead_source','requirements'
        ]

        for field in Lead._meta.get_fields():
            if field.concrete and not field.auto_created and field.name not in exclude_fields:
                field_info = {
                    'name': field.name,
                    'verbose_name': getattr(field, 'verbose_name', field.name),
                    'required': not getattr(field, 'blank', False),
                    'field_type': field.get_internal_type(),
                }
                lead_fields.append(field_info)
        User = get_user_model()
        context['lead_fields'] = lead_fields
        context['lead_owners'] =  User.objects.filter(is_active=True)        
        return context
    
   
@method_decorator(
    permission_required_or_denied("leads.add_leadcaptureform"), name="dispatch"
)    
class UpdateFormHeadingView(LoginRequiredMixin, TemplateView):
    """HTMX view to update form heading"""
    template_name = 'web_to_lead/form_heading.html'
    
    def post(self, request, *args, **kwargs):
        form_name = request.POST.get('form_name', '').strip()
        color = request.POST.get('color', '#ffffff')
        
        language = request.POST.get('language', 'en')  # Add language
        
        context = {
            'form_name': form_name if form_name else 'Contact Us',
            'color': color,
            'language': language  # Pass to template
        }
        
        return render(request, self.template_name, context)

@method_decorator(
    permission_required_or_denied("leads.add_leadcaptureform"), name="dispatch"
)
class UpdateFormPreviewView(LoginRequiredMixin, TemplateView):
    """HTMX view to update form preview"""
    template_name = 'web_to_lead/form_preview.html'
    
    def post(self, request, *args, **kwargs):
        
        
        selected_fields = request.POST.getlist('selected_fields[]')
        form_name = request.POST.get('form_name', '').strip()
        color = request.POST.get('color')
        language = request.POST.get('language', 'en')
        translation.activate(language)
        
        # Get field details
        fields_data = []
        for field_name in selected_fields:
            try:
                field = Lead._meta.get_field(field_name)
                fields_data.append({
                    'name': field_name,
                    'verbose_name': field.verbose_name if hasattr(field, 'verbose_name') else field_name,
                    'required': not field.blank if hasattr(field, 'blank') else True,
                    'field_type': field.get_internal_type(),
                    'choices': field.choices if hasattr(field, 'choices') and field.choices else None,
                })
            except:
                pass
        
        context = {
            'fields': fields_data,
            'color': color,
            'form_name': form_name,
            'language': language
        }
        
        return render(request, self.template_name, context)

@method_decorator(
    permission_required_or_denied("leads.add_leadcaptureform"), name="dispatch"
)
class SaveLeadFormView(LoginRequiredMixin, UpdateView):
    """View to save lead capture form configuration - one per company"""
    model = LeadCaptureForm
    fields = [
        'form_name', 
        'return_url_enable',
        'return_url', 
        'success_message',
        'success_description',
        'enable_recaptcha', 
        'language', 
        'header_color'
    ]
    success_url = reverse_lazy('leads:form_builder')
    template_name = 'web_to_lead/lead_form_builder.html'
    
    def get_object(self, queryset=None):
        """Get or create the form for the current company"""
        obj, created = LeadCaptureForm.objects.get_or_create(
            company=self.request.active_company,
            defaults={
                'created_by': self.request.user,
                'form_name': 'Contact Us',
                'language': 'en',
                'header_color': '#ffffff',
            }
        )
        return obj
    
    def form_valid(self, form):
        # Set the instance fields
        form.instance.created_by = self.request.user
        form.instance.company = self.request.active_company
        selected_fields = self.request.POST.getlist('selected_fields[]')
        form.instance.selected_fields = json.dumps(selected_fields)
        form.instance.header_color = self.request.POST.get('color')
        form.instance.lead_owner_id = self.request.POST.get("lead_owner")  

        if not selected_fields:
            form.add_error(None, "Select at least one field.")
            return self.form_invalid(form)

        return_url_enable = self.request.POST.get('return_url_enable') == 'on'
        form.instance.return_url_enable = return_url_enable
        
        if return_url_enable:
            if not form.instance.return_url:
                form.add_error('return_url', 'Return URL is required when enabled.')
                return self.form_invalid(form)
            form.instance.success_message = None
            form.instance.success_description = None
        else:
            if not form.instance.success_message:
                form.add_error('success_message', 'Success message is required.')
                return self.form_invalid(form)
            if not form.instance.success_description:
                form.add_error('success_description', 'Success description is required.')
                return self.form_invalid(form)
            # Clear return URL
            form.instance.return_url = None
        
        selected_language = form.instance.language
        
        translation.activate(selected_language)
        
        self.object = form.save()

        parsed_fields = []
        for field_name in selected_fields:
            try:
                field = Lead._meta.get_field(field_name)
                field_info = {
                    'name': field_name,
                    'verbose_name': str(getattr(field, 'verbose_name', field_name)),
                    'required': not getattr(field, 'blank', False),
                    'field_type': field.get_internal_type(),
                    'choices': getattr(field, 'choices', None)
                }
                parsed_fields.append(field_info)
            except:
                pass

        html_code = render_to_string(
            'web_to_lead/public_lead_form.html',
            {
                'form_obj': self.object,
                'selected_fields_parsed': parsed_fields,
                'form_id': self.object.id,
                'view': {'kwargs': {'form_id': self.object.id}},
            }
        )

        self.object.generated_html = html_code
        self.object.save()
        
        translation.deactivate()

        if self.request.headers.get('HX-Request'):
            form_url = self.request.build_absolute_uri(
                reverse('leads:public_lead_form', kwargs={'form_id': self.object.id})
            )
            
            return render(self.request, 'web_to_lead/form_saved_success.html', {
                'form_id': self.object.id,
                'form_url': form_url,
                'html_code': html_code,
            })

        return HttpResponseRedirect(self.success_url)
    
    def form_invalid(self, form):
        if self.request.headers.get('HX-Request'):
            # Get the parent view's context to include lead_fields
            lead_fields = []
            exclude_fields = [
                'id', 'is_active', 'created_at', 'updated_at', 'is_convert','additional_info','created_by','updated_by',
                'lead_score', 'email_message_id', 'lead_owner', 'lead_status','company','lead_source','requirements'
            ]

            for field in Lead._meta.get_fields():
                if field.concrete and not field.auto_created and field.name not in exclude_fields:
                    field_info = {
                        'name': field.name,
                        'verbose_name': getattr(field, 'verbose_name', field.name),
                        'required': not getattr(field, 'blank', False),
                        'field_type': field.get_internal_type(),
                    }
                    lead_fields.append(field_info)
            
            # Preserve form data
            form_data = {
                'form_name': self.request.POST.get('form_name', 'Contact Us'),
                'return_url_enable': self.request.POST.get('return_url_enable') == 'on',
                'return_url': self.request.POST.get('return_url', ''),
                'success_message': self.request.POST.get('success_message', ''),
                'success_description': self.request.POST.get('success_description', ''),
                'language': self.request.POST.get('language', 'en'),
                'color': self.request.POST.get('color', '#ffffff'),
                'selected_fields': self.request.POST.getlist('selected_fields[]'),
                'lead_owner': self.request.POST.get("lead_owner")

            }
            
            context = {
                'form': form,
                'errors': form.errors,
                'lead_fields': lead_fields,
                'form_data': form_data,
            }
            
            response = render(self.request, self.template_name, context)
            response['HX-Reselect'] = '#formBuilderForm'
            return response
        return super().form_invalid(form)
    
@method_decorator(
    permission_required_or_denied("leads.add_leadcaptureform"), name="dispatch"
)
class AddFieldView(LoginRequiredMixin, TemplateView):
    """HTMX view to add a field to selected list"""
    template_name = 'web_to_lead/selected_field.html'
    
    def post(self, request, *args, **kwargs):
        field_name = request.POST.get('field_name')
        field_verbose = request.POST.get('field_verbose')
        form_name = request.POST.get('form_name')
        language = request.POST.get('language', 'en')  # Add language
        
        context = {
            'field_name': field_name,
            'field_verbose': field_verbose,
            'form_name': form_name,
            'language': language  # Pass to template
        }
        
        # Trigger preview update after field is added
        response = render(request, self.template_name, context)
        response['HX-Trigger'] = 'updatePreview'
        return response


@method_decorator(
    permission_required_or_denied("leads.add_leadcaptureform"), name="dispatch"
)
class RemoveFieldView(LoginRequiredMixin, View):

    def post(self, request, *args, **kwargs):
        field_name = request.POST.get('field_name')
        js = f"""
        <script>
            var btn = document.querySelector('[data-field="{field_name}"].available-field');
            if(btn) btn.style.display = 'block';
            htmx.trigger('#colorPicker', 'change');
        </script>
        """
        response = HttpResponse(js)
        response['HX-Trigger'] = 'updatePreview'
        return response
    

@method_decorator(xframe_options_exempt, name='dispatch')
@method_decorator(csrf_exempt, name='dispatch')
class PublicLeadFormView(CreateView):
    """Public view for lead submission with HTMX support"""
    model = Lead
    template_name = 'web_to_lead/public_lead_form.html'
    
    def get_form_class(self):
        form_id = self.kwargs.get('form_id')
        try:
            form_config = LeadCaptureForm.objects.get(id=form_id, is_active=True)
            
            # Activate the form's language
            translation.activate(form_config.language)
            
            selected_fields = json.loads(form_config.selected_fields)
            
            class DynamicLeadForm(forms.ModelForm):
                class Meta:
                    model = Lead
                    fields = selected_fields
                    
            return DynamicLeadForm
        except LeadCaptureForm.DoesNotExist as e:
            raise HorillaHttp404(str(e), template="web_to_lead/web_to_lead_404.html")
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form_id = self.kwargs.get('form_id')
        
        try:
            form_config = LeadCaptureForm.objects.get(id=form_id, is_active=True)
            
            # Activate the form's language
            translation.activate(form_config.language)
            
            context['form_obj'] = form_config
            context['form_config'] = form_config
            
            # Parse selected fields for template
            selected_fields = json.loads(form_config.selected_fields)
            parsed_fields = []
            
            for field_name in selected_fields:
                try:
                    field = Lead._meta.get_field(field_name)
                    field_info = {
                        'name': field_name,
                        'verbose_name': str(getattr(field, 'verbose_name', field_name)),
                        'required': not getattr(field, 'blank', False),
                        'field_type': field.get_internal_type(),
                        'choices': getattr(field, 'choices', None)
                    }
                    parsed_fields.append(field_info)
                except:
                    pass
            
            context['selected_fields_parsed'] = parsed_fields
            
        except LeadCaptureForm.DoesNotExist as e:
            raise HorillaHttp404(str(e), template="web_to_lead/web_to_lead_404.html")
            
        return context
    
    def form_valid(self, form):
        form_id = self.kwargs.get('form_id')
        form_config = LeadCaptureForm.objects.get(id=form_id)
        form.instance.lead_owner = form_config.lead_owner
        form.instance.company = form_config.company
        form.instance.lead_source = 'website'
        try:
            form.instance.lead_status = LeadStatus.objects.first()
        except:
            pass
        
        self.object = form.save()
        
        # Check if this is an HTMX request
        if self.request.headers.get('HX-Request'):
            # Check if return URL exists
            if form_config.return_url and form_config.return_url.strip():
                return_url = form_config.return_url.strip()
                
                # Parse the URL to check if it's external
                parsed_url = urlparse(return_url)
                
                # If no scheme is present, add https://
                if not parsed_url.scheme:
                    if return_url.startswith('/'):
                        # It's a relative URL on the same domain
                        response = HttpResponse()
                        response['HX-Redirect'] = return_url
                        return response
                    else:
                        return_url = 'https://' + return_url
                
                # External redirect via HTMX
                response = HttpResponse()
                response['HX-Redirect'] = return_url
                return response
            
            header_color = form_config.header_color if form_config.header_color and form_config.header_color != '#ffffff' else 'hsl(8, 77%, 56%)'
            success_message = form_config.success_message if form_config.success_message else "Thank you!"
            success_description = form_config.success_description if form_config.success_description else "We have received your information and will get back to you soon."

            return render(self.request, 'web_to_lead/form_success.html', {  
                'header_color': header_color,
                'success_message': success_message,
                'success_description': success_description
            })
        return ""
        
       
    
    def form_invalid(self, form):
        # For HTMX requests, return the form with errors
        if self.request.headers.get('HX-Request'):
            return self.render_to_response(self.get_context_data(form=form))
        
        # Non-HTMX fallback
        return super().form_invalid(form)

@method_decorator(
    permission_required_or_denied("leads.add_leadcaptureform"), name="dispatch"
)   
class ToggleReturnUrlView(LoginRequiredMixin, View):
    """Toggle between return URL and success message fields"""
    
    def post(self, request, *args, **kwargs):
        return_url_enabled = request.POST.get('return_url_enable') == 'on'
        
        context = {
            'return_url_enabled': return_url_enabled
        }
        
        html = render_to_string('web_to_lead/conditional_fields.html', context, request=request)
        return HttpResponse(html)