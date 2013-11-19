#!/usr/bin/env python
# -*- coding: us-ascii -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
#

import os
import sys

if __name__ == "__main__":
    if sys.version_info < (2, 6, 5):
        # Avoid unhelpful errors https://code.djangoproject.com/ticket/18961
        raise NotImplementedError('Python version is too old (for Django)')
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cah.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
