from django.conf import settings
from django.shortcuts import redirect, render
from django.template import Context, Template
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from horilla_core.decorators import htmx_required
from horilla_core.forms import CompanyFormClass, UserFormClassSingle
from horilla_core.models import Company, HorillaUser, Role
from horilla_core.progress import ProgressStepsMixin
from horilla_generics.views import HorillaSingleFormView


class InitializeDatabaseConditionView(View):
    """
    checks whether the database needs initialization.
    """

    def get_initialize_condition(self):
        initialize_database = not HorillaUser.objects.exists()
        return initialize_database


class InitializeDatabase(View, ProgressStepsMixin):

    current_step = 1

    def get(self, request, *args, **kwargs):
        condition_view = InitializeDatabaseConditionView()
        initialize_database = condition_view.get_initialize_condition()
        next_url = request.GET.get("next", "/")
        if initialize_database:
            context = {
                "progress_steps": self.get_progress_steps(),
                "current_step": self.current_step,
            }
            return render(request, "initialize_database/db_password.html", context)
        return redirect(next_url)


class InitializeDatabaseUser(View, ProgressStepsMixin):

    current_step = 2

    def get(self, request, *args, **kwargs):
        condition_view = InitializeDatabaseConditionView()
        initialize_database = condition_view.get_initialize_condition()
        next_url = request.GET.get("next", "/")
        if (
            request.session.get("db_password") == settings.DB_INIT_PASSWORD
            and initialize_database
        ):
            context = {
                "progress_steps": self.get_progress_steps(),
                "current_step": self.current_step,
            }
            return render(request, "initialize_database/sign_up.html", context)
        return redirect(next_url)

    def post(self, request, *args, **kwargs):
        password = self.request.POST.get("db_password")

        if settings.DB_INIT_PASSWORD == password:
            request.session["db_password"] = password
            context = {
                "progress_steps": self.get_progress_steps(),
                "current_step": self.current_step,
            }
            return render(request, "initialize_database/sign_up.html", context)

        return render(
            request,
            "initialize_database/db_password.html",
            {"error": "Invalid password, please try again.", "password": password},
        )


class InitializeDatabaseCompany(View, ProgressStepsMixin):

    current_step = 3

    def get(self, request, *args, **kwargs):
        next_url = request.GET.get("next", "/")
        if request.session.get("db_password") == settings.DB_INIT_PASSWORD:
            context = {
                "progress_steps": self.get_progress_steps(),
                "current_step": self.current_step,
            }
            return render(
                request, "initialize_database/company_initialize.html", context
            )
        return redirect(next_url)


@method_decorator(htmx_required(login=False), name="dispatch")
class SignUpFormView(HorillaSingleFormView, ProgressStepsMixin):

    model = HorillaUser
    view_id = "user-form-view"
    form_url = reverse_lazy("horilla_core:sign_up_user")
    form_class = UserFormClassSingle
    header = False
    modal_height = False
    current_step = 3
    html = """
        {% load i18n static %}
        <div class="flex justify-end pt-5">
            <button class="border-[1px] border-[solid] border-[#e54f38] hover:border-[#9b210f] hover:bg-secondary-600 rounded-[5px] px-[15px] py-[8px] text-[#e54f38] flex gap-3 btn-with-icon border-[#e54f38] [transition:.3s] hover:text-[white]">
                {% trans "Next" %}
                <img src="{% static 'assets/icons/ar3.svg' %}" alt="" />
            </button>
        </div>
    """

    def get_button_html(self):
        t = Template(self.html)
        return t.render(Context({}))

    def form_valid(self, form):
        instance = form.save(commit=False)
        instance.is_staff = True
        instance.is_superuser = True
        instance.save()
        context = {
            "progress_steps": self.get_progress_steps(),
            "current_step": self.current_step,
        }
        response = render(
            self.request, "initialize_database/company_initialize.html", context
        )
        response["HX-Retarget"] = "#initialize-user"
        response["HX-Reselect"] = "#initialize-company"
        response["HX-Push-Url"] = str(
            reverse_lazy("horilla_core:initialize_database_company")
        )
        return response


@method_decorator(htmx_required(login=False), name="dispatch")
class InitializeCompanyFormView(HorillaSingleFormView, ProgressStepsMixin):

    model = Company
    view_id = "user-form-view"
    form_url = reverse_lazy("horilla_core:initialize_company_form")
    form_class = CompanyFormClass
    current_step = 4
    header = False
    modal_height = False
    html = """
        {% load i18n static %}
        <div class="flex justify-end pt-5">
            <button class="border-[1px] border-[solid] border-[#e54f38] hover:border-[#9b210f] hover:bg-secondary-600 rounded-[5px] px-[15px] py-[8px] text-[#e54f38] flex gap-3 btn-with-icon border-[#e54f38] [transition:.3s] hover:text-[white]">
                {% trans "Next" %}
                <img src="{% static 'assets/icons/ar3.svg' %}" alt="" />
            </button>
        </div>
    """

    def get_button_html(self):
        t = Template(self.html)
        return t.render(Context({}))

    def form_valid(self, form):
        instance = form.save(commit=False)
        instance.save()
        user = HorillaUser.objects.filter(is_superuser=True).first()
        user.company = instance
        user.save(update_fields=["company"])
        self.request.session["company_id"] = instance.id
        context = {
            "progress_steps": self.get_progress_steps(),
            "current_step": self.current_step,
            "company_id": instance.id,
            "is_last": self.is_last_step(),
        }
        response = render(
            self.request, "initialize_database/initialize_role.html", context
        )
        response["HX-Retarget"] = "#initialize-company"
        response["HX-Reselect"] = "#initialize-role"
        response["HX-Push-Url"] = str(
            reverse_lazy("horilla_core:initialize_database_role")
        )
        return response
        return


@method_decorator(csrf_exempt, name="dispatch")
class InitializeRoleView(View, ProgressStepsMixin):
    template_name = "initialize_database/initialize_role.html"
    current_step = 4
    response_template = None
    push_url = None
    select_id = None

    def get(self, request, *args, **kwargs):
        next_url = request.GET.get("next", "/")
        company_id = request.GET.get("company_id") or request.session.get("company_id")
        edit_role_id = request.GET.get("edit_role")
        roles = Role.objects.all()

        edit_role = None
        if edit_role_id:
            edit_role = Role.objects.filter(id=edit_role_id).first()

        if request.session.get("db_password") == settings.DB_INIT_PASSWORD:
            context = {
                "progress_steps": self.get_progress_steps(),
                "current_step": self.current_step,
                "roles": roles,
                "company_id": company_id,
                "edit_role": edit_role,
                "is_last": self.is_last_step(),
                "push_url": (
                    self.push_url
                    if self.push_url
                    else reverse_lazy("horilla_core:login")
                ),
                "select_id": self.select_id if self.select_id else "sec1",
            }
            return render(request, self.template_name, context)
        return redirect(next_url)

    def post(self, request, *args, **kwargs):
        next_step = request.POST.get("next_step")
        company_id = request.POST.get("company_id") or request.session.get("company_id")
        role_name = request.POST.get("role_name")
        description = request.POST.get("description")
        parent_role_id = request.POST.get("parent_role")
        next_url = request.POST.get("next", "/")
        delete_role_id = request.POST.get("delete_role")
        edit_role_id = request.POST.get("edit_role_id")

        if delete_role_id:
            role_to_delete = Role.objects.filter(id=delete_role_id).first()
            if role_to_delete:
                role_to_delete.delete()

        elif role_name and description:
            parent_role = (
                Role.objects.filter(id=parent_role_id).first()
                if parent_role_id
                else None
            )
            if edit_role_id:
                role = Role.objects.filter(id=edit_role_id).first()
                if role:
                    role.role_name = role_name
                    role.description = description
                    role.parent_role = parent_role
                    role.save()
            else:  # Create new role
                Role.objects.create(
                    role_name=role_name,
                    description=description,
                    parent_role=parent_role,
                )

        if next_step == "true":
            if self.is_last_step():
                request.session.flush()
            else:
                self.current_step = 5
            context = {
                "progress_steps": self.get_progress_steps(),
                "current_step": self.current_step,
                "company_id": company_id,
            }
            if self.response_template:
                return render(request, self.response_template, context)

            return redirect(next_url)

        roles = Role.objects.all()
        context = {
            "progress_steps": self.get_progress_steps(),
            "current_step": self.current_step,
            "roles": roles,
            "company_id": company_id,
            "is_last": self.is_last_step(),
            "push_url": (
                self.push_url if self.push_url else reverse_lazy("horilla_core:login")
            ),
            "select_id": self.select_id if self.select_id else "sec1",
        }
        return render(request, self.template_name, context)
