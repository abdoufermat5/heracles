import requests
import sys
import os
import json
import time

BASE_URL = "http://localhost:8000/api/v1"
USERNAME = "hrc-admin"
PASSWORD = "hrc-admin-secret"

# We will use the default base DN provided by the environment or a mock one if testing context.
# To test context, we would need a secondary department/OU. 
# For now, we will just verify that passing base_dn DOES NOT FAIL, 
# and potentially verify it creates things in the right place if we can read them back.
# Since we might not have a second department set up, we will use the default BASE_DN 
# but explicitly pass it as 'base_dn' parameter to ensure the API accepts it.
# We can also try a "fake" base_dn to see if it fails (which would prove it is being used).

def get_token():
    url = f"{BASE_URL}/auth/token"
    # Try different content types / patterns if standard doesn't work
    # Heracles uses OAuth2 password flow usually
    response = requests.post(url, data={
        "username": USERNAME, 
        "password": PASSWORD
    })
    if response.status_code != 200:
        print(f"Failed to login: {response.status_code} {response.text}")
        sys.exit(1)
    return response.json()["access_token"]

def verify_posix_groups(token, base_dn):
    print("\n--- Verifying POSIX Groups ---")
    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. List Groups with base_dn
    print(f"Listing POSIX groups with base_dn={base_dn}...")
    try:
        response = requests.get(f"{BASE_URL}/posix/groups", params={"base_dn": base_dn}, headers=headers)
        if response.status_code == 200:
            print(f"SUCCESS: List Posix Groups (Status 200)")
        else:
            print(f"FAILURE: List Posix Groups (Status {response.status_code}) - {response.text}")
    except Exception as e:
        print(f"EXCEPTION: {e}")

    # 2. Create Group with base_dn
    group_cn = f"test-ctx-group-{int(time.time())}"
    print(f"Creating POSIX group '{group_cn}' with base_dn={base_dn}...")
    data = {
        "cn": group_cn,
        "description": "Context Aware Test Group",
        "gidNumber": -1 # Auto allocate
    }
    
    # Need to check Schema for expected fields. PosixGroupFullCreate: cn, gidNumber (optional?), description (optional)
    # If gidNumber is required in API schema but optional in logic...
    # Assuming -1 or omitting triggers auto-allocation. Let's try omitting if it fails.
    
    response = requests.post(f"{BASE_URL}/posix/groups", params={"base_dn": base_dn}, json=data, headers=headers)
    if response.status_code == 201:
        print(f"SUCCESS: Create Posix Group (Status 201)")
        created_group = response.json()
    else:
        print(f"FAILURE: Create Posix Group (Status {response.status_code}) - {response.text}")
        return

    # 3. Get Group with base_dn
    print(f"Getting POSIX group '{group_cn}' with base_dn={base_dn}...")
    response = requests.get(f"{BASE_URL}/posix/groups/{group_cn}", params={"base_dn": base_dn}, headers=headers)
    if response.status_code == 200:
        print(f"SUCCESS: Get Posix Group (Status 200)")
    else:
        print(f"FAILURE: Get Posix Group (Status {response.status_code}) - {response.text}")

    # 4. Update Group with base_dn
    print(f"Updating POSIX group '{group_cn}' with base_dn={base_dn}...")
    update_data = {"description": "Updated Description"}
    response = requests.put(f"{BASE_URL}/posix/groups/{group_cn}", params={"base_dn": base_dn}, json=update_data, headers=headers)
    if response.status_code == 200:
        print(f"SUCCESS: Update Posix Group (Status 200)")
    else:
        print(f"FAILURE: Update Posix Group (Status {response.status_code}) - {response.text}")

    # 5. Delete Group with base_dn
    print(f"Deleting POSIX group '{group_cn}' with base_dn={base_dn}...")
    response = requests.delete(f"{BASE_URL}/posix/groups/{group_cn}", params={"base_dn": base_dn}, headers=headers)
    if response.status_code == 204:
        print(f"SUCCESS: Delete Posix Group (Status 204)")
    else:
        print(f"FAILURE: Delete Posix Group (Status {response.status_code}) - {response.text}")

def main():
    try:
        token = get_token()
        print("Logged in successfully.")
        
        # We need a valid base_dn. 
        # Typically "dc=heracles,dc=local" or similar.
        # We can fetch it from config or guess.
        # Let's try to infer from a normal list call response or just hardcode if known.
        # `os.environ` might not have it if we run outside container.
        # But we can try "dc=heracles,dc=local" which is common default in this project.
        
        test_base_dn = "dc=heracles,dc=local" 
        # Or if we want to test "filtering", we try the SAME base_dn as default, 
        # which should behave identically to no param, but prove parameters are accepted.
        
        verify_posix_groups(token, test_base_dn)
        
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
