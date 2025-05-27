import oci
from datetime import datetime, timedelta

# Load config and clients
config = oci.config.from_file()
identity_client = oci.identity.IdentityClient(config)
tenancy_id = config['tenancy']

# Configuration
cutoff_days = 45
cutoff_date = datetime.utcnow() - timedelta(days=cutoff_days)
service_tag_namespace = "user_tags"
service_tag_key = "service_user"
service_tag_value = "true"
inactive_group_name = "InactiveUsers"

# Helper: Get group OCID
def get_group_id_by_name(name):
    groups = oci.pagination.list_call_get_all_results(identity_client.list_groups, tenancy_id).data
    for group in groups:
        if group.name == name:
            return group.id
    raise Exception(f"Group '{name}' not found.")

inactive_group_id = get_group_id_by_name(inactive_group_name)

# Step 1: Find all active users
users = oci.pagination.list_call_get_all_results(identity_client.list_users, tenancy_id).data
disabled_users = []

for user in users:
    if user.lifecycle_state != "ACTIVE":
        continue

    try:
        user_info = identity_client.get_user(user.id).data

        # Skip tagged service users
        tags = user_info.defined_tags or {}
        if tags.get(service_tag_namespace, {}).get(service_tag_key, "").lower() == service_tag_value:
            print(f"[SKIP] Service user: {user.name}")
            continue

        last_login = user_info.time_last_login
        if not last_login or last_login < cutoff_date:
            disabled_users.append(user)

    except Exception as e:
        print(f"[ERROR] Skipping user {user.name}: {e}")

# Step 2: Disable login and move to restricted group
for user in disabled_users:
    print(f"[*] Processing inactive user: {user.name}")

    # Disable login
    identity_client.update_user(
        user.id,
        oci.identity.models.UpdateUserDetails(is_login_allowed=False)
    )

    # Remove from all groups
    user_groups = identity_client.list_user_group_memberships(tenancy_id, user_id=user.id).data
    for membership in user_groups:
        identity_client.delete_user_from_group(membership.id)

    # Add to InactiveUsers group
    identity_client.add_user_to_group(
        oci.identity.models.AddUserToGroupDetails(
            user_id=user.id,
            group_id=inactive_group_id
        )
    )

    print(f"[✔] User '{user.name}' disabled and moved to 'InactiveUsers' group.")

print(f"\n[✔] Completed. {len(disabled_users)} users processed.")
