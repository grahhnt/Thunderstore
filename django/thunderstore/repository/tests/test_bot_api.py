import jwt
import pytest
from django.urls import reverse

from thunderstore.core.models import IncomingJWTAuthConfiguration, SecretTypeChoices
from thunderstore.repository.models import DiscordUserBotPermission


@pytest.mark.django_db
def test_bot_api_deprecate_mod_200(api_client, admin_user, package, community_site):
    assert package.is_deprecated is False
    jwt_secret = "superSecret"
    auth = IncomingJWTAuthConfiguration.objects.create(
        name="Test configuration",
        user=admin_user,
        secret=jwt_secret,
        secret_type=SecretTypeChoices.HS256,
    )
    perms = DiscordUserBotPermission.objects.create(
        label="Test",
        thunderstore_user=admin_user,
        discord_user_id=1234,
        can_deprecate=True,
    )

    payload = {"package": package.full_package_name, "user": perms.discord_user_id}
    encoded = jwt.encode(
        payload=payload,
        key=jwt_secret,
        algorithm=SecretTypeChoices.HS256,
        headers={"kid": str(auth.key_id)},
    )

    response = api_client.post(
        reverse(
            "v1:bot.deprecate-mod",
            kwargs={"community_identifier": community_site.community.identifier},
        ),
        data=encoded,
        content_type="application/jwt",
    )
    assert response.status_code == 200
    assert response.content == b'{"success":true}'
    package.refresh_from_db()
    assert package.is_deprecated is True


@pytest.mark.django_db
def test_bot_api_deprecate_mod_403_thunderstore_perms(
    api_client, user, package, community_site
):
    assert package.is_deprecated is False
    jwt_secret = "superSecret"
    auth = IncomingJWTAuthConfiguration.objects.create(
        name="Test configuration",
        user=user,
        secret=jwt_secret,
        secret_type=SecretTypeChoices.HS256,
    )
    perms = DiscordUserBotPermission.objects.create(
        label="Test",
        thunderstore_user=user,
        discord_user_id=1234,
        can_deprecate=True,
    )

    payload = {"package": package.full_package_name, "user": perms.discord_user_id}
    encoded = jwt.encode(
        payload=payload,
        key=jwt_secret,
        algorithm=SecretTypeChoices.HS256,
        headers={"kid": str(auth.key_id)},
    )

    response = api_client.post(
        reverse(
            "v1:bot.deprecate-mod",
            kwargs={"community_identifier": community_site.community.identifier},
        ),
        data=encoded,
        content_type="application/jwt",
    )
    assert response.status_code == 403
    assert (
        response.content
        == b'{"detail":"You do not have permission to perform this action."}'
    )
    package.refresh_from_db()
    assert package.is_deprecated is False


@pytest.mark.django_db
def test_bot_api_deprecate_mod_403_discord_perms(
    api_client,
    admin_user,
    package,
    community_site,
):
    assert package.is_deprecated is False
    jwt_secret = "superSecret"
    auth = IncomingJWTAuthConfiguration.objects.create(
        name="Test configuration",
        user=admin_user,
        secret=jwt_secret,
        secret_type=SecretTypeChoices.HS256,
    )
    DiscordUserBotPermission.objects.create(
        label="Test",
        thunderstore_user=admin_user,
        discord_user_id=1234,
        can_deprecate=False,
    )

    payload = {"package": package.full_package_name, "user": 1234}
    encoded = jwt.encode(
        payload=payload,
        key=jwt_secret,
        algorithm=SecretTypeChoices.HS256,
        headers={"kid": str(auth.key_id)},
    )

    response = api_client.post(
        reverse(
            "v1:bot.deprecate-mod",
            kwargs={"community_identifier": community_site.community.identifier},
        ),
        data=encoded,
        content_type="application/jwt",
    )
    assert response.status_code == 403
    assert response.content == b'{"detail":"Insufficient Discord user permissions"}'
    package.refresh_from_db()
    assert package.is_deprecated is False


@pytest.mark.django_db
def test_bot_api_deprecate_mod_404(api_client, admin_user, community_site):
    jwt_secret = "superSecret"
    auth = IncomingJWTAuthConfiguration.objects.create(
        name="Test configuration",
        user=admin_user,
        secret=jwt_secret,
        secret_type=SecretTypeChoices.HS256,
    )
    perms = DiscordUserBotPermission.objects.create(
        label="Test",
        thunderstore_user=admin_user,
        discord_user_id=1234,
        can_deprecate=True,
    )

    payload = {"package": "Nonexistent-Package", "user": perms.discord_user_id}
    encoded = jwt.encode(
        payload=payload,
        key=jwt_secret,
        algorithm=SecretTypeChoices.HS256,
        headers={"kid": str(auth.key_id)},
    )
    response = api_client.post(
        reverse(
            "v1:bot.deprecate-mod",
            kwargs={"community_identifier": community_site.community.identifier},
        ),
        data=encoded,
        content_type="application/jwt",
    )
    assert response.status_code == 404
    assert response.content == b'{"detail":"Not found."}'
