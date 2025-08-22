# AWS Config Rules Collection

🎯 **Professional AWS Config Rules** for enterprise compliance monitoring and cost optimization.

[![CI & Security](https://github.com/zsoftly/aws-config-rules/actions/workflows/ci.yml/badge.svg)](https://github.com/zsoftly/aws-config-rules/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

## 🚀 Quick Start

### One-Click Deploy

[![Deploy from AWS Serverless Application Repository](https://img.shields.io/badge/Deploy%20from%20SAR-CloudWatch%20LogGroup%20Retention%20Monitor-orange?style=for-the-badge&logo=amazon-aws)](https://serverlessrepo.aws.amazon.com/applications/ca-central-1/410129828371/CloudWatch-LogGroup-Retention-Monitor)

### Local Setup
```bash
git clone https://github.com/zsoftly/aws-config-rules.git
cd aws-config-rules/cw-lg-retention-monitor
make deploy-local
```

## 📊 Rule Catalog

| Rule Name | Purpose | Status | Coverage | SAR Link |
|-----------|---------|--------|----------|----------|
| [`cw-lg-retention-monitor`](./cw-lg-retention-monitor/) | CloudWatch LogGroup retention compliance | ✅ v1.1.2 | 95% | [Deploy](https://serverlessrepo.aws.amazon.com/applications/ca-central-1/410129828371/CloudWatch-LogGroup-Retention-Monitor) |
| *More rules coming soon...* | | | | |

## 📚 Documentation

- [**Development Guide**](./DEVELOPMENT.md) - Setup, standards, and patterns
- [**Contributing**](./CONTRIBUTING.md) - How to contribute new rules
- [Rule Documentation](./cw-lg-retention-monitor/README.md) - Detailed rule information

## 🤝 Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.

## 📚 Resources

- [AWS Config Developer Guide](https://docs.aws.amazon.com/config/latest/developerguide/)
- [AWS SAM Documentation](https://docs.aws.amazon.com/serverless-application-model/)
- [AWS Serverless Application Repository](https://aws.amazon.com/serverless/serverlessrepo/)

## 🆘 Support

- [GitHub Issues](https://github.com/zsoftly/aws-config-rules/issues)
- [Discussions](https://github.com/zsoftly/aws-config-rules/discussions)
- [Professional Services](https://cloud.zsoftly.com/)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**⭐ If these rules help you achieve compliance and save costs, please star the repository!**

Built by [ZSoftly Technologies Inc](https://zsoftly.com) | Made in Canada 🇨🇦