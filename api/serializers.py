from rest_framework import serializers
from django.contrib.auth.models import User
from .models import UserProfile, SkillCategory, Skill, Project, Education, WorkExperience, ProcessExperience, GitHubRepository, GitHubCommitStats, QiitaArticle
from datetime import datetime

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']
        read_only_fields = ['id']

class SkillCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = SkillCategory
        fields = ['id', 'name', 'order']

class SkillSerializer(serializers.ModelSerializer):
    """スキルシリアライザー"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    
    class Meta:
        model = Skill
        fields = ['id', 'name', 'category', 'category_name', 'level', 'experience_years', 'icon', 'icon_id', 'description', 'order', 'is_highlighted']
        read_only_fields = ['id']

class ProcessExperienceSerializer(serializers.ModelSerializer):
    process_type_display = serializers.ReadOnlyField(source='get_process_type_display')
    
    class Meta:
        model = ProcessExperience
        fields = ['id', 'process_type', 'process_type_display', 'experience_count', 'description']
        read_only_fields = ['id']

class ProjectSerializer(serializers.ModelSerializer):
    technologies = SkillSerializer(source='technologies_used', many=True, read_only=True)
    technologies_ids = serializers.PrimaryKeyRelatedField(
        source='technologies_used', queryset=Skill.objects.all(), many=True, write_only=True, required=False
    )
    
    class Meta:
        model = Project
        fields = ['id', 'title', 'description', 'thumbnail', 'project_url', 'github_url', 
                  'technologies', 'technologies_ids', 'start_date', 'end_date', 
                  'is_featured', 'order', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        technologies = validated_data.pop('technologies_used', [])
        project = Project.objects.create(**validated_data)
        project.technologies_used.set(technologies)
        return project
    
    def update(self, instance, validated_data):
        technologies = validated_data.pop('technologies_used', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        if technologies is not None:
            instance.technologies_used.set(technologies)
        
        return instance

class EducationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Education
        fields = ['id', 'institution', 'start_date', 'end_date', 'description', 'is_visible']
        read_only_fields = ['id']

    def validate(self, data):
        """
        カスタムバリデーション
        """
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        if end_date and start_date and end_date < start_date:
            raise serializers.ValidationError({
                'end_date': ['終了日は開始日より後である必要があります。']
            })
        return data

    def validate_start_date(self, value):
        """
        開始日のバリデーション
        """
        if value > datetime.now().date():
            raise serializers.ValidationError('開始日は現在の日付より前である必要があります。')
        return value

    def validate_end_date(self, value):
        """
        終了日のバリデーション
        """
        if value and value > datetime.now().date():
            raise serializers.ValidationError('終了日は現在の日付より前である必要があります。')
        return value

class WorkExperienceSerializer(serializers.ModelSerializer):
    skills_used_details = SkillSerializer(source='skills_used', many=True, read_only=True)
    skills_used_ids = serializers.PrimaryKeyRelatedField(
        source='skills_used', queryset=Skill.objects.all(), many=True, write_only=True, required=False
    )
    
    class Meta:
        model = WorkExperience
        fields = [
            'id', 'company', 'position', 'project_name', 
            'start_date', 'end_date', 'current', 'description',
            'team_size', 'role_description', 'details',
            'os_used', 'languages_used', 'db_used', 'frameworks_used',
            'process_roles', 'process_details',
            'skills_used_details', 'skills_used_ids'
        ]
        read_only_fields = ['id']
    
    def create(self, validated_data):
        skills = validated_data.pop('skills_used', [])
        work_exp = WorkExperience.objects.create(**validated_data)
        work_exp.skills_used.set(skills)
        return work_exp
    
    def update(self, instance, validated_data):
        skills = validated_data.pop('skills_used', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        if skills is not None:
            instance.skills_used.set(skills)
        
        return instance

class GitHubRepositorySerializer(serializers.ModelSerializer):
    class Meta:
        model = GitHubRepository
        fields = [
            'id', 'name', 'full_name', 'html_url', 'description', 'language',
            'stargazers_count', 'forks_count', 'open_issues_count', 'watchers_count',
            'created_at', 'updated_at', 'pushed_at', 'featured', 'topics',
            'is_fork', 'is_private'
        ]
        read_only_fields = ['id']

class GitHubCommitStatsSerializer(serializers.ModelSerializer):
    class Meta:
        model = GitHubCommitStats
        fields = [
            'id', 'commit_count_total', 'commit_count_last_year',
            'contributions_by_month', 'languages_used', 'last_updated'
        ]
        read_only_fields = ['id', 'last_updated']

class QiitaArticleSerializer(serializers.ModelSerializer):
    class Meta:
        model = QiitaArticle
        fields = [
            'id', 'article_id', 'title', 'url', 'likes_count', 'stocks_count', 
            'comments_count', 'created_at', 'updated_at', 'tags', 
            'body_md', 'body_html', 'is_featured'
        ]
        read_only_fields = ['id']

class UserProfileSerializer(serializers.ModelSerializer):
    user_details = UserSerializer(source='user', read_only=True)
    skills = SkillSerializer(many=True, read_only=True)
    projects = ProjectSerializer(many=True, read_only=True)
    education = EducationSerializer(many=True, read_only=True)
    work_experiences = WorkExperienceSerializer(many=True, read_only=True)
    process_experiences = ProcessExperienceSerializer(many=True, read_only=True)
    github_repositories = GitHubRepositorySerializer(many=True, read_only=True)
    github_stats = GitHubCommitStatsSerializer(read_only=True)
    qiita_articles = QiitaArticleSerializer(many=True, read_only=True)
    
    class Meta:
        model = UserProfile
        fields = ['id', 'user', 'user_details', 'profile_image', 'display_name', 'title', 
                  'bio', 'specialty', 'location', 'email_public', 'github_username', 
                  'github_access_token', 'github_client_id', 'github_client_secret',
                  'qiita_username', 'qiita_access_token', 'twitter_username', 'linkedin_url', 'website_url', 
                  'resume', 'portfolio_slug', 'created_at', 'updated_at', 
                  'skills', 'projects', 'education', 'work_experiences', 'process_experiences',
                  'github_repositories', 'github_stats', 'qiita_articles']
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']
        extra_kwargs = {
            'github_access_token': {'write_only': True},  # トークンは外部に公開しない
            'github_client_secret': {'write_only': True},  # クライアントシークレットも公開しない
            'qiita_access_token': {'write_only': True}  # Qiitaトークンも公開しない
        }

class UserProfilePublicSerializer(serializers.ModelSerializer):
    """公開用プロフィールシリアライザー（パブリックに表示する情報のみ）"""
    skills = serializers.SerializerMethodField()
    projects = ProjectSerializer(many=True, read_only=True)
    education = EducationSerializer(many=True, read_only=True)
    work_experiences = WorkExperienceSerializer(many=True, read_only=True)
    process_experiences = ProcessExperienceSerializer(many=True, read_only=True)
    github_repositories = serializers.SerializerMethodField()
    github_stats = GitHubCommitStatsSerializer(read_only=True)
    qiita_articles = serializers.SerializerMethodField()
    
    class Meta:
        model = UserProfile
        fields = ['display_name', 'profile_image', 'title', 'bio', 'specialty', 
                  'location', 'email_public', 'github_username', 'qiita_username', 
                  'twitter_username', 'linkedin_url', 'website_url', 'resume', 
                  'skills', 'projects', 'education', 'work_experiences', 'process_experiences',
                  'github_repositories', 'github_stats', 'qiita_articles']
    
    def get_skills(self, obj):
        """スキルをカテゴリ別にグループ化"""
        skills_by_category = {}
        for skill in obj.skills.all():
            category_id = skill.category.id
            if category_id not in skills_by_category:
                skills_by_category[category_id] = {
                    'id': category_id,
                    'name': skill.category.name,
                    'skills': []
                }
            skills_by_category[category_id]['skills'].append(SkillSerializer(skill).data)
        
        return list(skills_by_category.values())
        
    def get_github_repositories(self, obj):
        """公開リポジトリのみを返す（featuredフラグが付いたものを優先）"""
        # フィルター: 非公開リポジトリを除外し、featuredフラグでフィルタリング
        repositories = obj.github_repositories.filter(is_private=False, featured=True)
        
        # featuredフラグが付いたリポジトリがない場合は、最大5件まで通常のリポジトリを返す
        if not repositories.exists():
            repositories = obj.github_repositories.filter(is_private=False).order_by('-pushed_at')[:5]
            
        return GitHubRepositorySerializer(repositories, many=True).data

    def get_qiita_articles(self, obj):
        """表示用のQiita記事を返す（is_featuredフラグが付いたものを優先）"""
        # フィルター: 特集記事のみ
        articles = obj.qiita_articles.filter(is_featured=True)
        
        # 特集記事がない場合は、最新の5件を返す
        if not articles.exists():
            articles = obj.qiita_articles.all().order_by('-created_at')[:5]
            
        return QiitaArticleSerializer(articles, many=True).data 