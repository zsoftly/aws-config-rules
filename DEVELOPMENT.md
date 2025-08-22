# Development Guide

## Environment Setup

### Prerequisites
- Python 3.12+
- AWS CLI configured
- SAM CLI installed
- Docker (for local testing)

### Initial Setup
```bash
# Clone repository
git clone https://github.com/zsoftly/aws-config-rules.git
cd aws-config-rules

# Install development dependencies
pip install -r requirements-dev.txt
```

## Project Structure

Each rule follows this standard structure:
```
rule-name/
├── src/                    # Lambda function source
│   └── lambda_function.py  # Main handler
├── tests/                  # Unit tests
│   └── test_lambda.py      # Test cases
├── template.yaml           # SAM template
├── README.md              # Rule documentation
├── Makefile               # Build automation
├── requirements.txt       # Python dependencies
└── pytest.ini            # Test configuration
```

## Development Standards

### Code Quality
- **Linting**: flake8 (configuration in `.flake8`)
- **Security**: Bandit SAST analysis
- **Formatting**: Black (line length: 100)
- **Type Hints**: Use where applicable

### Testing Requirements
- **Framework**: pytest
- **Coverage**: Minimum 75%
- **Mocking**: Use unittest.mock for AWS services
- **Test Data**: Include realistic test scenarios

### Naming Conventions
| Component | Convention | Example |
|-----------|------------|---------|
| Directories | kebab-case | `cw-lg-retention-monitor` |
| Python Functions | snake_case | `determine_compliance()` |
| Classes | PascalCase | `ComplianceEvaluator` |
| Constants | UPPER_SNAKE | `MAX_RETRIES` |
| SAM Resources | PascalCase | `ConfigRuleFunction` |

## Build & Deploy

### Local Development
```bash
cd rule-name/

# Build
make build

# Run tests
make test

# Check coverage
make coverage

# Deploy to AWS
make deploy-local
```

### SAM Commands
```bash
# Validate template
sam validate

# Build function
sam build

# Deploy with guided setup
sam deploy --guided

# Local testing
sam local invoke ConfigRuleFunction -e events/test-event.json
```

## CI/CD Pipeline

Our GitHub Actions workflow validates:
1. **Code Quality**: flake8 linting
2. **Security**: Bandit scanning
3. **Tests**: pytest with coverage
4. **Infrastructure**: SAM template validation

### Pipeline Configuration
See `.github/workflows/ci.yml` for full pipeline details.

## AWS Config Rule Development

### Rule Types
- **Configuration Rules**: Evaluate resource configurations
- **Periodic Rules**: Run on schedule (e.g., every 24 hours)
- **Change-Triggered Rules**: Run when resources change

### Lambda Handler Pattern
```python
def lambda_handler(event, context):
    # Parse Config event
    # Evaluate compliance
    # Return evaluations
    pass
```

### Testing Config Rules
```python
def test_compliance_evaluation():
    # Mock AWS Config event
    # Call handler
    # Assert compliance results
    pass
```

## Common Patterns

### Error Handling
```python
try:
    # AWS API call
except ClientError as e:
    logger.error(f"AWS API error: {e}")
    # Handle appropriately
```

### Pagination
```python
paginator = client.get_paginator('operation_name')
for page in paginator.paginate():
    # Process items
```

## Debugging

### Local Debugging
1. Use SAM local for Lambda testing
2. Enable verbose logging
3. Use debugger with VS Code/PyCharm

### CloudWatch Logs
```bash
# View function logs
sam logs -n ConfigRuleFunction --tail
```

## Performance Optimization

- Use boto3 session reuse
- Implement proper pagination
- Cache frequently accessed data
- Optimize Lambda memory/timeout

## Resources

- [AWS Config Rule Development Kit (RDK)](https://github.com/awslabs/aws-config-rdk)
- [Boto3 Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/)
- [AWS SAM Developer Guide](https://docs.aws.amazon.com/serverless-application-model/)
- [AWS Config Best Practices](https://docs.aws.amazon.com/config/latest/developerguide/)