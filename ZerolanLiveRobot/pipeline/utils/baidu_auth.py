import requests
from typeguard import typechecked


@typechecked
def get_baidu_access_token(api_key: str, secret_key: str) -> str:
    """
    Get Baidu access token using API key and secret key.
    :return: access_token string
    :raises ValueError: if token retrieval fails
    """
    url = "https://aip.baidubce.com/oauth/2.0/token"
    params = {
        "grant_type": "client_credentials",
        "client_id": api_key,
        "client_secret": secret_key,
    }
    response = requests.post(url, params=params)
    response.raise_for_status()
    token = response.json().get("access_token")
    if token is None:
        raise ValueError(
            "Failed to get Baidu access token. Check your API key and secret key."
        )
    return str(token)
