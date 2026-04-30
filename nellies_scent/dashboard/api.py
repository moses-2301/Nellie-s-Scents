from allauth.socialaccount.models import SocialApp, SocialAccount, SocialToken
from django.contrib.sites.models import Site
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from .provider_utils import get_provider_display


class SocialAppSerializer(serializers.ModelSerializer):
    """Serializer for django-allauth SocialApp model."""
    
    sites = serializers.PrimaryKeyRelatedField(queryset=Site.objects.all(), many=True)
    secret = serializers.CharField(write_only=True, allow_blank=True, required=False)
    masked_secret = serializers.SerializerMethodField(read_only=True)
    provider_display = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = SocialApp
        fields = [
            'id', 'provider', 'provider_display', 'name', 'client_id', 'secret', 
            'masked_secret', 'key', 'sites',
        ]
        read_only_fields = ['masked_secret', 'provider_display']

    def get_masked_secret(self, obj):
        """Return masked string if secret exists."""
        return '••••••••' if obj.secret else ''

    def get_provider_display(self, obj):
        """Return human-readable provider name."""
        return get_provider_display(obj.provider)

    def validate_provider(self, value):
        """Prevent duplicate providers."""
        if self.instance is None:  # Creating new
            if SocialApp.objects.filter(provider=value).exists():
                raise serializers.ValidationError(
                    f'A social app for {value.title()} already exists.'
                )
        return value

    def create(self, validated_data):
        """Create SocialApp and attach to site."""
        sites = validated_data.pop('sites', [])
        app = SocialApp.objects.create(**validated_data)
        
        if sites:
            app.sites.set(sites)
        else:
            # Auto-attach to default site if none provided
            from django.conf import settings
            site_id = getattr(settings, 'SITE_ID', 1)
            site = Site.objects.get(pk=site_id)
            app.sites.add(site)
        
        return app

    def update(self, instance, validated_data):
        """Update SocialApp and sites."""
        sites = validated_data.pop('sites', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        if sites is not None:
            instance.sites.set(sites)
        
        return instance


class SocialAccountSerializer(serializers.ModelSerializer):
    """Serializer for linked social accounts."""
    
    user = serializers.CharField(source='user.username', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    date_connected = serializers.DateTimeField(source='date_joined', read_only=True)
    provider_display = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = SocialAccount
        fields = ['id', 'user', 'user_email', 'provider', 'provider_display', 'uid', 'date_connected']

    def get_provider_display(self, obj):
        """Return human-readable provider name."""
        return get_provider_display(obj.provider)


class SocialTokenSerializer(serializers.ModelSerializer):
    """Serializer for stored social authentication tokens."""
    
    account_id = serializers.IntegerField(source='account.id', read_only=True)
    user = serializers.CharField(source='account.user.username', read_only=True)
    provider = serializers.CharField(source='account.provider', read_only=True)
    provider_display = serializers.SerializerMethodField(read_only=True)
    masked_token = serializers.SerializerMethodField(read_only=True)
    expiry_date = serializers.DateTimeField(source='expires_at', read_only=True)

    class Meta:
        model = SocialToken
        fields = ['id', 'account_id', 'user', 'provider', 'provider_display', 'masked_token', 'expiry_date']

    def get_provider_display(self, obj):
        """Return human-readable provider name."""
        return get_provider_display(obj.account.provider)

    def get_masked_token(self, obj):
        """Return partially masked token for security."""
        token_value = obj.token or ''
        if len(token_value) <= 10:
            return '••••••••'
        return token_value[:4] + '••••••••' + token_value[-4:]


class SocialAppViewSet(viewsets.ModelViewSet):
    """ViewSet for managing social authentication apps."""
    
    permission_classes = [IsAdminUser]
    queryset = SocialApp.objects.prefetch_related('sites').order_by('provider')
    serializer_class = SocialAppSerializer

    @action(detail=False, methods=['get'])
    def by_provider(self, request):
        """Get app by provider name."""
        provider = request.query_params.get('provider')
        if not provider:
            return Response(
                {'error': 'provider parameter required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            app = SocialApp.objects.get(provider=provider)
            serializer = self.get_serializer(app)
            return Response(serializer.data)
        except SocialApp.DoesNotExist:
            return Response(
                {'error': f'No app found for provider {provider}'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'])
    def test_connection(self, request, pk=None):
        """Test if app credentials are valid (validation check)."""
        app = self.get_object()
        
        if not app.client_id or not app.secret:
            return Response(
                {'status': 'incomplete', 'message': 'Missing client_id or secret'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        response_data = {
            'status': 'configured',
            'provider': app.provider,
            'name': app.name,
            'sites': list(app.sites.values_list('name', flat=True)),
            'message': 'App is configured for this provider'
        }
        return Response(response_data)


class SocialAccountViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only ViewSet for viewing linked social accounts."""
    
    permission_classes = [IsAdminUser]
    queryset = SocialAccount.objects.select_related('user').order_by('-date_joined')
    serializer_class = SocialAccountSerializer

    @action(detail=True, methods=['post'])
    def disconnect(self, request, pk=None):
        """Disconnect a user's social account."""
        account = self.get_object()
        user = account.user.username
        provider = account.provider
        account.delete()
        
        return Response({
            'message': f'Disconnected {provider} account for {user}'
        })

    @action(detail=False, methods=['get'])
    def by_provider(self, request):
        """List accounts by provider."""
        provider = request.query_params.get('provider')
        if not provider:
            return Response(
                {'error': 'provider parameter required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        accounts = self.get_queryset().filter(provider=provider)
        serializer = self.get_serializer(accounts, many=True)
        return Response(serializer.data)


class SocialTokenViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only ViewSet for viewing OAuth tokens (admin-only)."""
    
    permission_classes = [IsAdminUser]
    queryset = SocialToken.objects.select_related('account', 'account__user').order_by('-id')
    serializer_class = SocialTokenSerializer

    @action(detail=True, methods=['post'])
    def revoke(self, request, pk=None):
        """Revoke a stored OAuth token."""
        token = self.get_object()
        user = token.account.user.username
        provider = token.account.provider
        token.delete()
        
        return Response({
            'message': f'Revoked {provider} token for {user}'
        })

    @action(detail=False, methods=['get'])
    def by_provider(self, request):
        """List tokens by provider."""
        provider = request.query_params.get('provider')
        if not provider:
            return Response(
                {'error': 'provider parameter required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        tokens = self.get_queryset().filter(account__provider=provider)
        serializer = self.get_serializer(tokens, many=True)
        return Response(serializer.data)
