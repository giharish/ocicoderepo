#!/bin/bash

TENANCY_OCID="ocid1.tenancy.oc1..aaaaaaaakilrwdkq74qaqcavit6uem56h5dia6l3qiyp4mfrzeey7iuoad6q"
OUTPUT_FILE="oci_users_with_groups.csv"

echo "User OCID,User Name,Group OCID,Group Name" > "$OUTPUT_FILE"

# Get all users in the tenancy
users=$(oci iam user list --compartment-id "$TENANCY_OCID" --all --query 'data[*].{id:id, name:name}' --raw-output)

# Loop over each user
echo "$users" | jq -c '.[]' | while read user; do
  user_id=$(echo "$user" | jq -r '.id')
  user_name=$(echo "$user" | jq -r '.name')

  # Get groups for each user
  groups=$(oci iam user list-groups --user-id "$user_id" --query 'data[*].{id:id, name:name}' --raw-output)

  if [[ $(echo "$groups" | jq length) -eq 0 ]]; then
    echo "$user_id,$user_name,," >> "$OUTPUT_FILE"
  else
    echo "$groups" | jq -c '.[]' | while read group; do
      group_id=$(echo "$group" | jq -r '.id')
      group_name=$(echo "$group" | jq -r '.name')
      echo "$user_id,$user_name,$group_id,$group_name" >> "$OUTPUT_FILE"
    done
  fi
done

echo "✅ Exported to $OUTPUT_FILE"
