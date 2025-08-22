# Contributing to AWS Config Rules

Thank you for your interest in contributing to our AWS Config Rules collection!

## How to Contribute

### 1. Create GitHub Issue
**IMPORTANT**: All work must have an associated GitHub issue first.
- Open an [issue](https://github.com/zsoftly/aws-config-rules/issues/new)
- Describe the feature, bug, or improvement
- Note the issue number for your branch

### 2. Fork & Clone
```bash
git clone https://github.com/zsoftly/aws-config-rules.git
cd aws-config-rules
```

### 3. Create Branch with Issue Number
**Branch naming convention**: `issues/[issue-number]-descriptive-name`
```bash
# Example for issue #42 about adding S3 bucket encryption rule
git checkout -b issues/42-s3-bucket-encryption-rule
```

### 4. Development Workflow

#### For New Rules:
1. Create a new directory: `mkdir your-rule-name/`
2. Follow the existing rule structure (see `cw-lg-retention-monitor/` as template)
3. Include comprehensive tests (minimum 75% coverage)
4. Add rule-specific README.md
5. Update root README.md with your rule

#### For Bug Fixes/Improvements:
1. Make your changes
2. Add/update tests as needed
3. Ensure all tests pass

### 5. Testing Requirements
```bash
# Run tests locally
make test

# Check coverage
make coverage
```

- Minimum 75% code coverage required
- All CI checks must pass
- Security scanning must pass (Bandit)

### 6. Commit Guidelines
- Use clear, descriptive commit messages
- Follow conventional commits format when possible:
  - `feat:` for new features
  - `fix:` for bug fixes
  - `docs:` for documentation
  - `test:` for test additions/changes

### 7. Submit Pull Request
1. Push your branch to your fork
2. Create a pull request against `main` branch
3. Include:
   - Clear description of changes
   - Link to any related issues
   - Test results/coverage report

## Code of Conduct

- Be respectful and inclusive
- Welcome newcomers and help when you can
- Focus on constructive feedback
- Follow AWS best practices

## Need Help?

- Open an [issue](https://github.com/zsoftly/aws-config-rules/issues)
- Start a [discussion](https://github.com/zsoftly/aws-config-rules/discussions)
- Review existing rules for examples

## Recognition

All contributors will be recognized in our repository. Thank you for helping improve AWS compliance monitoring!