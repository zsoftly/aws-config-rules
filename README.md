# AWS Config Rules Collection

🎯 **Professional AWS Config Rules** for enterprise compliance monitoring and cost optimization.

[![CI & Security](https://github.com/zsoftly/aws-config-rules/actions/workflows/ci.yml/badge.svg)](https://github.com/zsoftly/aws-config-rules/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

## 📋 Available Rules

### 🔍 CloudWatch LogGroup Retention Monitor
**[`cw-lg-retention-monitor`](./cw-lg-retention-monitor/)**

- **Purpose:** Monitors CloudWatch log groups for minimum retention compliance
- **Problem Solved:** AWS's default rule incorrectly marks infinite retention as compliant
- **Status:** ✅ Production Ready (v1.0.0)
- **Integration:** Works with [LogGuardian](https://serverlessrepo.aws.amazon.com/applications/ca-central-1/410129828371/LogGuardian) for complete log management

## 🏗️ Repository Structure

```
aws-config-rules/
├── cw-lg-retention-monitor/     # CloudWatch log retention monitor
│   ├── src/                          # Lambda function source
│   ├── tests/                        # Unit tests (77% coverage)
│   ├── template.yaml                 # SAM template
│   ├── README.md                     # Rule-specific documentation
│   ├── Makefile                      # Build automation
│   └── pytest.ini                   # Test configuration
├── .github/                          # Shared CI/CD workflows
├── README.md                         # This file
└── LICENSE                           # MIT License
```

## 🚀 Quick Start

### Deploy via AWS Serverless Application Repository
**One-click deploy:**
[**Deploy CloudWatch LogGroup Retention Monitor**](https://serverlessrepo.aws.amazon.com/applications/ca-central-1/410129828371/CloudWatch-LogGroup-Retention-Monitor)

### Local Development
```bash
# Clone repository
git clone https://github.com/zsoftly/aws-config-rules.git
cd aws-config-rules

# Work on specific rule
cd cw-lg-retention-monitor

# Build and test
make build
make test

# Deploy to your account
make deploy-local
```

## 🧪 Testing & Quality

**Comprehensive Testing:**
- **Unit Tests**: 16+ test cases per rule
- **Code Coverage**: 75%+ requirement
- **Security Scanning**: Bandit SAST analysis
- **Code Quality**: flake8 linting
- **Infrastructure**: SAM template validation

**CI/CD Pipeline:**
- ✅ **Lint & Security** - Code quality and vulnerability scanning
- ✅ **SAM Validation** - CloudFormation template validation
- ✅ **Unit Tests** - Comprehensive test coverage

## 📊 Rule Catalog

| Rule Name | Purpose | Status | Coverage | SAR Link |
|-----------|---------|--------|----------|----------|
| [`cw-lg-retention-monitor`](./cw-lg-retention-monitor/) | CloudWatch LogGroup retention compliance | ✅ v1.0.0 | 77% | [Deploy](https://serverlessrepo.aws.amazon.com/applications/ca-central-1/410129828371/CloudWatch-LogGroup-Retention-Monitor) |
| *More rules coming soon...* | | | | |

## 🛠️ Development Guidelines

### Adding New Rules
1. **Create Directory**: `mkdir new-rule-name/`
2. **Use Template Structure**: Follow existing rule patterns
3. **Implement Tests**: Minimum 75% code coverage required
4. **Update CI**: Ensure pipeline includes your rule
5. **Document**: Add README and update this file

### Code Standards
- **Python 3.12+** for Lambda functions
- **SAM Framework** for infrastructure
- **pytest** for testing with coverage reports
- **flake8** for code linting
- **Bandit** for security analysis

### Naming Conventions
- **Directories**: `kebab-case` (e.g., `cw-lg-retention-monitor`)
- **Functions**: `snake_case` (e.g., `determine_compliance`)
- **Files**: Follow AWS and Python conventions

## 🤝 Contributing

1. **Fork** the repository
2. **Create** feature branch: `git checkout -b feature/new-rule`
3. **Develop** following our standards
4. **Test** thoroughly (CI must pass)
5. **Document** your changes
6. **Submit** pull request

## 📚 Resources

- [AWS Config Developer Guide](https://docs.aws.amazon.com/config/latest/developerguide/)
- [AWS SAM Documentation](https://docs.aws.amazon.com/serverless-application-model/)
- [AWS Serverless Application Repository](https://aws.amazon.com/serverless/serverlessrepo/)

## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/zsoftly/aws-config-rules/issues)
- **Discussions**: [GitHub Discussions](https://github.com/zsoftly/aws-config-rules/discussions)
- **Professional Services**: [cloud.zsoftly.com](https://cloud.zsoftly.com/)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**⭐ If these rules help you achieve compliance and save costs, please star the repository!**

Built by [ZSoftly Technologies Inc](https://zsoftly.com) | Made in Canada 🇨🇦