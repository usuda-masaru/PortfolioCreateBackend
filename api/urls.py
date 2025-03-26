from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken.views import obtain_auth_token
from .views import (
    UserProfileViewSet, SkillCategoryViewSet, SkillViewSet, 
    ProjectViewSet, EducationViewSet, WorkExperienceViewSet, 
    ProcessExperienceViewSet, GitHubRepositoryViewSet,
    PublicProfileView, github_oauth_callback, CustomObtainAuthToken,
    register_user, QiitaArticleViewSet
)

router = DefaultRouter()
router.register(r'profiles', UserProfileViewSet, basename='profiles')
router.register(r'skill-categories', SkillCategoryViewSet, basename='skill-categories')
router.register(r'skills', SkillViewSet, basename='skills')
router.register(r'projects', ProjectViewSet, basename='projects')
router.register(r'education', EducationViewSet, basename='education')
router.register(r'work-experiences', WorkExperienceViewSet, basename='work-experiences')
router.register(r'process-experiences', ProcessExperienceViewSet, basename='process-experiences')
router.register(r'github-repositories', GitHubRepositoryViewSet, basename='github-repositories')
router.register(r'qiita-articles', QiitaArticleViewSet, basename='qiita-articles')

urlpatterns = [
    path('', include(router.urls)),
    path('profile/<str:slug>/', PublicProfileView.as_view(), name='public-profile'),
    path('api-token-auth/', CustomObtainAuthToken.as_view(), name='api_token_auth'),
    path('auth/', include('rest_framework.urls')),
    path('oauth/github/callback/', github_oauth_callback, name='github-oauth-callback'),
    path('register/', register_user, name='register'),
] 