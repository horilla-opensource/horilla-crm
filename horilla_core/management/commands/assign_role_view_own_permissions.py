# In horilla_core/management/commands/assign_role_view_own_permissions.py

from django.contrib.auth.models import Permission
from django.core.management.base import BaseCommand

from horilla_core.models import Role


class Command(BaseCommand):
    help = "Assign view_own permissions to all existing roles and their members"

    def add_arguments(self, parser):
        parser.add_argument(
            "--role-id",
            type=int,
            help="Assign permissions to a specific role by ID",
        )

    def handle(self, *args, **options):
        view_own_perms = Permission.objects.filter(codename__startswith="view_own_")

        if not view_own_perms.exists():
            self.stdout.write(self.style.WARNING("No view_own permissions found!"))
            return

        if options["role_id"]:
            roles = Role.objects.filter(id=options["role_id"])
            if not roles.exists():
                self.stdout.write(
                    self.style.ERROR(f'Role with ID {options["role_id"]} not found!')
                )
                return
        else:
            roles = Role.objects.all()

        total_roles_updated = 0
        total_users_updated = 0

        for role in roles:
            existing_perm_ids = set(role.permissions.values_list("id", flat=True))

            view_own_perm_ids = set(view_own_perms.values_list("id", flat=True))

            missing_perm_ids = view_own_perm_ids - existing_perm_ids

            if missing_perm_ids:
                missing_perms = Permission.objects.filter(id__in=missing_perm_ids)

                role.permissions.add(*missing_perms)
                total_roles_updated += 1

                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ Added {len(missing_perm_ids)} permissions to role "{role.role_name}"'
                    )
                )

                members = role.users.all()
                for member in members:
                    user_existing_perms = set(
                        member.user_permissions.values_list("id", flat=True)
                    )
                    user_missing_perms = missing_perm_ids - user_existing_perms

                    if user_missing_perms:
                        user_perms_to_add = Permission.objects.filter(
                            id__in=user_missing_perms
                        )
                        member.user_permissions.add(*user_perms_to_add)
                        total_users_updated += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'  ✓ Added {len(user_missing_perms)} permissions to user "{member.username}"'
                            )
                        )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f'⊘ Role "{role.role_name}" already has all view_own permissions'
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✓ Summary: Updated {total_roles_updated} roles and {total_users_updated} users"
            )
        )
