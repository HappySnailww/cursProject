from rest_framework.routers import DefaultRouter
from .views import CategoryViewSet, TaskViewSet, CommentViewSet

router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'tasks', TaskViewSet, basename='task')
router.register(r'comments', CommentViewSet, basename='comment')

urlpatterns = router.urls