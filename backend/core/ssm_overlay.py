import os

def apply_ssm_overlay(client=None) -> int:
    prefix = os.environ.get("SSM_PREFIX")
    if not prefix:
        return 0
    
    import boto3
    from botocore.exceptions import ClientError
    
    if client is None:
        client = boto3.client("ssm")
    
    count = 0
    paginator = client.get_paginator('get_parameters_by_path')
    try:
        for page in paginator.paginate(Path=prefix, WithDecryption=True, Recursive=True):
            for param in page.get("Parameters", []):
                name = param["Name"].split("/")[-1].upper()
                if name not in os.environ:
                    os.environ[name] = param["Value"]
                count += 1
    except Exception as e:
        raise RuntimeError(f"SSM overlay failed: {e}")
    return count
