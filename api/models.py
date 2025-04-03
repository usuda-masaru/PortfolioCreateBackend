from django.db import models
from django.contrib.auth.models import User
import uuid
import os
from django.utils import timezone

def profile_image_path(instance, filename):
    """カスタムファイルパスを生成する"""
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('profile_images', filename)

def skill_icon_path(instance, filename):
    """スキルアイコンのファイルパスを生成する"""
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('skill_icons', filename)

def resume_path(instance, filename):
    """職務経歴書のファイルパスを生成する"""
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('resumes', filename)

def generate_unique_portfolio_id():
    """一意のポートフォリオIDを生成する"""
    # 短めのUUIDを生成（最初の8文字を使用）
    return str(uuid.uuid4()).replace('-', '')[:8]

class UserProfile(models.Model):
    """ユーザープロフィールモデル"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    profile_image = models.ImageField(upload_to=profile_image_path, blank=True, null=True)
    display_name = models.CharField(max_length=100)
    title = models.CharField(max_length=100, help_text="例: フルスタックエンジニア") 
    bio = models.TextField(blank=True, help_text="自己紹介/自己PR") 
    specialty = models.CharField(max_length=200, blank=True, help_text="専門分野")
    location = models.CharField(max_length=100, blank=True)
    email_public = models.EmailField(blank=True, help_text="公開用メールアドレス")
    github_username = models.CharField(max_length=100, blank=True)
    github_access_token = models.CharField(max_length=255, blank=True, null=True, help_text="GitHub連携用アクセストークン")
    qiita_username = models.CharField(max_length=100, blank=True)
    qiita_access_token = models.CharField(max_length=255, blank=True, null=True, help_text="Qiita連携用アクセストークン")
    twitter_username = models.CharField(max_length=100, blank=True)
    linkedin_url = models.URLField(blank=True)
    website_url = models.URLField(blank=True)
    resume = models.FileField(upload_to=resume_path, blank=True, null=True, help_text="職務経歴書PDF")
    portfolio_slug = models.SlugField(unique=True, help_text="URLに使用する一意の文字列", default=generate_unique_portfolio_id)
    github_client_id = models.CharField(max_length=255, blank=True, null=True)
    github_client_secret = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.display_name
    
    def save(self, *args, **kwargs):
        # 新規作成時にportfolio_slugが設定されていなければデフォルト値を設定
        if not self.portfolio_slug:
            self.portfolio_slug = generate_unique_portfolio_id()
        super(UserProfile, self).save(*args, **kwargs)

class SkillCategory(models.Model):
    """スキルカテゴリモデル（言語、フレームワーク、インフラなど）"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, default='')
    order = models.IntegerField(default=0)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='skill_categories')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'created_at']
        unique_together = ['name', 'user']  # ユーザーごとにカテゴリ名を一意にする

    def __str__(self):
        return self.name

class Skill(models.Model):
    """スキルモデル"""
    LEVEL_CHOICES = [
        (1, '初級'),
        (2, '中級'),
        (3, '上級'),
        (4, 'エキスパート'),
        (5, 'マスター'),
    ]
    
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='skills')
    category = models.ForeignKey(SkillCategory, on_delete=models.CASCADE, related_name='skills')
    name = models.CharField(max_length=100)
    level = models.IntegerField(choices=LEVEL_CHOICES, default=1)
    experience_years = models.DecimalField(max_digits=3, decimal_places=1, default=0)
    icon = models.ImageField(upload_to=skill_icon_path, blank=True, null=True)
    icon_id = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    is_highlighted = models.BooleanField(default=False, help_text="ポートフォリオで強調表示するスキル")
    
    class Meta:
        ordering = ['category', 'order', 'name']
        unique_together = ['user', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.get_level_display()})"

class ProcessExperience(models.Model):
    """担当工程の経験を記録するモデル"""
    PROCESS_CHOICES = [
        ('requirements', '要件定義'),
        ('basic_design', '基本設計'),
        ('detailed_design', '詳細設計'),
        ('implementation', '実装'),
        ('testing', '試験'),
        ('deployment', 'デプロイ/リリース'),
        ('operation', '運用/保守'),
    ]
    
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='process_experiences')
    process_type = models.CharField(max_length=50, choices=PROCESS_CHOICES)
    experience_count = models.PositiveIntegerField(default=0, help_text="担当した回数")
    description = models.TextField(blank=True, help_text="この工程での経験やスキルについての説明")
    
    class Meta:
        ordering = ['process_type']
        unique_together = ['user', 'process_type']
        verbose_name_plural = "Process Experiences"
    
    def __str__(self):
        return f"{self.get_process_type_display()} ({self.experience_count}回)"

class Project(models.Model):
    """プロジェクト/ポートフォリオ項目モデル"""
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='projects')
    title = models.CharField(max_length=200)
    description = models.TextField()
    thumbnail = models.ImageField(upload_to='project_thumbnails/', blank=True, null=True)
    project_url = models.URLField(blank=True, help_text="プロジェクトのURL")
    github_url = models.URLField(blank=True, help_text="GitHubリポジトリのURL")
    technologies_used = models.ManyToManyField(Skill, related_name='projects')
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    is_featured = models.BooleanField(default=False, help_text="注目プロジェクトとして表示")
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-is_featured', 'order', '-created_at']
    
    def __str__(self):
        return self.title

class Education(models.Model):
    """学歴モデル"""
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='education')
    institution = models.CharField(max_length=200, help_text="学校名（学科）")
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    description = models.TextField(blank=True)
    is_visible = models.BooleanField(default=True, help_text="ポートフォリオでの表示/非表示")
    
    class Meta:
        ordering = ['-end_date', '-start_date']
        verbose_name_plural = "Education"
    
    def __str__(self):
        return self.institution

class WorkExperience(models.Model):
    """職歴モデル"""
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='work_experiences')
    company = models.CharField(max_length=200, blank=True, null=True)
    position = models.CharField(max_length=200)
    project_name = models.CharField(max_length=200, blank=True, null=True)
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    current = models.BooleanField(default=False)
    description = models.TextField()
    team_size = models.PositiveIntegerField(blank=True, null=True)
    role_description = models.TextField(blank=True, null=True)

    # 詳細情報を保存
    details = models.JSONField(blank=True, null=True, default=dict)

    os_used = models.JSONField(blank=True, null=True, default=list)
    languages_used = models.JSONField(blank=True, null=True, default=list)
    db_used = models.JSONField(blank=True, null=True, default=list)
    frameworks_used = models.JSONField(blank=True, null=True, default=list)
    
    process_roles = models.JSONField(blank=True, null=True, default=list)
    process_details = models.JSONField(blank=True, null=True, default=dict)
    
    skills_used = models.ManyToManyField(Skill, blank=True, related_name='work_experiences')
    
    class Meta:
        ordering = ['-current', '-end_date', '-start_date']
    
    def __str__(self):
        return f"{self.position} at {self.company or 'プロジェクト'}"

# GitHubリポジトリモデル
class GitHubRepository(models.Model):
    """ユーザーのGitHubリポジトリ情報"""
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='github_repositories')
    name = models.CharField(max_length=255, help_text="リポジトリ名")
    full_name = models.CharField(max_length=255, help_text="フルリポジトリ名（ユーザー名/リポジトリ名）")
    html_url = models.URLField(help_text="GitHubリポジトリURL")
    description = models.TextField(blank=True, null=True, help_text="リポジトリの説明")
    language = models.CharField(max_length=100, blank=True, null=True, help_text="主要言語")
    stargazers_count = models.IntegerField(default=0, help_text="スター数")
    forks_count = models.IntegerField(default=0, help_text="フォーク数")
    open_issues_count = models.IntegerField(default=0, help_text="オープンなイシュー数")
    watchers_count = models.IntegerField(default=0, help_text="ウォッチャー数")
    created_at = models.DateTimeField(help_text="リポジトリ作成日")
    updated_at = models.DateTimeField(help_text="リポジトリ更新日")
    pushed_at = models.DateTimeField(help_text="最終プッシュ日")
    featured = models.BooleanField(default=False, help_text="ポートフォリオで特集するかどうか")
    topics = models.JSONField(default=list, blank=True, null=True, help_text="トピックタグ")
    is_fork = models.BooleanField(default=False, help_text="フォークかどうか")
    is_private = models.BooleanField(default=False, help_text="プライベートリポジトリかどうか")
    
    class Meta:
        verbose_name_plural = "GitHub Repositories"
        ordering = ['-featured', '-pushed_at']
    
    def __str__(self):
        return self.name

# GitHubコミット統計モデル
class GitHubCommitStats(models.Model):
    """ユーザーのGitHubコミット統計情報"""
    user = models.OneToOneField(UserProfile, on_delete=models.CASCADE, related_name='github_stats')
    commit_count_total = models.IntegerField(default=0, help_text="総コミット数")
    commit_count_last_year = models.IntegerField(default=0, help_text="過去1年のコミット数")
    contributions_by_month = models.JSONField(default=dict, help_text="月ごとのコントリビューション数")
    languages_used = models.JSONField(default=dict, help_text="使用言語の割合")
    last_updated = models.DateTimeField(auto_now=True, help_text="最終更新日")
    
    class Meta:
        verbose_name_plural = "GitHub Commit Stats"
        
    def __str__(self):
        return f"{self.user.display_name}のGitHub統計"

# QiitaArticleモデル
class QiitaArticle(models.Model):
    """ユーザーのQiita記事情報"""
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='qiita_articles')
    article_id = models.CharField(max_length=255, help_text="Qiita記事ID")
    title = models.CharField(max_length=255, help_text="記事タイトル")
    url = models.URLField(help_text="記事URL")
    likes_count = models.IntegerField(default=0, help_text="いいね数")
    stocks_count = models.IntegerField(default=0, help_text="ストック数")
    comments_count = models.IntegerField(default=0, help_text="コメント数")
    created_at = models.DateTimeField(help_text="記事作成日")
    updated_at = models.DateTimeField(help_text="記事更新日")
    tags = models.JSONField(default=list, blank=True, null=True, help_text="記事のタグ")
    body_md = models.TextField(blank=True, null=True, help_text="記事本文(Markdown)")
    body_html = models.TextField(blank=True, null=True, help_text="記事本文(HTML)")
    is_featured = models.BooleanField(default=False, help_text="ポートフォリオで特集するかどうか")
    
    class Meta:
        verbose_name_plural = "Qiita Articles"
        ordering = ['-is_featured', '-created_at']
        unique_together = ['user', 'article_id']
    
    def __str__(self):
        return self.title
