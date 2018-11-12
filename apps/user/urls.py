from django.conf.urls import include, url
from apps.user import views
from user.views import RegisterView,ActiveView,LoginView

urlpatterns = [
    url(r'^register$', RegisterView.as_view(), name='register'),  # 注册
    url(r'^active/(?P<token>.*)$',ActiveView.as_view(), name='active'),
    url(r'^login$', LoginView.as_view(), name='login'),
]
