import requests


def get_users(url, token):
    """
    Fetches user data from the JupyterHub API.

    Args:
        url (str): Unused label (kept for call-site compatibility).
        token (str): API token.

    Returns:
        list: List of user dicts.
    """
    all_data = []
    api_url = 'https://edx.datahub.berkeley.edu/hub/api'
    offset = 0
    while True:
        r = requests.get(
            api_url + f'/users?limit=200&offset={offset}',
            headers={
                'Authorization': f'token {token}'
            }
        )
        if r.status_code == 403:
            print(f"{url}: 403 error")
            return []
        if r.status_code != 200:
            print(r.status_code)
            print(r.text)
            raise Exception("Error getting users")
        r.raise_for_status()
        data = r.json()
        all_data.extend(data)
        # Stop if we got fewer than 200 users (indicating end of results)
        if len(data) < 200:
            break
        offset += 200
    return all_data
