#!/bin/bash

# AWS Config Prerequisites Checker
# This script verifies that AWS Config is properly set up before deploying Config rules

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================="
echo "AWS Config Prerequisites Checker"
echo "========================================="
echo ""

# Check AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}[X] AWS CLI is not installed${NC}"
    echo "Please install AWS CLI: https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html"
    exit 1
fi

# Check AWS credentials are configured
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}[X] AWS credentials not configured${NC}"
    echo "Please configure AWS credentials: aws configure"
    exit 1
fi

ACCOUNT_ID=$(aws sts get-caller-identity --query 'Account' --output text)
REGION=$(aws configure get region || echo "us-east-1")

echo "Checking AWS Config setup for:"
echo "  Account: $ACCOUNT_ID"
echo "  Region:  $REGION"
echo ""

# Initialize status variables
CONFIG_READY=true
ISSUES_FOUND=""

# Function to add issue
add_issue() {
    ISSUES_FOUND="${ISSUES_FOUND}\n  - $1"
    CONFIG_READY=false
}

# Check Configuration Recorder
echo -n "1. Checking Configuration Recorder... "
RECORDER_STATUS=$(aws configservice describe-configuration-recorder-status --output json 2>/dev/null || echo '{"ConfigurationRecordersStatus":[]}')

RECORDER_COUNT=$(echo "$RECORDER_STATUS" | python3 -c "import sys, json; data = json.load(sys.stdin); print(len(data.get('ConfigurationRecordersStatus', [])))" 2>/dev/null || echo "0")

if [ "$RECORDER_COUNT" == "0" ]; then
    echo -e "${RED}[X] Not found${NC}"
    add_issue "No Configuration Recorder found. AWS Config needs to be set up."
else
    RECORDING=$(echo "$RECORDER_STATUS" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data['ConfigurationRecordersStatus'][0].get('recording', False))" 2>/dev/null || echo "false")
    LAST_STATUS=$(echo "$RECORDER_STATUS" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data['ConfigurationRecordersStatus'][0].get('lastStatus', 'UNKNOWN'))" 2>/dev/null || echo "UNKNOWN")
    
    if [ "$RECORDING" == "True" ] && [ "$LAST_STATUS" == "SUCCESS" ]; then
        echo -e "${GREEN}[OK] Active and recording${NC}"
    elif [ "$RECORDING" == "False" ]; then
        echo -e "${YELLOW}[!] Found but not recording${NC}"
        RECORDER_NAME=$(echo "$RECORDER_STATUS" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data['ConfigurationRecordersStatus'][0].get('name', 'default'))" 2>/dev/null || echo "default")
        add_issue "Configuration Recorder exists but is stopped. Run: aws configservice start-configuration-recorder --configuration-recorder-name $RECORDER_NAME"
    else
        echo -e "${YELLOW}[!] Found but status: $LAST_STATUS${NC}"
        add_issue "Configuration Recorder status is not SUCCESS: $LAST_STATUS"
    fi
fi

# Check Delivery Channel
echo -n "2. Checking Delivery Channel... "
DELIVERY_CHANNELS=$(aws configservice describe-delivery-channels --output json 2>/dev/null || echo '{"DeliveryChannels":[]}')

CHANNEL_COUNT=$(echo "$DELIVERY_CHANNELS" | python3 -c "import sys, json; data = json.load(sys.stdin); print(len(data.get('DeliveryChannels', [])))" 2>/dev/null || echo "0")

if [ "$CHANNEL_COUNT" == "0" ]; then
    echo -e "${RED}[X] Not found${NC}"
    add_issue "No Delivery Channel found. AWS Config needs to be set up."
else
    S3_BUCKET=$(echo "$DELIVERY_CHANNELS" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data['DeliveryChannels'][0].get('s3BucketName', ''))" 2>/dev/null || echo "")
    if [ -n "$S3_BUCKET" ]; then
        echo -e "${GREEN}[OK] Found (S3: $S3_BUCKET)${NC}"
    else
        echo -e "${YELLOW}[!] Found but no S3 bucket configured${NC}"
        add_issue "Delivery Channel exists but no S3 bucket is configured"
    fi
fi

# Check Delivery Channel Status
echo -n "3. Checking Delivery Channel Status... "
DELIVERY_STATUS=$(aws configservice describe-delivery-channel-status --output json 2>/dev/null || echo '{"DeliveryChannelsStatus":[]}')

STATUS_COUNT=$(echo "$DELIVERY_STATUS" | python3 -c "import sys, json; data = json.load(sys.stdin); print(len(data.get('DeliveryChannelsStatus', [])))" 2>/dev/null || echo "0")

if [ "$STATUS_COUNT" == "0" ]; then
    echo -e "${RED}[X] Not available${NC}"
    add_issue "Cannot get Delivery Channel status"
else
    # Check configHistoryDeliveryInfo for S3 delivery (primary method)
    HISTORY_STATUS=$(echo "$DELIVERY_STATUS" | python3 -c "import sys, json; data = json.load(sys.stdin); status = data['DeliveryChannelsStatus'][0].get('configHistoryDeliveryInfo', {}); print(status.get('lastStatus', 'UNKNOWN'))" 2>/dev/null || echo "UNKNOWN")
    
    # Check configStreamDeliveryInfo for streaming (optional)
    STREAM_STATUS=$(echo "$DELIVERY_STATUS" | python3 -c "import sys, json; data = json.load(sys.stdin); status = data['DeliveryChannelsStatus'][0].get('configStreamDeliveryInfo', {}); print(status.get('lastStatus', 'UNKNOWN'))" 2>/dev/null || echo "UNKNOWN")
    
    if [ "$HISTORY_STATUS" == "SUCCESS" ]; then
        echo -e "${GREEN}[OK] Delivering to S3 successfully${NC}"
    elif [ "$STREAM_STATUS" == "SUCCESS" ]; then
        echo -e "${GREEN}[OK] Streaming successfully${NC}"
    elif [ "$HISTORY_STATUS" == "UNKNOWN" ] && [ "$STREAM_STATUS" == "NOT_APPLICABLE" ]; then
        echo -e "${YELLOW}[!] No recent deliveries (may be normal for new setup)${NC}"
    else
        echo -e "${YELLOW}[!] Delivery status: History=$HISTORY_STATUS, Stream=$STREAM_STATUS${NC}"
        if [ "$HISTORY_STATUS" != "SUCCESS" ] && [ "$HISTORY_STATUS" != "UNKNOWN" ]; then
            add_issue "S3 delivery status is not SUCCESS: $HISTORY_STATUS"
        fi
    fi
fi

# Check IAM Role
echo -n "4. Checking IAM Service Role... "
RECORDER_DETAILS=$(aws configservice describe-configuration-recorders --output json 2>/dev/null || echo '{"ConfigurationRecorders":[]}')

RECORDER_EXISTS=$(echo "$RECORDER_DETAILS" | python3 -c "import sys, json; data = json.load(sys.stdin); print(len(data.get('ConfigurationRecorders', [])))" 2>/dev/null || echo "0")

if [ "$RECORDER_EXISTS" != "0" ]; then
    ROLE_ARN=$(echo "$RECORDER_DETAILS" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data['ConfigurationRecorders'][0].get('roleARN', ''))" 2>/dev/null || echo "")
    if [ -n "$ROLE_ARN" ]; then
        echo -e "${GREEN}[OK] Configured${NC}"
        echo "     Role: $ROLE_ARN"
    else
        echo -e "${YELLOW}[!] No role found${NC}"
        add_issue "Configuration Recorder has no IAM role configured"
    fi
else
    echo -e "${RED}[X] Cannot check${NC}"
fi

# Check if recording log groups
echo -n "5. Checking if Log Groups are being recorded... "
if [ "$RECORDER_EXISTS" != "0" ]; then
    ALL_SUPPORTED=$(echo "$RECORDER_DETAILS" | python3 -c "import sys, json; data = json.load(sys.stdin); rec = data['ConfigurationRecorders'][0].get('recordingGroup', {}); print(rec.get('allSupported', False))" 2>/dev/null || echo "False")
    RESOURCE_TYPES=$(echo "$RECORDER_DETAILS" | python3 -c "import sys, json; data = json.load(sys.stdin); rec = data['ConfigurationRecorders'][0].get('recordingGroup', {}); types = rec.get('resourceTypes', []); print(','.join(types) if types else '')" 2>/dev/null || echo "")
    
    if [ "$ALL_SUPPORTED" == "True" ]; then
        echo -e "${GREEN}[OK] Recording all resources${NC}"
    elif echo "$RESOURCE_TYPES" | grep -q "AWS::Logs::LogGroup"; then
        echo -e "${GREEN}[OK] Recording Log Groups specifically${NC}"
    elif [ -z "$RESOURCE_TYPES" ]; then
        echo -e "${GREEN}[OK] Recording all resources (default)${NC}"
    else
        echo -e "${YELLOW}[!] May not be recording Log Groups${NC}"
        echo "     Recording: $RESOURCE_TYPES"
        add_issue "Configuration Recorder may not be recording AWS::Logs::LogGroup resources"
    fi
else
    echo -e "${RED}[X] Cannot check${NC}"
fi

echo ""
echo "========================================="
echo "RESULTS"
echo "========================================="

if [ "$CONFIG_READY" == "true" ]; then
    echo -e "${GREEN}AWS Config is properly configured!${NC}"
    echo ""
    echo "You can now deploy Config rules in this region."
    echo ""
    echo "Next steps:"
    echo "  1. Deploy the CloudWatch LogGroup Retention Monitor"
    echo "  2. View compliance results in AWS Config Console"
    exit 0
else
    echo -e "${RED}AWS Config is NOT properly configured${NC}"
    echo ""
    echo "Issues found:$ISSUES_FOUND"
    echo ""
    echo "To fix this, you have two options:"
    echo ""
    echo "Option 1: AWS Console (Recommended)"
    echo "  1. Go to https://console.aws.amazon.com/config/"
    echo "  2. Click 'Get started' → '1-click setup'"
    echo "  3. Accept defaults and click 'Confirm'"
    echo ""
    echo "Option 2: AWS CLI"
    echo "  See: https://docs.aws.amazon.com/config/latest/developerguide/gs-cli.html"
    echo ""
    echo "After fixing, run this script again to verify."
    exit 1
fi