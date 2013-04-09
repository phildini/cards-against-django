
from django.db import models
from django.contrib import admin

import cards.models

# Auto register all class models
def auto_register_admin(model_module):
    module_name = model_module.__name__
    for tmp_name in dir(model_module):
        tmp_obj = getattr(model_module, tmp_name)
        if isinstance(tmp_obj, models.base.ModelBase) and tmp_obj.__module__ == module_name:  # models.Model doesnt work (tested Django 1.2 and 1.5.1)
            tmp_admin_obj = globals().get(tmp_name + 'Admin')
            if tmp_admin_obj:
                admin.site.register(tmp_obj, tmp_admin_obj)
            else:
                admin.site.register(tmp_obj)

# There may be a better way than this but this works for me :-)
auto_register_admin(cards.models)
