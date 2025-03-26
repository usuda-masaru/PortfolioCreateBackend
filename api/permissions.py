from rest_framework import permissions

class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    オブジェクトの所有者のみが編集可能な権限クラス
    """
    def has_object_permission(self, request, view, obj):
        # 読み取り権限は全てのリクエストに許可
        if request.method in permissions.SAFE_METHODS:
            return True
            
        # ユーザープロフィールの場合
        if hasattr(obj, 'user'):
            # obj.userがUserProfileインスタンスの場合
            if hasattr(obj.user, 'user'):
                return obj.user.user == request.user
            # obj.userがUserインスタンスの場合
            return obj.user == request.user
            
        # ユーザープロフィールに関連するモデルの場合
        if hasattr(obj, 'profile'):
            return obj.profile.user == request.user
            
        # 直接user_idを持つモデルの場合
        if hasattr(obj, 'user_id'):
            return obj.user_id == request.user.id
            
        return False 