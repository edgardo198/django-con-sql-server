from django.contrib import admin
from  .models import *
from app.core.user.models import User
# Register your models here.
admin.site.register(User)
admin.site.register(Category)
admin.site.register(Client)
admin.site.register(Sale)
admin.site.register(Product)


