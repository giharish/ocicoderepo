import oci
from oci.auth import signers
import pandas as pd
from datetime import datetime
import smtplib
from email.message import EmailMessage
import os
import requests
from dateutil import tz
# List of Compartment OCIDS (Compartment IDs)
compartment_ids = [
    "Compartment-1",
    "Compartment-2"
]
region = "ap-mumbai-1"
# Email Configuration
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_FROM = "<sender email>"
EMAIL_PASSWORD = "<password>"  # App password if Gmail
EMAIL_TO = ["recipient_email_address]
EMAIL_SUBJECT = "OCI Volumes Backup Report"

# Output Excel file
output_file = "oci_volume_backups.xlsx"

# Use instance principal signer
signer = signers.InstancePrincipalsSecurityTokenSigner()

# Get tenancy and region from instance metadata
identity_client = oci.identity.IdentityClient(config={}, signer=signer)
tenancy_id = signer.tenancy_id

# Create database client using instance principal
bv_client = oci.core.BlockstorageClient(config={"region": region}, signer=signer)

all_backup_data = []

def make_timezone_naive(dt):
    if dt is not None and dt.tzinfo is not None:
        return dt.astimezone(tz.tzlocal()).replace(tzinfo=None)
    return dt

for compartment_id in compartment_ids:
    try:
        block_backups = bv_client.list_volume_backups(compartment_id=compartment_id).data
        for backup in block_backups:
            all_backup_data.append({
                "Volume ID": backup.volume_id,
                "Compartment": backup.compartment_id,
                "Backup Name": backup.display_name,
                "Backup ID": backup.id,
                "Type": backup.type,
                "Status": backup.lifecycle_state,
                "Created Time": make_timezone_naive(backup.time_created),
                "Size (GB)": round(backup.size_in_gbs or 0, 2),
                "Expiration Time": backup.expiration_time
            })
    except Exception as e:
        all_backup_data.append({
            "DB ID": backup.volume_id,
            "Backup ID": "ERROR",
            "Type": "-",
            "Status": str(e),
            "Start Time": None,
            "Size (GB)": "-",
            "Expiration Time": "-"
        })
    try:
        boot_backups = bv_client.list_boot_volume_backups(compartment_id=compartment_id).data
        for backup in boot_backups:
            all_backup_data.append({
                "Volume ID": backup.boot_volume_id,
                "Compartment": backup.compartment_id,
                "Backup Name": backup.display_name,
                "Backup ID": backup.id,
                "Type": backup.type,
                "Status": backup.lifecycle_state,
                "Created Time": make_timezone_naive(backup.time_created),
                "Size (GB)": round(backup.size_in_gbs or 0, 2),
                "Expiration Time": backup.expiration_time
            })
    except Exception as e:
        all_backup_data.append({
            "DB ID": backup.boot_volume_id,
            "Backup ID": "ERROR",
            "Type": "-",
            "Status": str(e),
            "Start Time": None,
            "Size (GB)": "-",
            "Expiration Time": "-"
        })


# ---------- Save to Excel ----------
df = pd.DataFrame(all_backup_data)
df.to_excel(output_file, index=False)

# ---------- Send Email ----------

msg = EmailMessage()
msg["Subject"] = EMAIL_SUBJECT
msg["From"] = EMAIL_FROM
msg["To"] = ", ".join(EMAIL_TO)
msg.set_content("Hi Team,\n\nPlease find attached the latest Oracle Volume backup report.\n\nRegards,\nAutomation Script")

# Attach Excel
with open(output_file, "rb") as f:
    file_data = f.read()
    msg.add_attachment(file_data, maintype="application", subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename=output_file)

# Send via SMTP
with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
    server.starttls()
    server.login(EMAIL_FROM, EMAIL_PASSWORD)
    server.send_message(msg)

print(f"✅ Email sent with {output_file} attached.")
