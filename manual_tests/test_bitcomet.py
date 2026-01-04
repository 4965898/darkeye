import requests

BASE_URL = "http://10.43.108.218:19259"
USERNAME = "yinruizhe"
PASSWORD = "1qw23er4"
from requests.auth import HTTPBasicAuth

session = requests.Session()
session.auth = (USERNAME, PASSWORD)

session = requests.Session()

resp = session.get(
    f"{BASE_URL}",
        data={
        "username": "yinruizhe",
        "password": "1qw23er4"
    }
)

print(resp.status_code)


