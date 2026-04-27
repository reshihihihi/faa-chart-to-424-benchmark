# Rerun Policy

## Principle

Reruns must explain failure recovery, not silently improve performance.

## Allowed Rerun Reasons

- API transport failure
- provider timeout
- corrupted raw response
- pre-registered parser failure that affects all methods consistently
- infrastructure crash before output was saved

## Not Allowed Without New Version

- changing a prompt after seeing evaluation errors
- changing parser repair to fix one method's outputs
- changing schema to accept known invalid outputs
- changing model version or model settings without a new run id
- dropping failed samples

## Required Rerun Record

Every rerun must record:

- original run id
- new run id
- method id
- sample ids affected
- reason
- prompt hash
- model config hash
- parser repair policy hash
- scorer version
- timestamp
- whether the rerun is eligible for formal reporting

