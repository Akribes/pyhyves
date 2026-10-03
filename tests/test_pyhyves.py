from unittest.mock import MagicMock, patch

from pyhyves import PasswordCredentials, Pyhyves, TokenCredentials


class TestCredentials:
    @patch("pyhyves.pyhyves.TokenAuth")
    def test_passes_token_credentials(self, mock_token_auth):
        credentials = TokenCredentials(access_token="some token")
        mock_token_auth.return_value = MagicMock()

        pyhyves = Pyhyves(credentials)

        mock_token_auth.assert_called_once_with(credentials)
        assert pyhyves._client._auth is mock_token_auth.return_value

    @patch("pyhyves.pyhyves.PasswordAuth")
    def test_passes_password_credentials(self, mock_password_auth):
        credentials = PasswordCredentials(login_id="user", password="password")
        mock_password_auth.return_value = MagicMock()

        pyhyves = Pyhyves(credentials)

        mock_password_auth.assert_called_once()
        assert mock_password_auth.call_args[0][1] is credentials
        assert pyhyves._client._auth is mock_password_auth.return_value

    def test_works_without_credentials(self):
        pyhyves = Pyhyves()
        assert pyhyves._client._auth is None
