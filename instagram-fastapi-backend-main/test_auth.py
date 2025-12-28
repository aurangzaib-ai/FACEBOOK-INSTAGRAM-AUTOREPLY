from google.oauth2.service_account import Credentials
import google.auth.transport.requests

creds = Credentials.from_service_account_file(
    "service_account.json",
    scopes=["https://www.googleapis.com/auth/cloud-platform"]
)

request = google.auth.transport.requests.Request()

try:
    creds.refresh(request)
    print("AUTH OK")
except Exception as e:
    print("AUTH FAILED:", e)
