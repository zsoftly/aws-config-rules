# Upgrade Guide for CloudWatch LogGroup Retention Monitor

This guide explains how to upgrade your existing SAR-deployed CloudWatch LogGroup Retention Monitor to the latest version.

## Table of Contents
- [Finding Your Current Version](#finding-your-current-version)
- [Available Versions](#available-versions)
- [Manual Upgrade Process](#manual-upgrade-process)
- [Automated Upgrade Script](#automated-upgrade-script)
- [Troubleshooting](#troubleshooting)

## Finding Your Current Version

**Note:** SAR version tags are unreliable and may show incorrect versions after updates. The upgrade script will use CloudFormation change sets to determine if actual updates are needed.

### Via AWS Console
1. Go to **CloudFormation** → Find your stack (usually `serverlessrepo-CloudWatch-LogGroup-Retention-Monitor`)
2. Click **Stack info** tab → Look for tag `serverlessrepo:semanticVersion` (may be inaccurate)
3. For actual update status, check Lambda function's **Last modified** timestamp

### Via AWS CLI
```bash
# Check version tag (may be inaccurate)
aws cloudformation describe-stacks \
  --stack-name serverlessrepo-CloudWatch-LogGroup-Retention-Monitor \
  --query "Stacks[0].Tags[?Key=='serverlessrepo:semanticVersion'].Value" \
  --output text

# Check Lambda last modified time (more reliable)
LAMBDA_NAME=$(aws cloudformation describe-stack-resources \
  --stack-name serverlessrepo-CloudWatch-LogGroup-Retention-Monitor \
  --query "StackResources[?ResourceType=='AWS::Lambda::Function'].PhysicalResourceId" \
  --output text | head -1)

aws lambda get-function --function-name "$LAMBDA_NAME" \
  --query "Configuration.LastModified" --output text
```

## Available Versions

| Version | Release Date | Changes |
|---------|-------------|---------|
| 1.1.1 | 2025-08-22 | Fixed Config rule deployment dependency issue |
| 1.1.0 | 2025-08-22 | Fixed stale evaluation handling for deleted resources |
| 1.0.2 | 2025-08-20 | Minor bug fixes |
| 1.0.1 | 2025-08-20 | Documentation updates |
| 1.0.0 | 2025-08-20 | Initial release |

## Manual Upgrade Process

### Prerequisites
- AWS CLI installed and configured
- Appropriate IAM permissions for CloudFormation and SAR
- Note your existing stack name and parameters

### Step 1: Get Current Parameters
```bash
aws cloudformation describe-stacks \
  --stack-name serverlessrepo-CloudWatch-LogGroup-Retention-Monitor \
  --query "Stacks[0].Parameters"
```

### Step 2: Generate Template URL
```bash
aws serverlessrepo create-cloud-formation-template \
  --application-id arn:aws:serverlessrepo:ca-central-1:410129828371:applications/CloudWatch-LogGroup-Retention-Monitor \
  --semantic-version 1.1.1
```

Copy the `TemplateUrl` from the output.

### Step 3: Update via CloudFormation Console
1. Go to **CloudFormation Console**
2. Select your stack (`serverlessrepo-CloudWatch-LogGroup-Retention-Monitor`)
3. Click **Update**
4. Select **Replace current template**
5. Choose **Amazon S3 URL**
6. Paste the `TemplateUrl` from Step 2
7. Click **Next**
8. Keep all existing parameter values
9. Click **Next** → **Next** → **Update stack**

### Step 4: Monitor Update
```bash
aws cloudformation wait stack-update-complete \
  --stack-name serverlessrepo-CloudWatch-LogGroup-Retention-Monitor
```

## Automated Upgrade Script

### Using the Upgrade Script

1. Download the upgrade script:
```bash
curl -O https://raw.githubusercontent.com/zsoftly/aws-config-rules/main/cw-lg-retention-monitor/scripts/upgrade-sar-stack.sh
chmod +x upgrade-sar-stack.sh
```

2. Run the upgrade:
```bash
# Upgrade to latest version
./upgrade-sar-stack.sh

# Upgrade to specific version
./upgrade-sar-stack.sh --version 1.1.1

# Specify stack name if different
./upgrade-sar-stack.sh --stack-name my-custom-stack-name
```

### Script Options
- `--version VERSION` - Specify version to upgrade to (default: latest)
- `--stack-name NAME` - Stack name (default: serverlessrepo-CloudWatch-LogGroup-Retention-Monitor)
- `--region REGION` - AWS region (default: current region)
- `--profile PROFILE` - AWS profile to use
- `--help` - Show help message

## Alternative: Delete and Redeploy

If the update process fails, you can delete and redeploy:

### Step 1: Delete Existing Stack
```bash
aws cloudformation delete-stack \
  --stack-name serverlessrepo-CloudWatch-LogGroup-Retention-Monitor

aws cloudformation wait stack-delete-complete \
  --stack-name serverlessrepo-CloudWatch-LogGroup-Retention-Monitor
```

### Step 2: Deploy New Version
```bash
aws serverlessrepo create-cloud-formation-change-set \
  --application-id arn:aws:serverlessrepo:ca-central-1:410129828371:applications/CloudWatch-LogGroup-Retention-Monitor \
  --stack-name serverlessrepo-CloudWatch-LogGroup-Retention-Monitor \
  --semantic-version 1.1.1 \
  --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND CAPABILITY_RESOURCE_POLICY \
  --parameter-overrides \
    Name=MinimumRetentionDays,Value=1 \
    Name=ConfigRuleName,Value=cw-lg-retention-min \
    Name=LambdaLogRetentionDays,Value=7
```

### Step 3: Execute Change Set
```bash
# Get change set ARN from previous command output
aws cloudformation execute-change-set --change-set-name <CHANGE_SET_ARN>
```

## Troubleshooting

### Common Issues

#### Template URL Expired
**Error**: `The specified S3 URL has expired`  
**Solution**: Template URLs expire after 6 hours. Generate a new URL and retry immediately.

#### Stack in UPDATE_ROLLBACK_FAILED
**Solution**: 
```bash
aws cloudformation continue-update-rollback \
  --stack-name serverlessrepo-CloudWatch-LogGroup-Retention-Monitor
```

#### Insufficient Permissions
**Error**: `User is not authorized to perform: serverlessrepo:CreateCloudFormationTemplate`  
**Solution**: Ensure your IAM role has the following permissions:
- `serverlessrepo:CreateCloudFormationTemplate`
- `cloudformation:UpdateStack`
- `cloudformation:CreateChangeSet`
- `cloudformation:ExecuteChangeSet`

### Verify Upgrade Success

1. Check stack status:
```bash
aws cloudformation describe-stacks \
  --stack-name serverlessrepo-CloudWatch-LogGroup-Retention-Monitor \
  --query "Stacks[0].StackStatus"
```

2. Verify Config rule is working:
```bash
aws configservice start-config-rules-evaluation \
  --config-rule-names cw-lg-retention-min
```

3. Check Lambda function update:
```bash
aws lambda get-function \
  --function-name cw-lg-retention-min-function \
  --query "Configuration.LastModified"
```

## Support

For issues or questions:
- GitHub Issues: https://github.com/zsoftly/aws-config-rules/issues
- Documentation: https://github.com/zsoftly/aws-config-rules

## Important Notes

- **Backup**: While Config rules don't store data, note your current parameters before upgrading
- **Testing**: Test upgrades in a development environment first
- **Timing**: Template URLs expire in 6 hours - complete the upgrade promptly
- **Rollback**: CloudFormation automatically rolls back failed updates