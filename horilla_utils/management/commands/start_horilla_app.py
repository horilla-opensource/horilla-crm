"""
Custom Django management command to build an app with additional files and folders,
and automatically configure URLs and settings.

Usage:
    python manage.py build_app app_name
"""

import os
import re
import shutil

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Creates a Django app with additional files and directories and auto-configures it"

    def add_arguments(self, parser):
        parser.add_argument("app_name", type=str, help="Name of the application")
        parser.add_argument(
            "--directory", "-d", dest="directory", help="Optional destination directory"
        )
        parser.add_argument(
            "--project",
            "-p",
            dest="project_name",
            help="Project name for URL configuration (default: derived from settings)",
        )

    def handle(self, *args, **options):
        app_name = options["app_name"]
        directory = options["directory"]
        project_name = "horilla"

        # If no project name specified, try to get it from settings module
        if not project_name:
            project_name = os.path.basename(settings.BASE_DIR)

        # If no directory specified, create the app in the current directory
        target_dir = os.path.join(directory, app_name) if directory else app_name

        self.stdout.write(f"Creating Horilla app '{app_name}'...")

        try:
            # Check if the app name is valid
            if not re.match(r"^[_a-zA-Z]\w*$", app_name):
                raise CommandError(
                    f"'{app_name}' is not a valid app name. It must start with a letter or underscore and contain only letters, numbers, and underscores."
                )

            # Create the app directory
            os.makedirs(target_dir, exist_ok=True)

            # Create basic app structure
            self._create_base_app_structure(app_name, target_dir, project_name)

            # Create additional files
            self._create_additional_files(app_name, target_dir)

            # Create templates directory
            self._create_templates_directory(target_dir)

            # Create templatetags directory
            self._create_templatetags_directory(target_dir)

            # Create static directory
            self._create_static_directory(target_dir, app_name)

        except Exception as e:
            self.stderr.write(f"Error creating app: {str(e)}")
            # Clean up if there was an error
            if os.path.exists(target_dir):
                shutil.rmtree(target_dir)
            return

        # Final success message
        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully built app '{app_name}' with extended structure!"
            )
        )

    def _create_base_app_structure(self, app_name, target_dir, project_name):
        """Create the basic Django app structure"""

        # __init__.py
        with open(os.path.join(target_dir, "__init__.py"), "w") as f:
            f.write(f'"""\nPackage initialization for the {app_name} app\n"""\n\n')

        # apps.py
        with open(os.path.join(target_dir, "apps.py"), "w") as f:
            f.write(
                f'"""\nAppConfig for the {app_name} app\n"""\n\n'
                "from django.apps import AppConfig\n"
                "from django.utils.translation import gettext_lazy as _\n\n"
                f"class {app_name.capitalize()}Config(AppConfig):\n"
                f'    """App configuration class for {app_name}."""\n'
                "    default_auto_field = 'django.db.models.BigAutoField'\n"
                f"    name = '{app_name}'\n"
                f"    verbose_name = _('{app_name.title()}')\n\n"
                "    def ready(self):\n"
                '        """Run app initialization logic (executed after Django setup).\n'
                "        Used to auto-register URLs and connect signals if required.\n"
                '        """\n'
                "        try:\n"
                "            # Auto-register this app's URLs and add to installed apps\n"
                "            from django.urls import include, path\n"
                f"            from {project_name}.urls import urlpatterns\n\n"
                "            # Add app URLs to main urlpatterns\n"
                f"            urlpatterns.append(\n"
                f"                path('{app_name}/', include('{app_name}.urls')),\n"
                "            )\n"
                "        except Exception as e:\n"
                "            import logging\n"
                f'            logging.warning(f"{app_name.capitalize()}Config.ready failed: {{e}}")\n'
                "            pass\n\n"
                "        super().ready()\n"
            )

        # models.py
        with open(os.path.join(target_dir, "models.py"), "w") as f:
            f.write(
                f'"""\nModels for the {app_name} app\n"""\n\n'
                "from django.db import models\n\n"
                f"# Create your {app_name} models here.\n"
            )

        # views.py
        with open(os.path.join(target_dir, "views.py"), "w") as f:
            f.write(
                f'"""\nViews for the {app_name} app\n"""\n\n'
                "from django.shortcuts import render\n"
            )

        # admin.py
        with open(os.path.join(target_dir, "admin.py"), "w") as f:
            f.write(
                f'"""\nAdmin registration for the {app_name} app\n"""\n\n'
                "from django.contrib import admin\n\n"
                f"# Register your {app_name} models here.\n"
            )

        # tests.py
        with open(os.path.join(target_dir, "tests.py"), "w") as f:
            f.write(
                f'"""\nTests for the {app_name} app\n"""\n\n'
                "from django.test import TestCase\n\n"
                f"# Create your {app_name} tests here.\n"
            )

        # migrations directory
        migrations_dir = os.path.join(target_dir, "migrations")
        os.makedirs(migrations_dir, exist_ok=True)
        with open(os.path.join(migrations_dir, "__init__.py"), "w") as f:
            f.write('"""\nMigration package for the {app_name} app\n"""\n')

    def _create_additional_files(self, app_name, target_dir):
        """Create additional Python files for the app"""
        additional_files = {
            "scheduler.py": (
                f'"""\nScheduler for the {app_name} app\n"""\n\n'
                f"# Define your {app_name} scheduled tasks here\n"
            ),
            "signals.py": (
                f'"""\nSignals for the {app_name} app\n"""\n\n'
                "from django.db.models.signals import pre_save, post_save\n"
                "from django.dispatch import receiver\n\n"
                f"# Define your {app_name} signals here\n"
            ),
            "filters.py": (
                f'"""\nFilters for the {app_name} app\n"""\n\n'
                "import django_filters\n\n"
                f"# Define your {app_name} filters here\n"
            ),
            "forms.py": (
                f'"""\nForms for the {app_name} app\n"""\n\n'
                "from django import forms\n\n"
                f"# Define your {app_name} forms here\n"
            ),
            "urls.py": (
                f'"""\nURLs for the {app_name} app\n"""\n\n'
                "from django.urls import path\n"
                "from . import views\n\n"
                f"app_name = '{app_name}'\n\n"
                "urlpatterns = [\n"
                "    # Define your URL patterns here\n"
                "]\n"
            ),
            "menu.py": (
                f'"""\nThis module registers Floating, Settings, My Settings, and Main Section menus\n'
                f'for the {app_name} app\n"""\n\n'
                "from django.urls import reverse_lazy\n"
                "from django.utils.translation import gettext_lazy as _\n\n"
                "from horilla.menu import (\n"
                "    floating_menu,\n"
                "    main_section_menu,\n"
                "    sub_section_menu,\n"
                "    settings_menu,\n"
                "    my_settings_menu,\n"
                ")\n"
                "# Define your menu registration logic here\n"
            ),
        }

        for file_name, content in additional_files.items():
            file_path = os.path.join(target_dir, file_name)
            with open(file_path, "w") as f:
                f.write(content)
            self.stdout.write(f"  Created {file_name}")

    def _create_templates_directory(self, target_dir):
        """Create templates directory directly in the app"""
        templates_dir = os.path.join(target_dir, "templates")

        os.makedirs(templates_dir, exist_ok=True)
        self.stdout.write("Created templates/ directory")

    def _create_static_directory(self, target_dir, app_name):
        """
        Create static directory for a Django app with namespacing,
        including assets/icons and assets/js folders.

        Args:
            target_dir (str): Path to the app folder
            app_name (str): Django app name to use as namespace
        """
        static_dir = os.path.join(target_dir, "static", app_name)

        icons_dir = os.path.join(static_dir, "assets", "icons")
        js_dir = os.path.join(static_dir, "assets", "js")

        for folder in [icons_dir, js_dir]:
            os.makedirs(folder, exist_ok=True)
        self.stdout.write(
            "Created static/ directory with assets/icons/ assets/js subfolders"
        )

    def _create_templatetags_directory(self, target_dir):
        """Create templatetags directory with init and custom tags file"""
        templatetags_dir = os.path.join(target_dir, "templatetags")
        os.makedirs(templatetags_dir, exist_ok=True)

        # Create __init__.py
        with open(os.path.join(templatetags_dir, "__init__.py"), "w") as f:
            f.write("")

        # Create custom tags file

        self.stdout.write(
            "Created templatetags/ directory with __init__.py and custom tags file"
        )
