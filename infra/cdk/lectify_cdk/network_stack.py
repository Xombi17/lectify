from aws_cdk import Stack
from aws_cdk import aws_ec2 as ec2
from constructs import Construct


class NetworkStack(Stack):
    """VPC (2 AZ, public + isolated, no NAT), S3 gateway endpoint, 4 SGs exposed as attributes."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.vpc = ec2.Vpc(
            self,
            "Vpc",
            ip_addresses=ec2.IpAddresses.cidr("10.0.0.0/16"),
            max_azs=2,
            nat_gateways=0,
            subnet_configuration=[
                ec2.SubnetConfiguration(name="public", subnet_type=ec2.SubnetType.PUBLIC, cidr_mask=24),
                ec2.SubnetConfiguration(name="isolated", subnet_type=ec2.SubnetType.PRIVATE_ISOLATED, cidr_mask=24),
            ],
            gateway_endpoints={"S3": ec2.GatewayVpcEndpointOptions(service=ec2.GatewayVpcEndpointAwsService.S3)},
        )

        self.sg_alb = ec2.SecurityGroup(self, "Alb", vpc=self.vpc, description="lectify ALB: HTTP from internet", allow_all_outbound=True)
        self.sg_alb.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(80))

        self.sg_api = ec2.SecurityGroup(self, "Api", vpc=self.vpc, description="lectify API: from ALB only", allow_all_outbound=True)
        for port in (8000, 3000):
            self.sg_api.add_ingress_rule(self.sg_alb, ec2.Port.tcp(port))

        self.sg_worker = ec2.SecurityGroup(self, "Worker", vpc=self.vpc, description="lectify worker: no ingress", allow_all_outbound=True)

        self.sg_rds = ec2.SecurityGroup(self, "Rds", vpc=self.vpc, description="lectify RDS: 5432 from api and worker", allow_all_outbound=False)
        for peer in (self.sg_api, self.sg_worker):
            self.sg_rds.add_ingress_rule(peer, ec2.Port.tcp(5432))
