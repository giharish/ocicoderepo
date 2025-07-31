#!/bin/bash

TENANCY_OCID="ocid1.tenancy.oc1..aaaaaaaaczy2ya4mb6y6wc7hewnixcduhgplx43xx6vdv5qy3j3qjyagnbia"
OUTPUT_FILE="oci_users_with_groups.csv"

echo "User OCID,User Name,Email,Group OCID,Group Name,Last Login,Status" > "$OUTPUT_FILE"

# Get all users in the tenancy
users=$(oci iam user list --compartment-id "$TENANCY_OCID" --all --query 'data[*].{id:id, name:name,email:email,lastlogin:"last-successful-login-time",status:"lifecycle-state"}' --profile=CIFCLSV6 --raw-output)

# Loop over each user
echo "$users" | jq -c '.[]' | while read user; do
  user_id=$(echo "$user" | jq -r '.id')
  user_name=$(echo "$user" | jq -r '.name')
  user_email=$(echo "$user" | jq -r '.email')
  user_lastlogin=$(echo "$user" | jq -r '.lastlogin')
  user_status=$(echo "$user" | jq -r '.status')

  # Get groups for each user
  groups=$(oci iam user list-groups --user-id "$user_id" --query 'data[*].{id:id, name:name}' --raw-output --profile=CIFCLSV6)

  if [[ $(echo "$groups" | jq length) -eq 0 ]]; then
    echo "$user_id,$user_name,," >> "$OUTPUT_FILE"
  else
    echo "$groups" | jq -c '.[]' | while read group; do
      group_id=$(echo "$group" | jq -r '.id')
      group_name=$(echo "$group" | jq -r '.name')
      echo "$user_id,$user_name,$user_email,$group_id,$group_name,$user_lastlogin,$user_status" >> "$OUTPUT_FILE"
    done
  fi
done

echo "✅ Exported to $OUTPUT_FILE"
