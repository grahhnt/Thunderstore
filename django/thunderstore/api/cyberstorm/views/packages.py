from copy import deepcopy
from typing import List, Optional, OrderedDict, Tuple
from urllib.parse import urlencode

from django.conf import settings
from django.core.paginator import Page
from django.db.models import Count, OuterRef, Q, QuerySet, Subquery, Sum
from django.urls import reverse
from django.utils.decorators import method_decorator
from rest_framework import serializers
from rest_framework.generics import ListAPIView, get_object_or_404
from rest_framework.pagination import PageNumberPagination

from thunderstore.api.cyberstorm.serializers import CyberstormPackagePreviewSerializer
from thunderstore.api.utils import conditional_swagger_auto_schema
from thunderstore.community.consts import PackageListingReviewStatus
from thunderstore.community.models import Community, PackageListingSection
from thunderstore.repository.models import Namespace, Package

# Keys are values expected in requests, values are args for .order_by().
ORDER_ARGS = {
    "last-updated": "-date_updated",
    "most-downloaded": "-download_count",  # annotated field
    "newest": "-date_created",
    "top-rated": "-rating_count",  # annotated field
}


class PackageListRequestSerializer(serializers.Serializer):
    """
    For deserializing the query parameters used in package filtering.
    """

    deprecated = serializers.BooleanField(default=False)
    excluded_categories = serializers.ListField(
        child=serializers.IntegerField(),
        default=[],
    )
    included_categories = serializers.ListField(
        child=serializers.IntegerField(),
        default=[],
    )
    nsfw = serializers.BooleanField(default=False)
    ordering = serializers.ChoiceField(
        choices=list(ORDER_ARGS.keys()),
        default="last-updated",
    )
    page = serializers.IntegerField(default=1, min_value=1)
    q = serializers.CharField(required=False, help_text="Free text search")
    section = serializers.UUIDField(required=False)


class PackageListResponseSerializer(serializers.Serializer):
    """
    Matches DRF's PageNumberPagination response.
    """

    count = serializers.IntegerField(min_value=0)
    previous = serializers.CharField(allow_null=True)
    next = serializers.CharField(allow_null=True)  # noqa: A003
    results = CyberstormPackagePreviewSerializer(many=True)


class PackageListPaginator(PageNumberPagination):
    page_size = 20

    def get_schema_fields(self, view):
        """
        By default this would return page (via page_query_param
        attribute) and page_size (via page_size_query_param attribute).
        The former would clash with the page field defined in our
        PackageListRequestSerializer, breaking the API documentation
        generated by drf_yasg. Returning an empty list means we have the
        control and responsibility to make sure the documentation
        matches reality.
        """
        return []


class BasePackageListAPIView(ListAPIView):
    """
    Base class for community-scoped, paginated, filterable package listings.

    Classes implementing this base class should receive `community_id`
    url parameter.

    Methods with names starting prefixed with underscore are you custom
    methods, whereas the rest are overwritten methods from ListAPIView.
    """

    pagination_class = PackageListPaginator
    serializer_class = CyberstormPackagePreviewSerializer
    viewname: str = ""  # Define in subclass

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def list(self, request, *args, **kwargs):  # noqa: A003
        assert self.paginator is not None

        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        response = self.paginator.get_paginated_response(serializer.data)

        # Paginator's default implementation uses the Request object to
        # construct previous/next links, which can open attack vectors
        # via cache. Ideally this would have been overridden in the
        # paginator itself, but that would require passing extra args,
        # which would change the methods signatures, which is icky and
        # not liked by MyPy either.
        (previous_url, next_url) = self._get_sibling_pages()
        response.data["previous"] = previous_url
        response.data["next"] = next_url

        return response

    def get_serializer(self, package_page: Page, **kwargs):
        """
        Augment the objects with information required by serializer.

        This is needed since the serializer returns community-related
        information that is not directly available on a Package object.

        This is an awkward place to do this but ListApiView didn't seem
        to contain more suitable way to adjust the items.

        Using Page as type overrides the default implementation, but is
        accurate as long as serializer_class is defined. If not, it may
        be any iterable, e.g. QuerySet.
        """
        package_list = self._get_packages_dicts(package_page)
        return super().get_serializer(package_list, **kwargs)

    def get_queryset(self) -> QuerySet[Package]:
        queryset = get_community_package_queryset(self._get_community())
        return self._annotate_queryset(queryset)

    def filter_queryset(self, queryset: QuerySet[Package]) -> QuerySet[Package]:
        community = self._get_community()
        require_approval = community.require_package_listing_approval
        queryset = self.get_queryset()
        params = self._get_validated_query_params()

        queryset = filter_by_review_status(require_approval, queryset)
        queryset = filter_deprecated(params["deprecated"], queryset)
        queryset = filter_nsfw(params["nsfw"], queryset)
        queryset = filter_in_categories(params["included_categories"], queryset)
        queryset = filter_not_in_categories(params["excluded_categories"], queryset)
        queryset = filter_by_section(params.get("section"), queryset)
        queryset = filter_by_query(params.get("q"), queryset)

        return queryset.order_by(
            "-is_pinned",
            "is_deprecated",
            ORDER_ARGS[params["ordering"]],
            "-date_updated",
            "-pk",
        )

    def _get_community(self) -> Community:
        """
        Read Community identifier from URL parameter and return object.
        """
        community_id = self.kwargs["community_id"]
        return get_object_or_404(Community, identifier=community_id)

    def _annotate_queryset(self, queryset: QuerySet[Package]) -> QuerySet[Package]:
        """
        Add annotations required to serialize the results.
        """

        this_package = Package.objects.filter(pk=OuterRef("pk"))

        return queryset.annotate(
            download_count=Subquery(
                this_package.annotate(
                    downloads=Sum("versions__downloads"),
                ).values("downloads"),
            ),
        ).annotate(
            rating_count=Subquery(
                this_package.annotate(
                    ratings=Count("package_ratings"),
                ).values("ratings"),
            ),
        )

    def _get_validated_query_params(self) -> OrderedDict:
        """
        Validate request query parameters with a request serializer.
        """
        qp = PackageListRequestSerializer(data=self.request.query_params)
        qp.is_valid(raise_exception=True)
        params = qp.validated_data

        # To improve cacheability.
        for value in params.values():
            if isinstance(value, list):
                value.sort()

        return params

    def _get_packages_dicts(self, package_page: Page):
        """
        Return objects that can be serialized by the response serializer.
        """
        community_id = self.kwargs["community_id"]
        packages = []

        for p in package_page:
            listing = p.community_listings.get(community__identifier=community_id)

            packages.append(
                {
                    "categories": listing.categories.all(),
                    "community_identifier": community_id,
                    "description": p.latest.description,
                    "download_count": p.download_count,
                    "icon_url": p.latest.icon.url if bool(p.latest.icon) else None,
                    "is_deprecated": p.is_deprecated,
                    "is_nsfw": listing.has_nsfw_content,
                    "is_pinned": p.is_pinned,
                    "last_updated": p.date_updated,
                    "namespace": p.namespace.name,
                    "name": p.name,
                    "rating_count": p.rating_count,
                    "size": p.latest.file_size,
                },
            )

        return packages

    def _get_sibling_pages(self) -> Tuple[Optional[str], Optional[str]]:
        """
        Return the URLs to previous and next pages of this result set.
        """
        assert self.paginator is not None
        assert hasattr(self.paginator, "page")
        page: Page = self.paginator.page

        assert self.viewname
        path = reverse(self.viewname, kwargs=self.kwargs)

        base_url = f"{settings.PROTOCOL}{settings.PRIMARY_HOST}{path}"
        previous_url = None
        next_url = None
        params = deepcopy(self._get_validated_query_params())

        if page.has_previous():
            params["page"] = page.previous_page_number()
            previous_url = f"{base_url}?{urlencode(params, doseq=True)}"

        if page.has_next():
            params["page"] = page.next_page_number()
            next_url = f"{base_url}?{urlencode(params, doseq=True)}"

        return (previous_url, next_url)


@method_decorator(
    name="get",
    decorator=conditional_swagger_auto_schema(
        query_serializer=PackageListRequestSerializer,
        responses={200: PackageListResponseSerializer()},
        operation_id="api_cyberstorm_package_community",
        tags=["cyberstorm"],
    ),
)
class CommunityPackageListAPIView(BasePackageListAPIView):
    """
    Community-scoped package list.
    """

    viewname = "api:cyberstorm:cyberstorm.package.community"


@method_decorator(
    name="get",
    decorator=conditional_swagger_auto_schema(
        query_serializer=PackageListRequestSerializer,
        manual_fields=[],
        responses={200: PackageListResponseSerializer()},
        operation_id="api_cyberstorm_package_community_namespace",
        tags=["cyberstorm"],
    ),
)
class NamespacePackageListAPIView(BasePackageListAPIView):
    """
    Community & Namespace-scoped package list.
    """

    viewname = "api:cyberstorm:cyberstorm.package.community.namespace"

    def get_queryset(self) -> QuerySet[Package]:
        namespace_id = self.kwargs["namespace_id"]
        namespace = get_object_or_404(Namespace, name__iexact=namespace_id)

        community_scoped_qs = super().get_queryset()
        return community_scoped_qs.exclude(~Q(namespace=namespace))


def get_community_package_queryset(community: Community) -> QuerySet[Package]:
    """
    Create base QuerySet for community scoped PackageListAPIViews.
    """

    return (
        Package.objects.active()  # type: ignore
        .select_related("latest", "namespace")
        .prefetch_related(
            "community_listings__categories",
            "community_listings__community",
        )
        .exclude(~Q(community_listings__community__pk=community.pk))
    )


def filter_deprecated(
    show_deprecated: bool,
    queryset: QuerySet[Package],
) -> QuerySet[Package]:
    if show_deprecated:
        return queryset

    return queryset.exclude(is_deprecated=True)


def filter_nsfw(
    show_nsfw: bool,
    queryset: QuerySet[Package],
) -> QuerySet[Package]:
    if show_nsfw:
        return queryset

    return queryset.exclude(community_listings__has_nsfw_content=True)


def filter_in_categories(
    category_ids: List[int],
    queryset: QuerySet[Package],
) -> QuerySet[Package]:
    """
    Include only packages belonging to specific categories.

    Multiple categories are OR-joined, i.e. if category_ids contain A
    and B, packages belonging to either will be returned.
    """
    if not category_ids:
        return queryset

    return queryset.exclude(
        ~Q(community_listings__categories__id__in=category_ids),
    )


def filter_not_in_categories(
    category_ids: List[int],
    queryset: QuerySet[Package],
) -> QuerySet[Package]:
    """
    Exclude packages belonging to specific categories.

    Multiple categories are OR-joined, i.e. if category_ids contain A
    and B, packages belonging to either will be rejected.
    """
    if not category_ids:
        return queryset

    return queryset.exclude(
        community_listings__categories__id__in=category_ids,
    )


def filter_by_section(
    section_uuid: Optional[str],
    queryset: QuerySet[Package],
) -> QuerySet[Package]:
    """
    PackageListingSections can be used as shortcut for multiple
    category filters.
    """
    if not section_uuid:
        return queryset

    try:
        section = PackageListingSection.objects.prefetch_related(
            "require_categories",
            "exclude_categories",
        ).get(uuid=section_uuid)
    except PackageListingSection.DoesNotExist:
        required = []
        excluded = []
    else:
        required = section.require_categories.values_list("pk", flat=True)
        excluded = section.exclude_categories.values_list("pk", flat=True)

    queryset = filter_in_categories(required, queryset)
    return filter_not_in_categories(excluded, queryset)


def filter_by_query(
    query: Optional[str],
    queryset: QuerySet[Package],
) -> QuerySet[Package]:
    """
    Filter packages by free text search.
    """
    if not query:
        return queryset

    search_fields = ("name", "owner__name", "latest__description")
    icontains_query = Q()
    parts = [x for x in query.split(" ") if x]

    for part in parts:
        for field in search_fields:
            icontains_query &= ~Q(**{f"{field}__icontains": part})

    return queryset.exclude(icontains_query).distinct()


def filter_by_review_status(
    require_approval: bool,
    queryset: QuerySet[Package],
) -> QuerySet[Package]:
    review_statuses = [PackageListingReviewStatus.approved]

    if not require_approval:
        review_statuses.append(PackageListingReviewStatus.unreviewed)

    return queryset.exclude(
        ~Q(community_listings__review_status__in=review_statuses),
    )
