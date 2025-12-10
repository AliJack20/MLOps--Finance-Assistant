import boto3
import time
import logging
import paramiko

logging.basicConfig(level=logging.INFO)


def start_ec2_instance(instance_id: str, region) -> str:
    """Start EC2 instance and return its public IP when ready."""
    ec2 = boto3.client("ec2", region_name=region)

    logging.info(f"Starting EC2 instance: {instance_id}")
    ec2.start_instances(InstanceIds=[instance_id])

    # Wait until running
    logging.info("Waiting for instance to be running...")
    waiter = ec2.get_waiter("instance_running")
    waiter.wait(InstanceIds=[instance_id])

    # Get public IP
    reservations = ec2.describe_instances(InstanceIds=[instance_id])["Reservations"]
    instance = reservations[0]["Instances"][0]
    public_ip = instance.get("PublicIpAddress")

    logging.info(f"Instance is running at: {public_ip}")
    return public_ip


def stop_ec2_instance(
    instance_id: str, region: str, key_path: str, username="ec2-user"
):
    """Stop Docker containers and then stop EC2 instance."""
    ec2 = boto3.client("ec2", region_name=region)

    # Get instance public IP
    desc = ec2.describe_instances(InstanceIds=[instance_id])
    public_ip = desc["Reservations"][0]["Instances"][0]["PublicIpAddress"]

    logging.info("Connecting to EC2 via SSH to stop Docker containers...")
    key = paramiko.RSAKey.from_private_key_file(key_path)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    # Wait a few seconds in case the instance just came online
    time.sleep(10)
    ssh.connect(public_ip, username=username, pkey=key)

    # Stop and remove all running containers
    docker_cleanup_cmd = (
        "cd /home/ec2-user/MLOps--Finance-Assistant && "
        "docker ps -q | xargs -r docker stop && "
        "docker ps -a -q | xargs -r docker rm"
    )
    logging.info("Stopping and removing all Docker containers...")
    stdin, stdout, stderr = ssh.exec_command(docker_cleanup_cmd)
    logging.info(stdout.read().decode())
    err = stderr.read().decode()
    if err:
        logging.error(err)

    ssh.close()

    # Finally, stop the EC2 instance
    logging.info(f"Stopping EC2 instance: {instance_id}")
    ec2.stop_instances(InstanceIds=[instance_id])
    logging.info("EC2 instance stopped successfully.")


def run_docker_commands_on_ec2(instance_id, region, key_path, username="ec2-user"):
    ec2 = boto3.client("ec2", region_name=region)

    # Wait for instance to be running
    logging.info("Waiting for EC2 instance to be running...")
    waiter = ec2.get_waiter("instance_running")
    waiter.wait(InstanceIds=[instance_id])

    # Get public IP
    desc = ec2.describe_instances(InstanceIds=[instance_id])
    public_ip = desc["Reservations"][0]["Instances"][0]["PublicIpAddress"]
    logging.info(f"Instance running at: {public_ip}")

    # Wait for SSH to be ready
    logging.info("Waiting 60 seconds for SSH to become available...")
    time.sleep(60)

    # Connect via SSH
    logging.info("Connecting via SSH...")
    key = paramiko.RSAKey.from_private_key_file(key_path)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(public_ip, username=username, pkey=key)

    # Run docker commands
    # Run the deploy script directly
    command = (
        "cd /home/ec2-user/MLOps--Finance-Assistant && "
        "chmod +x deploy_fastapi.sh && "
        "./deploy_fastapi.sh"
    )

    logging.info(f"Running: {command}")
    stdin, stdout, stderr = ssh.exec_command(command)
    logging.info(stdout.read().decode())
    err = stderr.read().decode()
    if err:
        logging.error(err)

    ssh.close()
    logging.info("Docker build and run completed.")
    return public_ip
