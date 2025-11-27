import requests
import time

# GitHub Copilot Client ID (VS Code)
CLIENT_ID = "Iv1.b507a08c87ecfe98"

def get_device_code():
    response = requests.post(
        "https://github.com/login/device/code",
        headers={"Accept": "application/json"},
        json={"client_id": CLIENT_ID, "scope": "read:user"}
    )
    response.raise_for_status()
    return response.json()

def get_token(device_code, interval):
    while True:
        time.sleep(interval)
        response = requests.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            json={
                "client_id": CLIENT_ID,
                "device_code": device_code,
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code"
            }
        )
        response.raise_for_status()
        data = response.json()
        
        if "access_token" in data:
            return data["access_token"]
        
        if "error" in data:
            if data["error"] == "authorization_pending":
                continue
            if data["error"] == "slow_down":
                interval += 5
                continue
            if data["error"] == "expired_token":
                print("Code expired, please try again.")
                return None
            print(f"Error: {data['error']}")
            return None

def main():
    print("Requesting device code...")
    try:
        data = get_device_code()
        device_code = data["device_code"]
        user_code = data["user_code"]
        verification_uri = data["verification_uri"]
        interval = data["interval"]

        print(f"\nPlease visit: {verification_uri}")
        print(f"And enter code: {user_code}")
        print("\nWaiting for authentication...")

        token = get_token(device_code, interval)
        
        if token:
            print("\nSuccess! Here is your Copilot Token:")
            print("-" * 50)
            print(token)
            print("-" * 50)
            print("Copy this token to your .env file as COPILOT_TOKEN")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
