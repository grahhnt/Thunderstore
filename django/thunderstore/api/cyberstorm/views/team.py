from django.db.models import Q, QuerySet
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import ListAPIView, RetrieveAPIView, get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request

from thunderstore.account.models.service_account import ServiceAccount
from thunderstore.api.cyberstorm.serializers import (
    CyberstormServiceAccountSerializer,
    CyberstormTeamMemberSerializer,
    CyberstormTeamSerializer,
)
from thunderstore.api.ordering import StrictOrderingFilter
from thunderstore.api.utils import CyberstormAutoSchemaMixin
from thunderstore.repository.models.team import Team, TeamMember


class TeamDetailAPIView(CyberstormAutoSchemaMixin, RetrieveAPIView):
    serializer_class = CyberstormTeamSerializer
    queryset = Team.objects.exclude(is_active=False)
    lookup_field = "name__iexact"
    lookup_url_kwarg = "team_id"


class TeamRestrictedAPIView(ListAPIView):
    """
    Ensure the user is a member of the Team.
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request: Request) -> None:
        super().check_permissions(request)

        teams = Team.objects.exclude(is_active=False)
        team = get_object_or_404(teams, name__iexact=self.kwargs["team_id"])

        if not team.can_user_access(request.user):
            raise PermissionDenied()


class TeamMembersAPIView(CyberstormAutoSchemaMixin, TeamRestrictedAPIView):
    serializer_class = CyberstormTeamMemberSerializer
    filter_backends = [StrictOrderingFilter]
    ordering = ["-role", "user__username"]

    def get_queryset(self) -> QuerySet[TeamMember]:
        return (
            TeamMember.objects.real_users()
            .exclude(~Q(team__name__iexact=self.kwargs["team_id"]))
            .prefetch_related("user__social_auth")
        )


class TeamServiceAccountsAPIView(CyberstormAutoSchemaMixin, TeamRestrictedAPIView):
    serializer_class = CyberstormServiceAccountSerializer
    filter_backends = [StrictOrderingFilter]
    ordering = ["user__first_name"]

    def get_queryset(self) -> QuerySet[ServiceAccount]:
        return ServiceAccount.objects.exclude(
            ~Q(owner__name__iexact=self.kwargs["team_id"]),
        ).select_related("user")