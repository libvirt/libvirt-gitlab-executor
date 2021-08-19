#!/bin/bash

scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
source "./job${CUSTOM_ENV_CI_JOB_ID}"

ssh -i "${scriptdir}/id_ed25519" \
    -o StrictHostKeyChecking=no \
    gitlab-runner@"${VM_NAME}" /bin/bash < "$1"
