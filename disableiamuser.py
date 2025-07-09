import oci
from datetime import datetime, timedelta

### Configuration
DAYS_THRESHOLD = 15
TENANCY_OCID = "<TENANCY_OCID>"
TOPIC_OCID = "<TOPIC_OCID>"

# OCI Clients (use resource principal in OCI Functions or config locally)
config = oci.config.from_file(file_location='<Location of Config File>', profile_name='DEFAULT')
identity = oci.identity.IdentityClient(config)
ons = oci.ons.NotificationDataPlaneClient(config)

# Track affected users
disabled_users = []

# Fetch all users
users = identity.list_users(compartment_id=TENANCY_OCID).data

for user in users:
    if user.lifecycle_state != "ACTIVE":
        continue

    # Get detailed user info
    user_details = identity.get_user(user.id).data
    last_login = user_details.last_successful_login_time
    tag = identity.get_user(user.id).data.defined_tags

    if 'trial' in tag and tag['trial'].get('App-Name') == 'ServiceUser':
        continue

    # Skip users with no login record
    if last_login is None:
        continue;

    days_inactive = (datetime.utcnow() - last_login.replace(tzinfo=None)).days

    if days_inactive >= DAYS_THRESHOLD:
        actions = []

        # 1. Disable Console Login

        identity.update_user_capabilities(user.id, update_user_capabilities_details = oci.identity.models.UpdateUserCapabilitiesDetails(can_use_console_password=False))
        actions.append("🔒 Console access disabled")
        actions.append(f"User OCID impacted is {user.id}")

        # 2. Revoke API Keys
        api_keys = identity.list_api_keys(user.id).data
        for key in api_keys:
            identity.delete_api_key(user.id, key.fingerprint)
        if api_keys:
            actions.append(f"🗝️ Revoked {len(api_keys)} API key(s)")

        # 3. Revoke Auth Tokens
        tokens = identity.list_auth_tokens(user.id).data
        for token in tokens:
            identity.delete_auth_token(user.id, token.id)
        if tokens:
            actions.append(f"📛 Revoked {len(tokens)} auth token(s)")

        # Collect results
        disabled_users.append(
            f"👤 {user.name} ({user.description or 'No Description'}) - "
            f"Last login: {last_login.strftime('%Y-%m-%d')}\n" +
            "  " + "\n  ".join(actions)
        )

# Prepare message
if disabled_users:
    body = (
        "⚠️ IAM Compliance Action: Inactive Users Locked & Credentials Revoked (>= 45 days)\n\n"
        + "\n\n".join(disabled_users)
    )
else:
    body = "✅ IAM Compliance Check: No inactive users found over 45 days."

# Send Notification
ons.publish_message(
    topic_id=TOPIC_OCID,
    message_details=oci.ons.models.MessageDetails(
        title="OCI IAM Compliance Report",
        body=body
    )
)

print("✅ IAM audit completed and notification sent.")
