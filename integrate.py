
import requests

headers = {
    'Authorization': 'Bearer <access_token>',
    'Content-Type': 'application/json',
    'Accept': 'application/json',
}

response = requests.get('https://api.pinterest.com/v5/pins/{2955556002688113}?={2955556002688113}', headers=headers)
        