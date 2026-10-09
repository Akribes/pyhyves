# This client ID is used by the web app. Other client IDs are rejected
HYVES_CLIENT_ID = "38e5b2e0-67de-4150-b71c-0e744b0ac489"

HYVES_AUTHORIZATION_URL = "https://auth.hyves.nl/oauth2/authorize"
HYVES_TOKEN_URL = "https://auth.hyves.nl/oauth2/token"
HYVES_API_URL = "https://api.hyves.nl"

# We cannot actually receive this redirect, so it is only used to satisfy the authorization server, which rejects all
# other redirect URLs. We intercept the authorization code from the redirect ourselves.
HYVES_REDIRECT_URL = "https://hyves.nl/auth"

HYVES_SCOPE = "openid offline_access"

BATCHED_REQUEST_LIMIT = 20
