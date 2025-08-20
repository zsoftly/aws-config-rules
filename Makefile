.PHONY: help build package publish deploy clean test lint

# Default values
AWS_REGION ?= ca-central-1
SEMANTIC_VERSION ?= 1.0.0
APP_NAME = cw-loggroup-retention-monitor

# SAM managed bucket will be created automatically
S3_BUCKET_PREFIX = aws-sam-cli-managed-default-samclisourcebucket

help:	## Show this help message
	@echo "AWS Config Rules - CloudWatch Log Retention Monitor"
	@echo "====================================================="
	@echo ""
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Environment variables:"
	@echo "  AWS_PROFILE      AWS profile to use (from environment)"
	@echo "  AWS_REGION       AWS region (default: $(AWS_REGION))"
	@echo "  SEMANTIC_VERSION Version for SAR publishing (default: $(SEMANTIC_VERSION))"

prepare-sar:	## Prepare template for SAR publishing (uses SAR_README.md)
	@echo "Preparing template for SAR publishing..."
	@cp template.yaml template-sar.yaml
	@sed -i.bak 's/ReadmeUrl: README.md/ReadmeUrl: SAR_README.md/' template-sar.yaml
	@rm -f template-sar.yaml.bak
	@echo "SAR template prepared with SAR_README.md"

validate:	## Validate SAM template
	@echo " Validating SAM template..."
	@AWS_DEFAULT_REGION=$(AWS_REGION) sam validate
	@AWS_DEFAULT_REGION=$(AWS_REGION) sam validate --lint
	@echo " Template validation passed"

build:	## Build SAM application
	@echo " Building SAM application..."
	@AWS_DEFAULT_REGION=$(AWS_REGION) sam build
	@echo " Build completed"

package: prepare-sar build	## Package application for SAR (uses SAR_README.md)
	@echo " Packaging application for SAR..."
	@AWS_DEFAULT_REGION=$(AWS_REGION) \
		sam package \
		--template template-sar.yaml \
		--resolve-s3 \
		--output-template-file packaged-template.yaml
	@echo " Package completed with SAR_README.md"

publish: package	## Publish to AWS Serverless Application Repository
	@echo " Publishing to AWS SAR (global distribution)..."
	@echo "   Account: $$(aws sts get-caller-identity --query Account --output text)"
	@echo "   Region: $(AWS_REGION) (distributes globally)"
	@echo "   Version: $(SEMANTIC_VERSION)"
	@AWS_DEFAULT_REGION=$(AWS_REGION) \
		sam publish --template packaged-template.yaml
	@echo ""
	@echo " Successfully published to SAR!"
	@echo " Application is now available globally in all AWS regions"
	@echo ""
	@echo "SAR Console: https://$(AWS_REGION).console.aws.amazon.com/lambda/home?region=$(AWS_REGION)#/create/app"

deploy-local: build	## Deploy locally for testing (uses original README.md)
	@echo " Deploying locally for testing..."
	@AWS_DEFAULT_REGION=$(AWS_REGION) \
		sam deploy \
		--stack-name $(APP_NAME)-local-test \
		--capabilities CAPABILITY_IAM \
		--parameter-overrides \
			MinimumRetentionDays=1 \
			ConfigRuleName=cw-log-retention-min-test \
			LambdaLogRetentionDays=7 \
		--resolve-s3
	@echo " Local deployment completed"

test-rule:	## Test the deployed Config rule
	@echo " Testing Config rule..."
	@AWS_DEFAULT_REGION=$(AWS_REGION) \
		aws configservice start-config-rules-evaluation \
		--config-rule-names cw-log-retention-min-test
	@echo " Waiting for evaluation to complete..."
	@sleep 15
	@echo " Compliance results:"
	@AWS_DEFAULT_REGION=$(AWS_REGION) \
		aws configservice get-compliance-details-by-config-rule \
		--config-rule-name cw-log-retention-min-test \
		--query 'EvaluationResults[*].[EvaluationResultIdentifier.EvaluationResultQualifier.ResourceId,ComplianceType]' \
		--output table

verify-sar:	## Verify SAR publication
	@echo " Verifying SAR publication..."
	@AWS_DEFAULT_REGION=$(AWS_REGION) \
		aws serverlessrepo get-application \
		--application-id arn:aws:serverlessrepo:$(AWS_REGION):$$(aws sts get-caller-identity --query Account --output text):applications/$(APP_NAME) \
		--query '{Name:Name,Version:Version.SemanticVersion,Description:Description}' \
		--output table
	@echo " SAR publication verified"

clean:	## Clean up generated files
	@echo " Cleaning up..."
	@rm -rf .aws-sam/
	@rm -f packaged-template.yaml
	@rm -f template-sar.yaml
	@echo " Cleanup completed"

lint:	## Run linting on source code
	@echo " Linting Python code..."
	@python -m flake8 src/ --max-line-length=120 --ignore=E501,W503 || echo "Install flake8 for linting: pip install flake8"
	@echo " Linting completed"

update-version:	## Update version in template (usage: make update-version SEMANTIC_VERSION=1.1.0)
	@echo "Updating version to $(SEMANTIC_VERSION)..."
	@sed -i.bak 's/SemanticVersion: .*/SemanticVersion: $(SEMANTIC_VERSION)/' template.yaml
	@rm -f template.yaml.bak
	@echo " Version updated to $(SEMANTIC_VERSION)"

# Complete workflow targets
dev-deploy: validate build deploy-local test-rule	## Complete development workflow: validate, build, deploy locally, test

sar-deploy: validate update-version publish verify-sar	## Complete SAR workflow: validate, update version, publish, verify

# Quick commands
quick-publish: package publish	## Quick publish (skip validation)

status:	## Show current status and configuration
	@echo " Current Configuration:"
	@echo "   AWS Profile: $$AWS_PROFILE"
	@echo "   AWS Region: $(AWS_REGION)"
	@echo "   App Name: $(APP_NAME)"
	@echo "   Version: $(SEMANTIC_VERSION)"
	@echo ""
	@echo " Environment Check:"
	@echo -n "   AWS CLI: "; aws --version 2>/dev/null || echo " Not installed"
	@echo -n "   SAM CLI: "; sam --version 2>/dev/null || echo " Not installed"
	@echo -n "   Account: "; aws sts get-caller-identity --query Account --output text 2>/dev/null || echo " Not configured"
	@echo ""
	@echo "Files:"
	@ls -la *.yaml *.md 2>/dev/null || echo "   No template files found"