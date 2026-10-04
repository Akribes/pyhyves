from unittest.mock import MagicMock, patch

from pyhyves import PasswordCredentials, Pyhyves, TokenCredentials


class TestCredentials:
    @patch("pyhyves.pyhyves.TokenAuth")
    @patch("pyhyves.pyhyves.HyvesClient")
    def test_passes_token_credentials(self, mock_hyves_client, mock_token_auth):
        credentials = TokenCredentials(access_token="some token")
        mock_token_auth.return_value = MagicMock()

        Pyhyves(credentials)

        mock_token_auth.assert_called_once_with(credentials)
        mock_hyves_client.assert_called_once()
        assert mock_hyves_client.call_args[1]["auth"] is mock_token_auth.return_value

    @patch("pyhyves.pyhyves.PasswordAuth")
    @patch("pyhyves.pyhyves.HyvesClient")
    def test_passes_password_credentials(self, mock_hyves_client, mock_password_auth):
        credentials = PasswordCredentials(login_id="user", password="password")
        mock_password_auth.return_value = MagicMock()

        Pyhyves(credentials)

        mock_password_auth.assert_called_once()
        assert mock_password_auth.call_args[0][1] is credentials
        mock_hyves_client.assert_called_once()
        assert mock_hyves_client.call_args[1]["auth"] is mock_password_auth.return_value

    @patch("pyhyves.pyhyves.HyvesClient")
    def test_works_without_credentials(self, mock_hyves_client):
        Pyhyves()
        assert mock_hyves_client.call_args[1]["auth"] is None
