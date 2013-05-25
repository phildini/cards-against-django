from django.db.models import get_models, get_app
from django.contrib import admin
from django.contrib.admin.sites import AlreadyRegistered


def autoregister(*app_list):
    searchable_fieldnames = ['name', 'text']
    for app_name in app_list:
        app_models = get_app(app_name)
        for model in get_models(app_models):
            # make fields defined in `searchable_fieldnames` searchable
            # in the model admin
            model_admin_name = '%sAdmin' % model.__name__
            field_names = model._meta.get_all_field_names()

            search_fields = []
            for field_name in searchable_fieldnames:
                if field_name in field_names:
                    search_fields.append(field_name)

            if search_fields:
                model_admin = type(model_admin_name, (admin.ModelAdmin,),
                                   {'search_fields': search_fields, })
            else:
                model_admin = None

            try:
                if model_admin:
                    admin.site.register(model, model_admin)
                else:
                    admin.site.register(model)
            except AlreadyRegistered:
                pass


autoregister('cards')
