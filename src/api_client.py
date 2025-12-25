import json

import requests


class APIClient:
    """
    A reusable client for interacting with the Node.js backend API.
    Handles base URL, headers, and authentication tokens.
    """

    def __init__(self, base_url="http://localhost:3000"):
        self.base_url = base_url
        self.headers = {
            "Content-Type": "application/json"
        }
        self.auth_token = None

    def _handle_auth_response(self, response_data):
        """
        [NEW METHOD] Processes a successful login response to extract and set the token.
        """
        token = response_data.get("data", {}).get("token")

        if token:
            self.auth_token = token
            print("🔑 Login Successful! Token stored for subsequent requests.")
            return True
        else:
            print("⚠️ Login Success but no token found in response. Cannot proceed with protected routes.")
            return False

    def _handle_error_response(self, endpoint, status_code, response_text):
        """
        [NEW METHOD] Standardized logging for API errors.
        """
        print(f"❌ Request to {endpoint} failed.")
        print(f"   Status: {status_code}")
        try:
            # Try to pretty-print JSON error details if available
            error_data = json.loads(response_text)
            print(f"   Details: {error_data.get('message', 'No specific error message provided.')}")
        except json.JSONDecodeError:
            print(f"   Raw Response: {response_text}")

    def _request(self, method, endpoint, data=None):
        # ... (This method remains the same, it handles I/O only) ...
        """
        Internal, abstracted method to handle all HTTP requests.
        """
        url = self.base_url + endpoint

        # Add Authorization header if a token is available
        if self.auth_token:
            self.headers["Authorization"] = f"Bearer {self.auth_token}"

        print(f"\n[REQUEST] ➡️ {method} {url}")

        try:
            # Use the requests library to execute the call
            response = requests.request(
                method,
                url,
                json=data,
                headers=self.headers
            )

            return response

        except requests.exceptions.ConnectionError:
            print("\n[ERROR] 💥 Connection Error!")
            print("Ensure the Node.js backend is running and listening on the correct port.")
            return None
        except Exception as e:
            print(f"\n[ERROR] An unexpected error occurred: {e}")
            return None

    def login(self, name):
        """
        [REFACTORED] Specific method for the /api/login endpoint.
        Focuses only on making the request and delegating response handling.
        """
        endpoint = "/api/users/login"
        payload = {"name": name}

        response = self._request("POST", endpoint, data=payload)

        if response is not None:
            print(f"[RESPONSE] ✅ Status: {response.status_code}")
            response_data = None
            try:
                response_data = response.json()
            except json.JSONDecodeError:
                pass

            if response.status_code in [200, 201]:
                # DELEGATE: Handle state update (token setting)
                if response_data and self._handle_auth_response(response_data):
                    return response_data

            # DELEGATE: Handle error logging if login failed or was an empty success
            self._handle_error_response(endpoint, response.status_code, response.text)

        return None

    def get_user_accounts(self):
        """
        [UPDATED] Example of a protected endpoint that uses the new error handler.
        """
        endpoint = f"/api/accounts"

        if not self.auth_token:
            print("🚫 Error: Cannot access protected endpoint. Please log in first.")
            return None

        response = self._request("GET", endpoint)

        if response is not None:
            print(f"[RESPONSE] ✅ Status: {response.status_code}")

            if response.status_code == 200:
                print("👤 Profile retrieved successfully.")
                return response.json()
            else:
                # Use the new error handler for failed protected requests
                self._handle_error_response(endpoint, response.status_code, response.text)
        return None
