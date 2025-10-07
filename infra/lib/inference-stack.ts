import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as eks from 'aws-cdk-lib/aws-eks';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as iam from 'aws-cdk-lib/aws-iam';

export class InferenceStack extends cdk.Stack {
  public readonly vpc: ec2.Vpc;
  public readonly cluster: eks.CfnCluster;

  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Create VPC for EKS cluster
    this.vpc = new ec2.Vpc(this, 'InferenceVpc', {
      maxAzs: 2,
      natGateways: 1
    });

    // Create IAM role for EKS cluster
    const clusterRole = new iam.Role(this, 'ClusterRole', {
      assumedBy: new iam.ServicePrincipal('eks.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonEKSClusterPolicy'),
        // Required policies for EKS Auto Mode
        iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonEKSBlockStoragePolicy'),
        iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonEKSComputePolicy'),
        iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonEKSLoadBalancingPolicy'),
        iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonEKSNetworkingPolicy')
      ]
    });

    // Add sts:TagSession to the cluster role's trust policy (required for EKS Auto Mode)
    clusterRole.assumeRolePolicy?.addStatements(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        principals: [new iam.ServicePrincipal('eks.amazonaws.com')],
        actions: ['sts:AssumeRole', 'sts:TagSession']
      })
    );

    // Create EKS cluster with Auto Mode
    this.cluster = new eks.CfnCluster(this, 'InferenceCluster', {
      name: `inference-cluster-${this.account}`,
      version: '1.33',
      roleArn: clusterRole.roleArn,
      resourcesVpcConfig: {
        subnetIds: [...this.vpc.privateSubnets.map(s => s.subnetId), ...this.vpc.publicSubnets.map(s => s.subnetId)]
      },
      accessConfig: {
        authenticationMode: 'API_AND_CONFIG_MAP'
      },
      computeConfig: {
        enabled: true
      },
      kubernetesNetworkConfig: {
        elasticLoadBalancing: {
          enabled: true
        }
      },
      storageConfig: {
        blockStorage: {
          enabled: true
        }
      }
    });

    // Add federated user as cluster admin
    new eks.CfnAccessEntry(this, 'FederatedUserAccessEntry', {
      clusterName: this.cluster.name!,
      principalArn: 'arn:aws:iam::113273159455:role/aws-reserved/sso.amazonaws.com/ap-southeast-1/AWSReservedSSO_awsisb_IsbUsersPS_3b51908f5baadfb6',
      type: 'STANDARD',
      accessPolicies: [{
        policyArn: 'arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy',
        accessScope: {
          type: 'cluster'
        }
      }]
    });

    // Outputs
    new cdk.CfnOutput(this, 'VpcId', {
      value: this.vpc.vpcId
    });

    new cdk.CfnOutput(this, 'ClusterName', {
      value: this.cluster.name!
    });


  }
}