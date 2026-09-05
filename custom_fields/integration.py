"""
Integration hooks for injecting custom fields into Lead and Opportunity forms
and detail views.
"""

from custom_fields.utils import (
    CUSTOM_FIELD_PREFIX,
    build_custom_form_fields,
    custom_field_form_name,
    get_custom_field_definitions,
    is_custom_field_name,
    load_custom_field_values,
    save_custom_field_values,
)


class CustomFieldSaveMixin:
    """
    Persist extra ``cf_*`` form fields after the model instance is saved.

    Horilla multi-step and single-step views both call ``save(commit=False)``
    then ``instance.save()`` then ``form.save_m2m()``. Hooking ``save_m2m``
    is the reliable place to write custom field values without wrapping
    the view's ``form_valid``.

    ``use_required_attribute = False`` keeps Django's ``required`` validation
    but skips the HTML ``required`` attribute. Native browser validation
    otherwise blocks the last wizard step: the step body is in a 300px
    overflow box, and Select2-hidden choice fields are not focusable.
    """

    use_required_attribute = False

    def save(self, commit=True):
        instance = super().save(commit=commit)
        if commit:
            self._persist_custom_fields(instance)
        else:
            original_save_m2m = self.save_m2m

            def _save_m2m():
                original_save_m2m()
                self._persist_custom_fields(self.instance)

            self.save_m2m = _save_m2m
        return instance

    def _persist_custom_fields(self, instance):
        if not instance or not instance.pk:
            return
        cleaned = {
            key: value
            for key, value in (getattr(self, "cleaned_data", None) or {}).items()
            if key.startswith(CUSTOM_FIELD_PREFIX)
        }
        if not cleaned:
            return
        save_custom_field_values(
            instance.__class__,
            instance.pk,
            cleaned,
            company=getattr(instance, "company", None),
        )


class CustomFieldMultiStepMixin(CustomFieldSaveMixin):
    """
    Mixin for HorillaMultiStepForm subclasses. Injects custom fields into
    the last step. Must be prepended to the class's __bases__.
    """

    def __init__(self, *args, **kwargs):
        from django import forms as django_forms

        model = self._meta.model
        custom_fields_map = build_custom_form_fields(model)

        if custom_fields_map:
            original_step_fields = {}
            for klass in type(self).__mro__:
                if klass in (CustomFieldMultiStepMixin, CustomFieldSaveMixin):
                    continue
                step_fields = klass.__dict__.get("step_fields")
                if step_fields:
                    original_step_fields = dict(step_fields)
                    break

            last_step = max(original_step_fields.keys()) if original_step_fields else 1
            new_step_fields = dict(original_step_fields)
            new_step_fields[last_step] = list(
                new_step_fields.get(last_step, [])
            ) + list(custom_fields_map.keys())
            self.step_fields = new_step_fields

        super().__init__(*args, **kwargs)

        if not custom_fields_map:
            return

        current_step = getattr(self, "current_step", 1)
        last_step = max(self.step_fields.keys()) if self.step_fields else 1
        form_data = getattr(self, "form_data", None) or {}
        instance = getattr(self, "instance", None)
        existing_values = {}
        if instance and instance.pk:
            existing_values = load_custom_field_values(model, instance.pk)

        for key, field in custom_fields_map.items():
            val = form_data.get(key)
            if val in (None, ""):
                val = existing_values.get(key)
            if val is not None:
                field.initial = val

            self.fields[key] = field

            if current_step != last_step:
                self.fields[key].required = False
                self.fields[key].widget = django_forms.HiddenInput()
                self._step_hidden_fields.add(key)
            elif val is not None:
                self.initial[key] = val

    def clean(self):
        """
        HorillaMultiStepForm.clean() calls ``model._meta.get_field`` for every
        current-step name and catches ``models.FieldDoesNotExist``, which does
        not exist on ``horilla.db.models``. Extra ``cf_*`` fields would then
        raise ``AttributeError``.

        Strip custom fields from ``step_fields`` before Horilla's ``clean``,
        then restore current-step ``cf_*`` errors that ``_clean_fields`` already
        collected. Horilla sources stay unchanged.
        """
        original_step_fields = self.step_fields
        current_fields = list((original_step_fields or {}).get(self.current_step, []))
        saved_cf_errors = {}
        error_dict = getattr(self, "_errors", None)
        if error_dict:
            for name in current_fields:
                if is_custom_field_name(name) and name in error_dict:
                    saved_cf_errors[name] = error_dict[name]
        try:
            self.step_fields = {
                step: [name for name in fields if not is_custom_field_name(name)]
                for step, fields in (original_step_fields or {}).items()
            }
            cleaned_data = super().clean()
        finally:
            self.step_fields = original_step_fields

        for name, errors in saved_cf_errors.items():
            self._errors[name] = errors
        return cleaned_data


class CustomFieldSingleFormMixin(CustomFieldSaveMixin):
    """
    Mixin for HorillaModelForm subclasses. Injects custom fields and populates
    existing values when editing.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        model = self._meta.model
        custom_fields_map = build_custom_form_fields(model)
        self.fields.update(custom_fields_map)

        instance = getattr(self, "instance", None)
        if instance and instance.pk:
            existing_values = load_custom_field_values(model, instance.pk)
            for key, val in existing_values.items():
                if key in self.fields:
                    self.initial[key] = val


class CustomFieldDetailMixin:
    """
    Merge custom fields into a detail view's ``body`` so they render in the
    header grid and the Details tab. Values are attached on the instance so
    ``display_field_value`` can read them. Fields stay editable (pen icon)
    unless Horilla already marked them non-editable.
    """

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = (
            context.get("obj")
            or context.get("object")
            or getattr(self, "object", None)
        )
        apply_custom_fields_to_detail_context(
            context, obj, request=getattr(self, "request", None), view=self
        )
        return context


def _visibility_field_names(visibility, attr):
    if visibility is None:
        return None
    saved = getattr(visibility, attr, None)
    if not saved:
        return None
    from custom_fields.detail_hooks import field_names_from_list

    return field_names_from_list(saved)


def _detail_visibility_for(request, obj):
    if request is None or not getattr(request, "user", None):
        return None
    if not getattr(obj, "_meta", None):
        return None
    from horilla.contrib.core.models import DetailFieldVisibility
    from horilla.urls import resolve

    url_name = request.GET.get("detail_url_name") or ""
    if not url_name:
        try:
            resolved = resolve(request.path)
            url_name = resolved.url_name if resolved else ""
        except Exception:
            url_name = ""
    return DetailFieldVisibility.all_objects.filter(
        user=request.user,
        app_label=obj._meta.app_label,
        model_name=obj._meta.model_name,
        url_name=url_name,
    ).first()


def merge_custom_fields_into_body(body, ordered_names, definitions, obj, values):
    """
    Rebuild a detail ``body`` list so ``cf_*`` rows follow saved picker order.

    ``ordered_names is None`` means the user has no saved visibility: keep
    model fields and append every custom field. When ``ordered_names`` is a
    list, only custom fields present in that list are shown, at that index.
    """
    model_rows = []
    model_by_name = {}
    for item in body or []:
        name = (
            item[1]
            if isinstance(item, (list, tuple)) and len(item) >= 2
            else item
        )
        name = str(name)
        if is_custom_field_name(name):
            continue
        model_rows.append(item)
        model_by_name[name] = item

    defs_by_key = {custom_field_form_name(defn): defn for defn in definitions}

    def cf_row(defn):
        key = custom_field_form_name(defn)
        value = values.get(key)
        setattr(obj, key, "" if value is None else value)
        return (defn.name, key)

    if ordered_names is None:
        result = list(model_rows)
        for defn in definitions:
            result.append(cf_row(defn))
        return result

    result = []
    for name in ordered_names:
        name = str(name)
        if is_custom_field_name(name):
            defn = defs_by_key.get(name)
            if defn:
                result.append(cf_row(defn))
        elif name in model_by_name:
            result.append(model_by_name[name])
    return result


def apply_custom_fields_to_detail_context(context, obj, request=None, view=None):
    """Add ``(label, cf_<id>)`` rows to context['body'] and set values on obj."""
    if obj is None or not getattr(obj, "pk", None):
        return context

    definitions = list(get_custom_field_definitions(obj.__class__))
    if not definitions:
        return context

    values = load_custom_field_values(obj.__class__, obj.pk)
    visibility = _detail_visibility_for(request, obj)

    from horilla.contrib.generics.views.detail_tabs import HorillaDetailSectionView

    if view is not None and isinstance(view, HorillaDetailSectionView):
        ordered_names = _visibility_field_names(visibility, "details_fields")
    else:
        ordered_names = _visibility_field_names(visibility, "header_fields")

    context["body"] = merge_custom_fields_into_body(
        context.get("body"), ordered_names, definitions, obj, values
    )
    return context
