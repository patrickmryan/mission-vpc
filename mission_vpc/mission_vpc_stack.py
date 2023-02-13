from aws_cdk import (
    Stack,
    Tags,
    aws_iam as iam,
    aws_ec2 as ec2,
)
from constructs import Construct


class MissionVpcStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        permissions_boundary_policy_arn = self.node.try_get_context(
            "PermissionsBoundaryPolicyArn"
        )

        if not permissions_boundary_policy_arn:
            permissions_boundary_policy_name = self.node.try_get_context(
                "PermissionsBoundaryPolicyName"
            )
            if permissions_boundary_policy_name:
                permissions_boundary_policy_arn = self.format_arn(
                    service="iam",
                    region="",
                    account=self.account,
                    resource="policy",
                    resource_name=permissions_boundary_policy_name,
                )

        if permissions_boundary_policy_arn:
            policy = iam.ManagedPolicy.from_managed_policy_arn(
                self, "PermissionsBoundary", permissions_boundary_policy_arn
            )
            iam.PermissionsBoundary.of(self).apply(policy)

        # apply tags to everything in the stack
        app_tags = self.node.try_get_context("Tags") or {}
        for key, value in app_tags.items():
            Tags.of(self).add(key, value)

        cidr_range = self.node.try_get_context("CidrRange") or "10.0.0.0/16"
        max_azs = self.node.try_get_context("MaxAZs") or 2
        subnet_configs = []
        subnet_cidr_mask = 27

        # VPC CIDR
        # maybe TG

        isolated_config = ec2.SubnetConfiguration(
            name="isolated",
            subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
            cidr_mask=subnet_cidr_mask,
        )

        ssm_accessible_config = ec2.SubnetConfiguration(
            name="ssm",
            subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
            cidr_mask=subnet_cidr_mask,
        )

        vpc = ec2.Vpc(
            self,
            "MissionVpc",
            ip_addresses=ec2.IpAddresses.cidr(cidr_range),
            enable_dns_hostnames=True,
            enable_dns_support=True,
            max_azs=max_azs,
            subnet_configuration=[isolated_config, ssm_accessible_config],
        )

        service_names = ["ssm", "ssmmessages", "ec2messages", "logs"]

        ssm_subnets = vpc.select_subnets(subnet_group_name="ssm")

        for name in service_names:
            endpoint = vpc.add_interface_endpoint(
                f"{name}-{self.stack_name}",
                service=ec2.InterfaceVpcEndpointAwsService(name),
                subnets=ec2.SubnetSelection(subnets=ssm_subnets.subnets),
            )
