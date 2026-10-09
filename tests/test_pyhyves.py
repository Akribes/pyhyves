from unittest.mock import AsyncMock, patch

import pytest

from pyhyves import PasswordCredentials, Pyhyves, TokenCredentials


class TestCredentials:
    @patch("pyhyves.pyhyves.HyvesOAuth2Client")
    @patch("pyhyves.pyhyves.HyvesClient")
    def test_passes_token_credentials(self, mock_hyves_client, mock_oauth_client):
        credentials = TokenCredentials(access_token="some token")

        Pyhyves(credentials)

        mock_oauth_client.assert_called_once_with(credentials)
        mock_hyves_client.assert_called_once_with(mock_oauth_client.return_value)

    @patch("pyhyves.pyhyves.HyvesOAuth2Client")
    @patch("pyhyves.pyhyves.HyvesClient")
    def test_passes_password_credentials(self, mock_hyves_client, mock_oauth_client):
        credentials = PasswordCredentials(login_id="user", password="password")

        Pyhyves(credentials)

        mock_oauth_client.assert_called_once_with(credentials)
        mock_hyves_client.assert_called_once_with(mock_oauth_client.return_value)

    @patch("pyhyves.pyhyves.HyvesOAuth2Client")
    @patch("pyhyves.pyhyves.HyvesClient")
    def test_works_without_credentials(self, mock_hyves_client, mock_oauth_client):
        Pyhyves()

        mock_oauth_client.assert_called_once_with(None)
        mock_hyves_client.assert_called_once_with(mock_oauth_client.return_value)


class TestLifecycle:
    @pytest.mark.asyncio
    async def test_aclose_closes_client(self):
        pyhyves = Pyhyves()
        try:
            with patch.object(pyhyves._http, "aclose", new=AsyncMock()) as mock_close:
                await pyhyves.aclose()
            mock_close.assert_awaited_once()
        finally:
            await pyhyves._http.aclose()

    @pytest.mark.asyncio
    async def test_context_manager_closes_client(self):
        async with Pyhyves() as pyhyves:
            client = pyhyves._http

        assert client.is_closed