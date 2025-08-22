#!/bin/bash

# CloudWatch LogGroup Retention Monitor - SAR Stack Upgrade Script
# Simplified version that doesn't rely on unreliable SAR version tags

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
APPLICATION_ID="arn:aws:serverlessrepo:ca-central-1:410129828371:applications/CloudWatch-LogGroup-Retention-Monitor"
DEFAULT_STACK_NAME="serverlessrepo-CloudWatch-LogGroup-Retention-Monitor"
STACK_NAME=""
VERSION="latest"
REGION=""
PROFILE=""

# Function to print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Upgrade SAR-deployed CloudWatch LogGroup Retention Monitor to a new version.

OPTIONS:
    --stack-name NAME     Stack name (default: $DEFAULT_STACK_NAME)
    --version VERSION     Version to upgrade to (default: latest)
    --region REGION       AWS region (default: current region)
    --profile PROFILE     AWS profile to use
    --help               Show this help message

EXAMPLES:
    # Upgrade to latest version
    $0

    # Upgrade to specific version
    $0 --version 1.1.2

    # Use custom stack name
    $0 --stack-name my-custom-stack --version 1.1.2

EOF
    exit 0
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --stack-name)
            STACK_NAME="$2"
            shift 2
            ;;
        --version)
            VERSION="$2"
            shift 2
            ;;
        --region)
            REGION="$2"
            shift 2
            ;;
        --profile)
            PROFILE="$2"
            shift 2
            ;;
        --help)
            show_usage
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            ;;
    esac
done

# Set AWS CLI options
AWS_OPTS=""
if [ -n "$PROFILE" ]; then
    AWS_OPTS="$AWS_OPTS --profile $PROFILE"
fi
if [ -n "$REGION" ]; then
    AWS_OPTS="$AWS_OPTS --region $REGION"
else
    REGION=$(aws configure get region $AWS_OPTS || echo "us-east-1")
    AWS_OPTS="$AWS_OPTS --region $REGION"
fi

# Use default stack name if not provided
if [ -z "$STACK_NAME" ]; then
    STACK_NAME="$DEFAULT_STACK_NAME"
fi

echo "========================================="
echo "SAR Stack Upgrade Tool"
echo "========================================="
echo ""
print_info "Stack Name: $STACK_NAME"
print_info "Region: $REGION"

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    print_error "AWS CLI is not installed"
    echo "Please install AWS CLI: https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html"
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity $AWS_OPTS &> /dev/null; then
    print_error "AWS credentials not configured or invalid"
    echo "Please configure AWS credentials: aws configure"
    exit 1
fi

# Check if stack exists
print_info "Checking if stack exists..."
if ! aws cloudformation describe-stacks --stack-name "$STACK_NAME" $AWS_OPTS &> /dev/null; then
    print_error "Stack '$STACK_NAME' not found"
    echo "Please check the stack name and try again"
    exit 1
fi

# Get target version first
if [ "$VERSION" == "latest" ]; then
    print_info "Getting latest available version..."
    VERSION=$(aws serverlessrepo list-application-versions \
        --application-id "$APPLICATION_ID" \
        --query "Versions | sort_by(@, &CreationTime) | [-1].SemanticVersion" \
        --output text $AWS_OPTS)
    print_info "Latest version available: $VERSION"
else
    print_info "Target version: $VERSION"
fi

# Get Lambda info for comparison
LAMBDA_NAME=$(aws cloudformation describe-stack-resources \
    --stack-name "$STACK_NAME" \
    --query "StackResources[?ResourceType=='AWS::Lambda::Function'].PhysicalResourceId" \
    --output text $AWS_OPTS | head -1)

if [ -n "$LAMBDA_NAME" ]; then
    LAMBDA_UPDATE=$(aws lambda get-function \
        --function-name "$LAMBDA_NAME" \
        --query "Configuration.LastModified" \
        --output text $AWS_OPTS 2>/dev/null)
    
    print_info "Current Lambda last modified: $LAMBDA_UPDATE"
fi

# Get current parameters for the upgrade
CURRENT_PARAMS=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --query "Stacks[0].Parameters" \
    --output json $AWS_OPTS)

# Generate template URL for target version
print_info "Checking for differences between current and target version $VERSION..."
print_info "Generating template URL for version $VERSION..."
TEMPLATE_RESPONSE=$(aws serverlessrepo create-cloud-formation-template \
    --application-id "$APPLICATION_ID" \
    --semantic-version "$VERSION" \
    --output json $AWS_OPTS)

TEMPLATE_URL=$(echo "$TEMPLATE_RESPONSE" | grep -o '"TemplateUrl": "[^"]*"' | cut -d'"' -f4)

if [ -z "$TEMPLATE_URL" ]; then
    print_error "Failed to generate template URL"
    exit 1
fi

print_success "Template URL generated"

# Create change set to check if update is needed
CHANGE_SET_NAME="Upgrade$(echo "$VERSION" | tr '.' '-')-$(date +%s)"
print_info "Creating change set to check for updates..."

CHANGE_SET_PARAMS=""
for param in $(echo "$CURRENT_PARAMS" | jq -r '.[] | .ParameterKey'); do
    CHANGE_SET_PARAMS="$CHANGE_SET_PARAMS ParameterKey=$param,UsePreviousValue=true"
done

# Create change set
CHANGE_SET_OUTPUT=$(aws cloudformation create-change-set \
    --stack-name "$STACK_NAME" \
    --change-set-name "$CHANGE_SET_NAME" \
    --template-url "$TEMPLATE_URL" \
    --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND \
    --parameters $CHANGE_SET_PARAMS \
    --output json $AWS_OPTS 2>&1)

if [ $? -ne 0 ]; then
    print_error "Failed to create change set"
    echo "$CHANGE_SET_OUTPUT"
    exit 1
fi

CHANGE_SET_ARN=$(echo "$CHANGE_SET_OUTPUT" | grep -o '"Id": "[^"]*"' | cut -d'"' -f4)

# Wait for change set
print_info "Checking for required updates..."
sleep 3

# Check change set status
CHANGE_SET_STATUS=$(aws cloudformation describe-change-set \
    --stack-name "$STACK_NAME" \
    --change-set-name "$CHANGE_SET_NAME" \
    --query "Status" \
    --output text $AWS_OPTS 2>/dev/null)

if [ "$CHANGE_SET_STATUS" == "FAILED" ]; then
    STATUS_REASON=$(aws cloudformation describe-change-set \
        --stack-name "$STACK_NAME" \
        --change-set-name "$CHANGE_SET_NAME" \
        --query "StatusReason" \
        --output text $AWS_OPTS)
    
    if echo "$STATUS_REASON" | grep -qi "no updates\|didn't contain changes"; then
        print_success "No changes needed - stack is already up to date with version $VERSION"
        
        if [ -n "$LAMBDA_UPDATE" ]; then
            print_info "Lambda last modified: $LAMBDA_UPDATE"
        fi
        
        # Clean up
        aws cloudformation delete-change-set \
            --stack-name "$STACK_NAME" \
            --change-set-name "$CHANGE_SET_NAME" $AWS_OPTS 2>/dev/null
        
        exit 0
    else
        print_error "Change set failed: $STATUS_REASON"
        aws cloudformation delete-change-set \
            --stack-name "$STACK_NAME" \
            --change-set-name "$CHANGE_SET_NAME" $AWS_OPTS 2>/dev/null
        exit 1
    fi
fi

# Wait for change set to be ready
aws cloudformation wait change-set-create-complete \
    --stack-name "$STACK_NAME" \
    --change-set-name "$CHANGE_SET_NAME" $AWS_OPTS 2>/dev/null

# Display changes
print_info "Changes to be applied:"
aws cloudformation describe-change-set \
    --stack-name "$STACK_NAME" \
    --change-set-name "$CHANGE_SET_NAME" \
    --query "Changes[*].{Action:ResourceChange.Action,Resource:ResourceChange.LogicalResourceId,Type:ResourceChange.ResourceType}" \
    --output table $AWS_OPTS

# Confirm execution
echo ""
read -p "Do you want to apply these changes? (y/N): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_warning "Upgrade cancelled"
    aws cloudformation delete-change-set \
        --stack-name "$STACK_NAME" \
        --change-set-name "$CHANGE_SET_NAME" $AWS_OPTS 2>/dev/null
    exit 0
fi

# Execute change set
print_info "Applying changes..."
aws cloudformation execute-change-set \
    --stack-name "$STACK_NAME" \
    --change-set-name "$CHANGE_SET_NAME" $AWS_OPTS

# Wait for update
print_info "Waiting for stack update to complete (this may take several minutes)..."
if aws cloudformation wait stack-update-complete \
    --stack-name "$STACK_NAME" $AWS_OPTS; then
    print_success "Stack successfully upgraded to version $VERSION"
    
    # Show Lambda update time
    LAMBDA_NAME=$(aws cloudformation describe-stack-resources \
        --stack-name "$STACK_NAME" \
        --query "StackResources[?ResourceType=='AWS::Lambda::Function'].PhysicalResourceId" \
        --output text $AWS_OPTS | head -1)
    
    if [ -n "$LAMBDA_NAME" ]; then
        LAMBDA_UPDATE=$(aws lambda get-function \
            --function-name "$LAMBDA_NAME" \
            --query "Configuration.LastModified" \
            --output text $AWS_OPTS 2>/dev/null)
        print_info "Lambda updated: $LAMBDA_UPDATE"
    fi
    
    # Trigger evaluation
    CONFIG_RULE=$(aws cloudformation describe-stack-resources \
        --stack-name "$STACK_NAME" \
        --query "StackResources[?ResourceType=='AWS::Config::ConfigRule'].PhysicalResourceId" \
        --output text $AWS_OPTS | head -1)
    
    if [ -n "$CONFIG_RULE" ]; then
        aws configservice start-config-rules-evaluation \
            --config-rule-names "$CONFIG_RULE" $AWS_OPTS 2>/dev/null && \
        print_success "Config rule evaluation triggered"
    fi
else
    print_error "Stack update failed or was rolled back"
    echo "Check CloudFormation console for details"
    exit 1
fi

echo ""
print_success "Upgrade complete!"