import boto3

session = boto3.Session(profile_name='praveen-devkraft')
ec2 = session.client('ec2', region_name='ap-south-1')

# Saare SGs lo
all_sgs = ec2.describe_security_groups()['SecurityGroups']
all_sg_ids = {sg['GroupId']: sg['GroupName'] for sg in all_sgs}

used_sg_ids = set()

# EC2 instances mein use ho rahe SGs
instances = ec2.describe_instances()['Reservations']
for r in instances:
    for i in r['Instances']:
        for sg in i.get('SecurityGroups', []):
            used_sg_ids.add(sg['GroupId'])

# ELB (Load Balancers) mein use ho rahe SGs
try:
    elb = session.client('elbv2', region_name='ap-south-1')
    lbs = elb.describe_load_balancers()['LoadBalancers']
    for lb in lbs:
        for sg in lb.get('SecurityGroups', []):
            used_sg_ids.add(sg)
except Exception as e:
    print(f"ELB check skipped: {e}")

# RDS mein use ho rahe SGs
try:
    rds = session.client('rds', region_name='ap-south-1')
    dbs = rds.describe_db_instances()['DBInstances']
    for db in dbs:
        for sg in db.get('VpcSecurityGroups', []):
            used_sg_ids.add(sg['VpcSecurityGroupId'])
except Exception as e:
    print(f"RDS check skipped: {e}")

# Lambda mein use ho rahe SGs
try:
    lmb = session.client('lambda', region_name='ap-south-1')
    functions = lmb.list_functions()['Functions']
    for fn in functions:
        vpc = fn.get('VpcConfig', {})
        for sg in vpc.get('SecurityGroupIds', []):
            used_sg_ids.add(sg)
except Exception as e:
    print(f"Lambda check skipped: {e}")

# ECS mein use ho rahe SGs
try:
    ecs = session.client('ecs', region_name='ap-south-1')
    clusters = ecs.list_clusters()['clusterArns']
    for cluster in clusters:
        tasks = ecs.list_tasks(cluster=cluster)['taskArns']
        if tasks:
            task_details = ecs.describe_tasks(cluster=cluster, tasks=tasks)['tasks']
            for task in task_details:
                for attachment in task.get('attachments', []):
                    for detail in attachment.get('details', []):
                        if detail['name'] == 'securityGroupIds':
                            for sg in detail['value'].split(','):
                                used_sg_ids.add(sg.strip())
except Exception as e:
    print(f"ECS check skipped: {e}")

# Unused SGs find karo
unused_sgs = []
for sg_id, sg_name in all_sg_ids.items():
    if sg_id not in used_sg_ids and sg_name != 'default':
        unused_sgs.append({'ID': sg_id, 'Name': sg_name})

# Print karo
print(f"\n{'='*60}")
print(f"Total SGs      : {len(all_sg_ids)}")
print(f"Used SGs       : {len(used_sg_ids)}")
print(f"Unused SGs     : {len(unused_sgs)}")
print(f"{'='*60}\n")

print(f"{'SG ID':<25} {'SG Name':<40}")
print('-'*65)
for sg in unused_sgs:
    print(f"{sg['ID']:<25} {sg['Name']:<40}")

# CSV save karo
import csv
with open('unused_sgs.csv', 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['ID', 'Name'])
    writer.writeheader()
    writer.writerows(unused_sgs)

print(f"\nCSV saved: unused_sgs.csv")
