# piano/urls.py

from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
# هذا السطر ليس ضروريًا إذا استخدمنا دالة static()، ولكن لا ضرر من بقائه
from django.views.static import serve as static_serve

# 1. المسارات الأساسية للـ API ولوحة التحكم
urlpatterns = [
    path('admin/', admin.site.urls),
    # Friendly index for the auth root (shows links to login/registration)
    path('auth/', TemplateView.as_view(template_name='auth_index.html'), name='auth-home'),
    path('api/', include('users.urls')),
    path('auth/', include('dj_rest_auth.urls')),
    path('auth/registration/', include('dj_rest_auth.registration.urls')),
    path('accounts/', include('allauth.urls')),
]

# 2. إضافة مسارات خدمة ملفات الميديا (هذا هو التعديل الأهم)
# يجب أن يأتي هذا الجزء *قبل* مسار اصطياد الكل
if settings.DEBUG:
    # Provide a friendly index for the media root (so GET /media/ doesn't show the static.serve 404)
    urlpatterns += [
        path('media/', TemplateView.as_view(template_name='media_index.html'), name='media-home'),
    ]
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# 3. مسار اصطياد الكل لخدمة الواجهة الأمامية يأتي في النهاية
urlpatterns += [
    re_path(r'^(?!admin|api|auth|accounts|media).*$', TemplateView.as_view(template_name='index.html'), name='home'),
]
# ملاحظة: أضفت 'media' إلى القائمة المستبعدة كإجراء احترازي إضافي.