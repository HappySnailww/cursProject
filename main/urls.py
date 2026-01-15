from django.urls import include, path
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework.routers import DefaultRouter

from . import views
from .views import (
    CategoryViewSet,
    CommentViewSet,
    TaskViewSet,
)

router = DefaultRouter()
router.register(r"categories", CategoryViewSet, basename="category")
router.register(r"tasks", TaskViewSet, basename="task")
router.register(r"comments", CommentViewSet, basename="comment")

urlpatterns = [
    path("", views.home, name="home"),
    path("tasks/", views.task_list, name="task_list"),
    path("tasks/add/", views.task_add, name="task_add"),
    path("tasks/edit/<int:pk>/", views.task_edit, name="task_edit"),
    path("tasks/delete/<int:pk>/", views.task_delete, name="task_delete"),
    path("tasks/<int:task_id>/comment/add/", views.comment_add, name="comment_add"),
    path("auth/register/", views.register, name="register"),
    path("auth/login/", views.login_view, name="login"),
    path("auth/logout/", views.logout_view, name="logout"),
    path("api/", include(router.urls)),
    path("api/auth/login/", obtain_auth_token, name="api_login"),
]
