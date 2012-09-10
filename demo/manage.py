#!/usr/bin/env python
import os
import sys

# Set this directory's root on the path
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "demo.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
