

# CloudWatch Log Retention Enforcer (AWS SAR)

**Enterprise-grade automation for CloudWatch log group retention compliance**

**License:** MIT | **Language:** Python 3.12+ | **Platform:** AWS SAM

---

## Why This Exists

This application is built to support [LogGuardian](https://github.com/zsoftly/logguardian), as the AWS native config rule (`CW_LOGGROUP_RETENTION_PERIOD_CHECK`) is limiting and does not meet enterprise compliance needs.

- **Native AWS rule limitation:** Marks infinite retention as compliant, leading to unexpected costs and compliance gaps.
- **This app:** Strictly enforces retention, flags infinite retention, and supports cost control for enterprise environments.
- **Marketplace:** LogGuardian is available in the AWS Serverless Application Repository: [LogGuardian SAR](https://serverlessrepo.aws.amazon.com/applications/ca-central-1/410129828371/LogGuardian)

---

## What It Does

- **Retention Enforcement:** Flags log groups as NON_COMPLIANT if retention is infinite (null) or not the required value
- **Config Compliance:** COMPLIANT only if retention matches the configured value
- **Automation:** Periodic, real-time, and manual evaluation

---

## Quick Deploy

**AWS Console:**
1. Click "Deploy" in SAR
2. Configure parameters (default retention: 7 days)
3. Deploy to your AWS account

**AWS CLI:**
```bash
aws serverlessrepo create-cloud-formation-template \
  --application-id arn:aws:serverlessrepo:ca-central-1:YOUR-ACCOUNT:applications/cloudwatch-log-retention-enforcer \
  --semantic-version 1.0.0 \
  --region ca-central-1

aws cloudformation deploy \
  --template-file template.yaml \
  --stack-name log-retention-enforcer \
  --capabilities CAPABILITY_IAM
```

---

## Key Features

- **Strict Retention Policy:** Flags infinite retention and wrong retention periods
- **Automated Scheduling:** Periodic and event-driven compliance checks
- **Enterprise Ready:** Works with existing AWS Config setup
- **Multi-Region:** Deploy in any AWS region

**Configuration:**
| Name                  | Default | Description                       |
|----------------------|---------|-----------------------------------|
| RequiredRetentionDays | 7       | Retention period (1-3653 days)    |
| ConfigRuleName        | cloudwatch-log-retention-enforcer | Name for the Config rule |

---

## Documentation & Support

**📚 Documentation:**
- [Main Project README](https://github.com/zsoftly/aws-config-rules)
- [AWS Config Rules Developer Guide](https://docs.aws.amazon.com/config/latest/developerguide/evaluate-config.html)

**🆘 Support:**
- [Report Issues](https://github.com/zsoftly/aws-config-rules/issues)
- [Discussions](https://github.com/zsoftly/aws-config-rules/discussions)

---

## License

MIT License - see the [LICENSE](https://github.com/zsoftly/aws-config-rules/blob/main/LICENSE) file for details.

---

**Built by [ZSoftly Technologies Inc](https://zsoftly.com) | Made in Canada | [Professional Services](https://cloud.zsoftly.com/)**
