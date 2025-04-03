from django.contrib import admin
from .models import UserProfile, SkillCategory, Skill, Project, Education, WorkExperience

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'user', 'title', 'portfolio_slug', 'created_at')
    search_fields = ('display_name', 'user__username', 'title', 'bio', 'specialty')
    readonly_fields = ('created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')

@admin.register(SkillCategory)
class SkillCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'order')
    ordering = ('order', 'name')

@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'category', 'level', 'experience_years')
    list_filter = ('category', 'level')
    search_fields = ('name', 'user__display_name', 'description')
    ordering = ('category', 'order', 'name')

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'is_featured', 'start_date', 'end_date')
    list_filter = ('is_featured', 'start_date', 'end_date')
    search_fields = ('title', 'description', 'user__display_name')
    readonly_fields = ('created_at', 'updated_at')
    filter_horizontal = ('technologies_used',)

@admin.register(Education)
class EducationAdmin(admin.ModelAdmin):
    list_display = ('institution', 'start_date', 'end_date', 'is_visible')
    list_filter = ('is_visible',)
    search_fields = ('institution', 'description')
    ordering = ('-end_date', '-start_date')

@admin.register(WorkExperience)
class WorkExperienceAdmin(admin.ModelAdmin):
    list_display = ('position', 'company', 'user', 'start_date', 'end_date', 'current')
    list_filter = ('start_date', 'end_date', 'current')
    search_fields = ('company', 'position', 'description', 'user__display_name')
    filter_horizontal = ('skills_used',)
