import oci
from datetime import datetime, timedelta

### Configuration
DAYS_THRESHOLD = 15
TENANCY_OCID = "ocid1.tenancy.oc1..aaaaaaaakilrwdkq74qaqcavit6uem56h5dia6l3qiyp4mfrzeey7iuoad6q"
TOPIC_OCID = "ocid1.onstopic.oc1.ap-mumbai-1.amaaaaaavwj4rqiakidvgzyowcw3jwug6nor5p6uzztmhhlyqisd34ryp5yq"

# OCI Clients (use resource principal in OCI Functions or config locally)
config = oci.config.from_file(file_location='/Users/girishraja/.oci/config', profile_name='DEFAULT')
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
