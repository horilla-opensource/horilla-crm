from django.contrib.auth.mixins import LoginRequiredMixin

from horilla_core.models import RecentlyViewed


class RecentlyViewedMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        if hasattr(self, "object") and self.object and request.user.is_authenticated:
            RecentlyViewed.objects.add_viewed_item(request.user, self.object)
        return response
