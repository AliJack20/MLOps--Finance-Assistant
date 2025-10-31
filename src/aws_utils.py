import boto3
import time
import logging

logging.basicConfig(level=logging.INFO)

def start_ec2_instance(instance_id: str, region) -> str:
    """Start EC2 instance and return its public IP when ready."""
    ec2 = boto3.client('ec2',region_name=region)
    
    logging.info(f"Starting EC2 instance: {instance_id}")
    ec2.start_instances(InstanceIds=[instance_id])

    # Wait until running
    logging.info("Waiting for instance to be running...")
    waiter = ec2.get_waiter('instance_running')
    waiter.wait(InstanceIds=[instance_id])

    # Get public IP
    reservations = ec2.describe_instances(InstanceIds=[instance_id])['Reservations']
    instance = reservations[0]['Instances'][0]
    public_ip = instance.get('PublicIpAddress')

    logging.info(f"Instance is running at: {public_ip}")
    return public_ip


def stop_ec2_instance(instance_id: str, region):
    """Stop EC2 instance."""
    ec2 = boto3.client('ec2',region_name=region)
    logging.info(f"Stopping EC2 instance: {instance_id}")
    ec2.stop_instances(InstanceIds=[instance_id])
    logging.info("EC2 instance stopped.")
