#!/bin/bash

scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

set -eo pipefail

RUNNER_BASE_PATH=$(pwd)
VM_BASE_NAME="gitlab-${CUSTOM_ENV_CI_PROJECT_NAME}-${CUSTOM_ENV_NAME}-${CUSTOM_ENV_CI_JOB_ID}"
VM_BASE_IMAGE="${CUSTOM_ENV_NAME}.qcow2"

SUFFIX=$(head /dev/urandom | tr -dc "a-z0-9" | head -c8)
VM_NAME="${VM_BASE_NAME}-${SUFFIX}"
VM_IMAGE="${VM_NAME}.qcow2"

# save the machine and image name - we'll need it in the run & cleanup stages
echo -e "VM_NAME=${VM_NAME}\nVM_IMAGE=${VM_IMAGE}" > "./job${CUSTOM_ENV_CI_JOB_ID}"

# we'll create a throwaway overlay storage for the CI machine
echo "Creating overlay volume '${VM_IMAGE}'"
virsh vol-create-as \
    --name ${VM_IMAGE} \
    --pool default \
    --capacity 10G \
    --format qcow2 \
    --backing-vol ${VM_BASE_IMAGE} \
    --backing-vol-format qcow2

# create a transient runner machine
echo "Creating virtual machine '${VM_NAME}'"
virt-install \
    --name "${VM_NAME}" \
    --disk vol="default/${VM_IMAGE}" \
    --vcpus=4 \
    --ram=4096 \
    --network default \
    --graphics none \
    --transient \
    --noautoconsole \
    --import

# turn off "pipefail" as we need to continually test whether SSH has finally been started in
# the machine and SSH would exit with 255, failing the whole script
set +e pipefail
echo "Waiting for SSH"
for i in $(seq 1 30); do
    ssh -i ${scriptdir}/id_ed25519 -o StrictHostKeyChecking=no gitlab-runner@${VM_NAME} true &>/dev/null

    if [ $? -eq 0 ]; then
        break
    fi

    if [ $i -eq 30 ];then
        echo "Waited 30 seconds for VM to start, exiting..."
        exit 1
    fi

    sleep 1
done

#echo "Updating the machine"
#${scriptdir}/libvirt-ci.git/lcitool update "${VM_NAME}" libvirt

echo "============"
echo "PREPARE DONE"
echo "============"
