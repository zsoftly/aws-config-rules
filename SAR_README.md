

# cw-loggroup-retention-monitor (AWS SAR)

**CloudWatch log group retention compliance monitoring**

**License:** MIT | **Language:** Python 3.12+ | **Platform:** AWS SAM

---

## Why This Exists

This application is built to support [LogGuardian](https://github.com/zsoftly/logguardian), as the AWS native config rule (`CW_LOGGROUP_RETENTION_PERIOD_CHECK`) is limiting and does not meet enterprise compliance needs.

- **Native AWS rule limitation:** Marks infinite retention as compliant, leading to unexpected costs and compliance gaps.
- **This app:** Strictly enforces retention, flags infinite retention, and supports cost control for enterprise environments.
- **Marketplace:** LogGuardian is available in the AWS Serverless Application Repository: [LogGuardian SAR](https://serverlessrepo.aws.amazon.com/applications/ca-central-1/410129828371/LogGuardian)

---

## What It Does

- **Retention Monitoring:** Reports log groups as NON_COMPLIANT if retention is infinite (null) or below the minimum value
- **Config Compliance:** COMPLIANT if retention meets or exceeds the configured minimum
- **Non-Intrusive:** Monitors only - does not modify log group settings
- **Automation:** Periodic, real-time, and manual evaluation

---

## Quick Deploy

**AWS Console:**
1. Click "Deploy" in SAR
2. Configure parameters (default minimum: 1 day)
3. Deploy to your AWS account

**AWS CLI:**
```bash
aws serverlessrepo create-cloud-formation-template \
  --application-id arn:aws:serverlessrepo:ca-central-1:YOUR-ACCOUNT:applications/cw-loggroup-retention-monitor \
  --semantic-version 1.0.0 \
  --region ca-central-1

aws cloudformation deploy \
  --template-file template.yaml \
  --stack-name cw-loggroup-retention-monitor \
  --capabilities CAPABILITY_IAM
```

---

## Key Features

- **Accurate Compliance Monitoring:** Reports infinite retention and periods below minimum
- **Automated Scheduling:** Periodic and event-driven compliance checks
- **Enterprise Ready:** Works with existing AWS Config setup
- **Multi-Region:** Deploy in any AWS region

**Configuration Parameters:**

**MinimumRetentionDays**
- Default: 1
- Description: Minimum retention period (1-3653 days)
- Valid values: 1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, 3653

**ConfigRuleName**
- Default: cw-log-retention-min
- Description: Name for the AWS Config rule (must contain 'retention')
- Pattern: Must contain the word 'retention' (case-insensitive)

**LambdaLogRetentionDays**
- Default: 7
- Description: Retention period for Lambda function logs (1-3653 days)
- Valid values: 1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, 3653

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
