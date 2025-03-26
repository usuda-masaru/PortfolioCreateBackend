from django.shortcuts import render
from rest_framework import viewsets, permissions, status, generics
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly, AllowAny
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.db.models import Prefetch
import requests
import json
from datetime import datetime
from django.conf import settings
from django.http import HttpResponseRedirect
from rest_framework.views import APIView
from django.views.decorators.csrf import csrf_exempt
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token

from .models import UserProfile, SkillCategory, Skill, Project, Education, WorkExperience, ProcessExperience, GitHubRepository, GitHubCommitStats, generate_unique_portfolio_id, QiitaArticle
from .serializers import (
    UserSerializer, UserProfileSerializer, UserProfilePublicSerializer,
    SkillCategorySerializer, SkillSerializer, ProjectSerializer,
    EducationSerializer, WorkExperienceSerializer, ProcessExperienceSerializer,
    GitHubRepositorySerializer, GitHubCommitStatsSerializer, QiitaArticleSerializer
)
from .permissions import IsOwnerOrReadOnly

# ユーザー登録API
@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):
    """
    新規ユーザー登録API
    """
    if request.method == 'POST':
        user_data = {
            'username': request.data.get('username', '').strip(),
            'email': request.data.get('email', '').strip(),
            'password': request.data.get('password', '').strip()
        }
        
        errors = {}
        
        # バリデーション
        if not user_data['username']:
            errors['username'] = 'ユーザー名は必須です'
        elif len(user_data['username']) < 3:
            errors['username'] = 'ユーザー名は3文字以上で入力してください'
        elif User.objects.filter(username=user_data['username']).exists():
            errors['username'] = 'このユーザー名は既に使用されています'
            
        if not user_data['email']:
            errors['email'] = 'メールアドレスは必須です'
        elif User.objects.filter(email=user_data['email']).exists():
            errors['email'] = 'このメールアドレスは既に登録されています'
            
        if not user_data['password']:
            errors['password'] = 'パスワードは必須です'
        elif len(user_data['password']) < 8:
            errors['password'] = 'パスワードは8文字以上で入力してください'
            
        if errors:
            return Response({'error': errors}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # ユーザー作成
            user = User.objects.create_user(
                username=user_data['username'],
                email=user_data['email'],
                password=user_data['password']
            )
            
            # プロフィール作成
            UserProfile.objects.create(
                user=user,
                display_name=user.username,
                title="",
                portfolio_slug=generate_unique_portfolio_id()
            )
            
            # トークン生成
            token, created = Token.objects.get_or_create(user=user)
            
            return Response({
                'token': token.key,
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email
                }
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({
                'error': {
                    'message': '登録処理中にエラーが発生しました',
                    'detail': str(e)
                }
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class UserProfileViewSet(viewsets.ModelViewSet):
    """
    ユーザープロフィールのViewSet
    """
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
    
    def get_queryset(self):
        if self.request.user.is_staff:
            return UserProfile.objects.all()
        return UserProfile.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
        
    @action(detail=False, methods=['get'])
    def me(self, request):
        """現在ログインしているユーザーのプロフィールを取得"""
        profile, created = UserProfile.objects.get_or_create(
            user=request.user,
            defaults={
                'display_name': request.user.get_full_name() or request.user.username,
                'portfolio_slug': generate_unique_portfolio_id()
            }
        )
        serializer = self.get_serializer(profile)
        return Response(serializer.data)

class PublicProfileView(generics.RetrieveAPIView):
    """
    公開プロフィールビュー（認証不要）
    """
    serializer_class = UserProfilePublicSerializer
    permission_classes = [AllowAny]
    lookup_field = 'portfolio_slug'
    lookup_url_kwarg = 'slug'
    
    def get_queryset(self):
        return UserProfile.objects.all().prefetch_related(
            'skills__category',
            'projects__technologies_used',
            'education',
            'work_experiences__skills_used',
            'process_experiences'
        )

class SkillCategoryViewSet(viewsets.ModelViewSet):
    """
    スキルカテゴリのViewSet
    """
    serializer_class = SkillCategorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return SkillCategory.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response(
                {'error': 'カテゴリの削除に失敗しました。このカテゴリに属するスキルが存在する可能性があります。'},
                status=status.HTTP_400_BAD_REQUEST
            )

class SkillViewSet(viewsets.ModelViewSet):
    """
    スキルのViewSet
    """
    serializer_class = SkillSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
    
    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Skill.objects.all()
        try:
            profile = UserProfile.objects.get(user=user)
            return Skill.objects.filter(profile=profile)
        except UserProfile.DoesNotExist:
            return Skill.objects.none()
    
    def perform_create(self, serializer):
        profile, created = UserProfile.objects.get_or_create(
            user=self.request.user,
            defaults={
                'display_name': self.request.user.get_full_name() or self.request.user.username,
                'portfolio_slug': generate_unique_portfolio_id()
            }
        )
        serializer.save(user=profile)

    @action(detail=True, methods=['post'])
    def set_icon(self, request, pk=None):
        """アイコンIDを設定するカスタムエンドポイント"""
        skill = self.get_object()
        
        # リクエストからアイコンIDを取得
        icon_id = request.data.get('icon_id')
        if not icon_id:
            return Response({'error': 'icon_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # アイコンIDをスキルに設定
        skill.icon = icon_id
        skill.save()
        
        # 更新されたスキルを返す
        serializer = self.get_serializer(skill)
        return Response(serializer.data)

class ProcessExperienceViewSet(viewsets.ModelViewSet):
    """
    担当工程経験のViewSet
    """
    serializer_class = ProcessExperienceSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
    
    def get_queryset(self):
        if self.request.user.is_staff:
            return ProcessExperience.objects.all()
        
        try:
            profile = UserProfile.objects.get(user=self.request.user)
            return ProcessExperience.objects.filter(user=profile)
        except UserProfile.DoesNotExist:
            return ProcessExperience.objects.none()
    
    def perform_create(self, serializer):
        profile, created = UserProfile.objects.get_or_create(
            user=self.request.user,
            defaults={
                'display_name': self.request.user.get_full_name() or self.request.user.username,
                'portfolio_slug': generate_unique_portfolio_id()
            }
        )
        serializer.save(user=profile)
        
    @action(detail=False, methods=['post'], url_path='bulk-update')
    def bulk_update(self, request):
        """複数の担当工程経験を一括更新するカスタムエンドポイント"""
        process_experiences = request.data.get('process_experiences', [])
        if not process_experiences or not isinstance(process_experiences, list):
            return Response({'error': 'process_experiences list is required'}, 
                           status=status.HTTP_400_BAD_REQUEST)
        
        profile, created = UserProfile.objects.get_or_create(
            user=self.request.user,
            defaults={
                'display_name': self.request.user.get_full_name() or self.request.user.username,
                'portfolio_slug': generate_unique_portfolio_id()
            }
        )
        
        updated_experiences = []
        
        for exp_data in process_experiences:
            process_type = exp_data.get('process_type')
            if not process_type:
                continue
                
            experience_count = exp_data.get('experience_count', 0)
            description = exp_data.get('description', '')
            
            # 既存のレコードを更新または新規作成
            exp, created = ProcessExperience.objects.update_or_create(
                user=profile,
                process_type=process_type,
                defaults={
                    'experience_count': experience_count,
                    'description': description
                }
            )
            
            updated_experiences.append(self.get_serializer(exp).data)
        
        return Response({
            'message': f'{len(updated_experiences)} process experiences updated',
            'process_experiences': updated_experiences
        })

class ProjectViewSet(viewsets.ModelViewSet):
    """
    プロジェクトのViewSet
    """
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
    
    def get_queryset(self):
        if self.request.user.is_staff:
            return Project.objects.all()
        
        try:
            profile = UserProfile.objects.get(user=self.request.user)
            return Project.objects.filter(user=profile)
        except UserProfile.DoesNotExist:
            return Project.objects.none()
    
    def perform_create(self, serializer):
        profile, created = UserProfile.objects.get_or_create(
            user=self.request.user,
            defaults={
                'display_name': self.request.user.get_full_name() or self.request.user.username,
                'portfolio_slug': generate_unique_portfolio_id()
            }
        )
        serializer.save(user=profile)

class EducationViewSet(viewsets.ModelViewSet):
    """
    学歴のViewSet
    """
    serializer_class = EducationSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
    
    def get_queryset(self):
        if self.request.user.is_staff:
            return Education.objects.all()
        
        try:
            profile = UserProfile.objects.get(user=self.request.user)
            return Education.objects.filter(user=profile)
        except UserProfile.DoesNotExist:
            return Education.objects.none()
    
    def perform_create(self, serializer):
        profile, created = UserProfile.objects.get_or_create(
            user=self.request.user,
            defaults={
                'display_name': self.request.user.get_full_name() or self.request.user.username,
                'portfolio_slug': generate_unique_portfolio_id()
            }
        )
        serializer.save(user=profile)

class WorkExperienceViewSet(viewsets.ModelViewSet):
    """
    職歴のViewSet
    """
    serializer_class = WorkExperienceSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
    
    def get_queryset(self):
        if self.request.user.is_staff:
            return WorkExperience.objects.all()
        
        try:
            profile = UserProfile.objects.get(user=self.request.user)
            return WorkExperience.objects.filter(user=profile)
        except UserProfile.DoesNotExist:
            return WorkExperience.objects.none()
    
    def perform_create(self, serializer):
        profile, created = UserProfile.objects.get_or_create(
            user=self.request.user,
            defaults={
                'display_name': self.request.user.get_full_name() or self.request.user.username,
                'portfolio_slug': generate_unique_portfolio_id()
            }
        )
        serializer.save(user=profile)

class GitHubRepositoryViewSet(viewsets.ModelViewSet):
    """GitHubリポジトリを管理するViewSet"""
    serializer_class = GitHubRepositorySerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]

    def get_queryset(self):
        user_profile = get_object_or_404(UserProfile, user=self.request.user)
        return GitHubRepository.objects.filter(user=user_profile)
    
    @action(detail=False, methods=['post'])
    def sync(self, request):
        """GitHubからリポジトリ情報を同期する"""
        print("===== GitHub同期処理を開始 =====")
        user_profile = get_object_or_404(UserProfile, user=request.user)
        
        print(f"ユーザープロフィール情報: ID={user_profile.id}, ユーザー名={user_profile.user.username}")
        print(f"GitHub設定: github_username={user_profile.github_username}, access_token={bool(user_profile.github_access_token)}")
        print(f"GitHub OAuth: client_id={bool(user_profile.github_client_id)}, client_secret={bool(user_profile.github_client_secret)}")
        
        # GitHubのユーザー名がない場合はエラー
        if not user_profile.github_username:
            print("エラー: GitHubユーザー名が設定されていません")
            return Response(
                {"error": "GitHubユーザー名が設定されていません。プロフィール設定画面で設定してください。"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # GitHubアクセストークンがあれば認証付きで、なければ認証なしで
        headers = {}
        if user_profile.github_access_token:
            headers["Authorization"] = f"token {user_profile.github_access_token}"
            print(f"GitHub API認証: Authorizationヘッダーを設定しました")
        else:
            print("警告: GitHub APIの認証なしでリクエストを実行します（レート制限あり）")
        
        github_username = user_profile.github_username
        
        try:
            # GitHubユーザー情報を取得
            user_url = f"https://api.github.com/users/{github_username}"
            print(f"GitHub APIリクエスト: {user_url}")
            user_response = requests.get(user_url, headers=headers)
            print(f"GitHub APIレスポンス (ユーザー情報): status={user_response.status_code}")
            
            if user_response.status_code != 200:
                print(f"エラー: GitHubユーザー情報の取得に失敗: {user_response.text}")
                return Response(
                    {"error": f"GitHubユーザー情報の取得に失敗しました: {user_response.text}"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            user_response.raise_for_status()
            user_data = user_response.json()
            print(f"GitHubユーザー情報: login={user_data.get('login')}, name={user_data.get('name')}, public_repos={user_data.get('public_repos')}")
            
            # リポジトリ一覧を取得
            repos_url = f"https://api.github.com/users/{github_username}/repos?per_page=100"
            print(f"GitHub APIリクエスト: {repos_url}")
            repos_response = requests.get(repos_url, headers=headers)
            print(f"GitHub APIレスポンス (リポジトリ一覧): status={repos_response.status_code}")
            
            if repos_response.status_code != 200:
                print(f"エラー: GitHubリポジトリ一覧の取得に失敗: {repos_response.text}")
                return Response(
                    {"error": f"GitHubリポジトリ一覧の取得に失敗しました: {repos_response.text}"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            repos_response.raise_for_status()
            repos_data = repos_response.json()
            print(f"取得したリポジトリ数: {len(repos_data)}")
            
            if len(repos_data) == 0:
                print("警告: リポジトリが0件でした")
            else:
                # サンプルとして最初の1件だけ詳細を表示
                sample_repo = repos_data[0]
                print(f"サンプルリポジトリ: name={sample_repo.get('name')}, full_name={sample_repo.get('full_name')}, private={sample_repo.get('private')}")
            
            # 既存のリポジトリIDリスト（同期後に不要なものを削除するため）
            existing_repos = list(GitHubRepository.objects.filter(
                user=user_profile
            ).values_list('full_name', flat=True))
            print(f"DB上の既存リポジトリ数: {len(existing_repos)}")
            
            synced_repos = []
            
            # 各リポジトリを処理
            for repo_data in repos_data:
                print(f"リポジトリを処理中: {repo_data.get('full_name')}")
                # リポジトリの言語を取得
                languages_url = repo_data.get('languages_url')
                languages_data = {}
                
                if languages_url:
                    languages_response = requests.get(languages_url, headers=headers)
                    if languages_response.status_code == 200:
                        languages_data = languages_response.json()
                        print(f"  言語情報: {list(languages_data.keys())[:5]}")
                    else:
                        print(f"  警告: 言語情報の取得に失敗: status={languages_response.status_code}")
                
                # トピックを取得（GitHubAPIv3では別エンドポイントが必要）
                topics = []
                topics_url = f"https://api.github.com/repos/{repo_data['full_name']}/topics"
                topics_headers = headers.copy()
                topics_headers["Accept"] = "application/vnd.github.mercy-preview+json"
                
                topics_response = requests.get(topics_url, headers=topics_headers)
                if topics_response.status_code == 200:
                    topics_data = topics_response.json()
                    topics = topics_data.get('names', [])
                    print(f"  トピック: {topics[:5]}")
                else:
                    print(f"  警告: トピック情報の取得に失敗: status={topics_response.status_code}")
                
                try:
                    # DBに保存または更新
                    repo, created = GitHubRepository.objects.update_or_create(
                        user=user_profile,
                        full_name=repo_data['full_name'],
                        defaults={
                            'name': repo_data['name'],
                            'html_url': repo_data['html_url'],
                            'description': repo_data['description'] or '',
                            'language': repo_data['language'] or '',
                            'stargazers_count': repo_data['stargazers_count'],
                            'forks_count': repo_data['forks_count'],
                            'open_issues_count': repo_data['open_issues_count'],
                            'watchers_count': repo_data['watchers_count'],
                            'created_at': datetime.strptime(repo_data['created_at'], '%Y-%m-%dT%H:%M:%SZ'),
                            'updated_at': datetime.strptime(repo_data['updated_at'], '%Y-%m-%dT%H:%M:%SZ'),
                            'pushed_at': datetime.strptime(repo_data['pushed_at'], '%Y-%m-%dT%H:%M:%SZ') if repo_data['pushed_at'] else None,
                            'topics': topics,
                            'is_fork': repo_data['fork'],
                            'is_private': repo_data['private'],
                        }
                    )
                    print(f"  DB保存結果: {'作成' if created else '更新'}")
                    synced_repos.append(repo_data['full_name'])
                except Exception as e:
                    print(f"  エラー: リポジトリのDB保存中に例外発生: {str(e)}")
            
            # 同期されなかったリポジトリを削除（リモートで削除された場合）
            deleted_count = 0
            for repo_name in existing_repos:
                if repo_name not in synced_repos:
                    GitHubRepository.objects.filter(
                        user=user_profile, 
                        full_name=repo_name
                    ).delete()
                    deleted_count += 1
            
            print(f"削除されたリポジトリ数: {deleted_count}")
            
            # コミット統計情報を取得・更新
            print("コミット統計情報の同期を開始")
            stats = self._sync_commit_stats(user_profile, headers)
            print(f"コミット統計情報の同期完了: {bool(stats)}")
            
            print(f"===== GitHub同期処理が完了: 同期リポジトリ数={len(synced_repos)} =====")
            return Response({
                "message": "GitHubリポジトリを同期しました",
                "repository_count": len(synced_repos)
            })
            
        except requests.exceptions.RequestException as e:
            print(f"エラー: GitHub API呼び出し中に例外発生: {str(e)}")
            return Response(
                {"error": f"GitHubAPIの呼び出し中にエラーが発生しました: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as e:
            print(f"エラー: 予期せぬ例外が発生: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return Response(
                {"error": f"予期せぬエラーが発生しました: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _sync_commit_stats(self, user_profile, headers):
        """コミット統計情報を同期する内部メソッド"""
        github_username = user_profile.github_username
        
        try:
            # 貢献度グラフ用のデータを取得（GitHub API v3では取得できないため、別方法が必要）
            current_year = datetime.now().year
            year_stats = {}
            
            # ユーザーの総コミット数を概算（上限あり）
            search_commits_url = f"https://api.github.com/search/commits?q=author:{github_username}"
            search_headers = headers.copy()
            search_headers["Accept"] = "application/vnd.github.cloak-preview+json"
            
            commits_response = requests.get(search_commits_url, headers=search_headers)
            total_commits = 0
            
            if commits_response.status_code == 200:
                commits_data = commits_response.json()
                total_commits = commits_data.get('total_count', 0)
            
            # 言語使用統計を計算
            repos = GitHubRepository.objects.filter(user=user_profile, is_fork=False)
            languages_count = {}
            
            for repo in repos:
                if repo.language and repo.language not in ['', 'null', 'None']:
                    if repo.language in languages_count:
                        languages_count[repo.language] += 1
                    else:
                        languages_count[repo.language] = 1
            
            # 月別コントリビューション（簡易的な実装）
            monthly_contributions = {
                '01': 0, '02': 0, '03': 0, '04': 0, '05': 0, '06': 0,
                '07': 0, '08': 0, '09': 0, '10': 0, '11': 0, '12': 0
            }
            
            # 統計情報をDBに保存
            github_stats, created = GitHubCommitStats.objects.update_or_create(
                user=user_profile,
                defaults={
                    'commit_count_total': total_commits,
                    'commit_count_last_year': min(total_commits, 1000),  # 概算
                    'contributions_by_month': monthly_contributions,
                    'languages_used': languages_count
                }
            )
            
            return github_stats
            
        except Exception as e:
            # エラーがあっても処理は続行（ログに記録）
            print(f"コミット統計の同期中にエラー: {str(e)}")
            return None
    
    @action(detail=True, methods=['patch'])
    def toggle_featured(self, request, pk=None):
        """リポジトリの特集フラグを切り替える"""
        repo = self.get_object()
        repo.featured = not repo.featured
        repo.save()
        
        serializer = self.get_serializer(repo)
        return Response(serializer.data)

# CSRF保護を無効化したトークン認証ビュー
class CustomObtainAuthToken(ObtainAuthToken):
    """
    CSRF保護を無効化したトークン認証ビュー
    """
    @csrf_exempt
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

# GitHub OAuth認証のコールバックビュー
@api_view(['GET'])
@permission_classes([AllowAny])
def github_oauth_callback(request):
    """GitHub OAuth認証のコールバック処理"""
    print("===== GitHub OAuth コールバック処理を開始 =====")
    code = request.GET.get('code')
    state = request.GET.get('state')
    
    print(f"リクエストパラメータ: code={bool(code)}, state={state}")
    
    if not code:
        print("エラー: 認証コードがありません")
        return HttpResponseRedirect(f"{settings.FRONTEND_URL}/dashboard/github?error=no_code")
    
    # StateはCSRF対策として確認すべきだが、本実装では簡略化
    
    # トークンの取得先ユーザーを特定（state引数からユーザーIDを取得する想定）
    try:
        # ユーザー情報を取得
        token_url = 'https://github.com/login/oauth/access_token'
        
        # まずトークンを付与されるユーザーのプロフィールを取得
        user_profile = None
        if state and state.isdigit():
            user_id = int(state)
            print(f"ユーザーID: {user_id}")
            try:
                user_profile = UserProfile.objects.get(user_id=user_id)
                print(f"ユーザープロフィール取得: id={user_profile.id}, github_username={user_profile.github_username}")
            except UserProfile.DoesNotExist:
                print(f"エラー: ユーザーID {user_id} のプロフィールが見つかりません")
                return HttpResponseRedirect(f"{settings.FRONTEND_URL}/dashboard/github?error=invalid_user")
        else:
            print(f"警告: ステートパラメータが数値ではありません: {state}")
        
        # ユーザープロフィールが取得できない場合はデフォルト値を使用
        client_id = user_profile.github_client_id if user_profile and user_profile.github_client_id else settings.GITHUB_CLIENT_ID
        client_secret = user_profile.github_client_secret if user_profile and user_profile.github_client_secret else settings.GITHUB_CLIENT_SECRET
        
        print(f"GitHub OAuth認証情報: client_id={client_id[:5]}..., client_secret設定済み={bool(client_secret)}")
        
        # GitHubからアクセストークンを取得
        print(f"GitHub APIリクエスト: {token_url}")
        response = requests.post(
            token_url,
            data={
                'client_id': client_id,
                'client_secret': client_secret,
                'code': code,
            },
            headers={'Accept': 'application/json'}
        )
        
        print(f"GitHub APIレスポンス (トークン): status={response.status_code}")
        
        if response.status_code != 200:
            print(f"エラー: GitHubからのトークン取得に失敗: {response.text}")
            return HttpResponseRedirect(f"{settings.FRONTEND_URL}/dashboard/github?error=token_error")
        
        token_data = response.json()
        print(f"トークンレスポンス: {list(token_data.keys())}")
        
        access_token = token_data.get('access_token')
        
        if not access_token:
            print("エラー: アクセストークンがレスポンスに含まれていません")
            return HttpResponseRedirect(f"{settings.FRONTEND_URL}/dashboard/github?error=no_token")
        
        print(f"アクセストークン取得成功: {access_token[:5]}...")
        
        # ユーザー情報を取得してユーザー名を設定
        if access_token:
            user_url = "https://api.github.com/user"
            print(f"GitHub APIリクエスト (ユーザー情報): {user_url}")
            user_response = requests.get(
                user_url,
                headers={"Authorization": f"token {access_token}"}
            )
            
            print(f"GitHub APIレスポンス (ユーザー情報): status={user_response.status_code}")
            
            if user_response.status_code == 200:
                user_data = user_response.json()
                github_username = user_data.get('login')
                print(f"GitHub ユーザー情報: login={github_username}, name={user_data.get('name')}")
                
                if github_username and user_profile:
                    user_profile.github_username = github_username
                    print(f"GitHubユーザー名を設定: {github_username}")
                
        # アクセストークンを保存（stateからユーザーを特定しない場合は現在のリクエストユーザーに保存）
        if user_profile:
            user_profile.github_access_token = access_token
            user_profile.save()
            print(f"プロフィール保存完了: github_access_token={bool(user_profile.github_access_token)}")
            
            # 成功したらフロントエンドにリダイレクト
            print("===== GitHub OAuth コールバック処理が成功 =====")
            return HttpResponseRedirect(f"{settings.FRONTEND_URL}/dashboard/github?success=true")
        else:
            print("エラー: ユーザープロフィールが見つかりません")
            return HttpResponseRedirect(f"{settings.FRONTEND_URL}/dashboard/github?error=no_user")
            
    except Exception as e:
        print(f"エラー: GitHub OAuth処理中に例外が発生: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return HttpResponseRedirect(f"{settings.FRONTEND_URL}/dashboard/github?error=server_error")

class QiitaArticleViewSet(viewsets.ModelViewSet):
    """
    Qiita記事を管理するViewSet
    """
    serializer_class = QiitaArticleSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    
    def get_queryset(self):
        if self.request.user.is_staff:
            return QiitaArticle.objects.all()
        try:
            profile = UserProfile.objects.get(user=self.request.user)
            return QiitaArticle.objects.filter(user=profile)
        except UserProfile.DoesNotExist:
            return QiitaArticle.objects.none()
    
    @action(detail=False, methods=['post'])
    def sync(self, request):
        """Qiitaから記事を同期する"""
        try:
            # ユーザープロフィールを取得
            profile = UserProfile.objects.get(user=request.user)
            
            # Qiitaユーザー名とアクセストークンを確認
            if not profile.qiita_username or not profile.qiita_access_token:
                return Response(
                    {"error": "Qiitaのユーザー名とアクセストークンを設定してください。"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Qiita APIのヘッダー設定
            headers = {
                "Authorization": f"Bearer {profile.qiita_access_token}"
            }
            
            # 自分の記事を取得（最大100件）
            response = requests.get(
                f"https://qiita.com/api/v2/users/{profile.qiita_username}/items?per_page=100",
                headers=headers
            )
            
            if response.status_code != 200:
                return Response(
                    {"error": f"Qiita APIエラー: {response.status_code}", "detail": response.text},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            articles_data = response.json()
            
            # 記事を同期
            synced_count = 0
            
            for article_data in articles_data:
                # 記事のIDを取得
                article_id = article_data["id"]
                
                # タグ情報を整形
                tags = [tag.get("name") for tag in article_data.get("tags", [])]
                
                # 記事を更新または作成
                article, created = QiitaArticle.objects.update_or_create(
                    user=profile,
                    article_id=article_id,
                    defaults={
                        "title": article_data["title"],
                        "url": article_data["url"],
                        "likes_count": article_data["likes_count"],
                        "stocks_count": article_data.get("stocks_count", 0),
                        "comments_count": article_data["comments_count"],
                        "created_at": article_data["created_at"],
                        "updated_at": article_data["updated_at"],
                        "tags": tags,
                        "body_md": article_data.get("body", ""),
                        "body_html": article_data.get("rendered_body", "")
                    }
                )
                
                synced_count += 1
            
            return Response({
                "success": True,
                "message": f"{synced_count}件の記事を同期しました",
                "articles_count": synced_count
            })
            
        except UserProfile.DoesNotExist:
            return Response(
                {"error": "ユーザープロフィールが見つかりません。"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": f"同期中にエラーが発生しました: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['patch'])
    def toggle_featured(self, request, pk=None):
        """記事の特集フラグを切り替える"""
        article = self.get_object()
        article.is_featured = not article.is_featured
        article.save()
        
        return Response({
            "success": True,
            "is_featured": article.is_featured,
            "message": f"記事「{article.title}」を{'特集に追加' if article.is_featured else '特集から削除'}しました"
        })
