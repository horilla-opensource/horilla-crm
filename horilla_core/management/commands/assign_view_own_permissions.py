from django.contrib.auth.models import Permission
from django.core.management.base import BaseCommand

from horilla_core.models import HorillaUser


class Command(BaseCommand):
    help = "Assign view_own permissions to all existing non-superuser users"

    def handle(self, *args, **options):
        users = HorillaUser.objects.filter(is_superuser=False)
        view_own_perms = Permission.objects.filter(codename__startswith="view_own_")

        if not view_own_perms.exists():
            self.stdout.write(self.style.WARNING("No view_own permissions found!"))
            return

        count = 0
        for user in users:
            existing_perm_ids = set(user.user_permissions.values_list("id", flat=True))
            view_own_perm_ids = set(view_own_perms.values_list("id", flat=True))
            missing_perm_ids = view_own_perm_ids - existing_perm_ids

            if missing_perm_ids:
                missing_perms = Permission.objects.filter(id__in=missing_perm_ids)
                user.user_permissions.add(*missing_perms)
                count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ Added {len(missing_perm_ids)} permissions to {user.username}"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nTotal: Updated {count} users with view_own permissions"
            )
        )
