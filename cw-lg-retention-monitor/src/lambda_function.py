import json
import boto3
import botocore
import os
from datetime import datetime


def lambda_handler(event, context):
    """
    AWS Config rule Lambda handler for CloudWatch Log Group Retention Monitor
    
    Monitors CloudWatch log groups for compliance with minimum retention periods.
    Reports log groups as NON_COMPLIANT if:
    - retentionInDays is null (infinite retention)
    - retentionInDays is less than the minimum required value
    
    Reports log groups as COMPLIANT if retentionInDays meets or exceeds the minimum required value.
    Does not modify or enforce retention policies - monitoring only.
    """
    
    print(f"Received event: {json.dumps(event, default=str)}")
    
    # Extract rule parameters
    rule_parameters = {}
    if 'ruleParameters' in event:
        rule_parameters = json.loads(event['ruleParameters'])
    
    # Get minimum retention days from parameters or environment
    required_retention_days = int(
        rule_parameters.get('MinimumRetentionDays', 
        os.environ.get('REQUIRED_RETENTION_DAYS', '1'))
    )
    
    print(f"Minimum retention days: {required_retention_days}")
    
    # Parse invoking event
    invoking_event = json.loads(event['invokingEvent'])
    message_type = invoking_event['messageType']
    
    # Initialize AWS clients
    config_client = boto3.client('config')
    logs_client = boto3.client('logs')
    
    evaluations = []
    
    try:
        if message_type == 'ScheduledNotification':
            # Periodic evaluation - check all log groups
            evaluations = evaluate_all_log_groups(logs_client, required_retention_days, event)
        elif message_type in ['ConfigurationItemChangeNotification', 'OversizedConfigurationItemChangeNotification']:
            # Configuration change - evaluate specific log group
            configuration_item = get_configuration_item(invoking_event, config_client)
            if configuration_item and configuration_item.get('resourceType') == 'AWS::Logs::LogGroup':
                evaluation = evaluate_single_log_group(configuration_item, required_retention_days)
                if evaluation:
                    evaluations.append(evaluation)
        else:
            print(f"Unsupported message type: {message_type}")
            
    except Exception as e:
        print(f"Error during evaluation: {str(e)}")
        # Return a NOT_APPLICABLE evaluation to prevent Config rule failure
        evaluations = [{
            'ComplianceResourceType': 'AWS::::Account',
            'ComplianceResourceId': event.get('accountId', 'unknown'),
            'ComplianceType': 'NOT_APPLICABLE',
            'Annotation': f'Error during evaluation: {str(e)}',
            'OrderingTimestamp': datetime.now()
        }]
    
    # Submit evaluations to Config
    if evaluations:
        submit_evaluations(config_client, evaluations, event)
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'Config rule evaluation completed',
            'evaluations_count': len(evaluations)
        })
    }


def evaluate_all_log_groups(logs_client, required_retention_days, event):
    """Evaluate all CloudWatch log groups in the account"""
    evaluations = []
    
    try:
        paginator = logs_client.get_paginator('describe_log_groups')
        
        for page in paginator.paginate():
            for log_group in page['logGroups']:
                log_group_name = log_group['logGroupName']
                current_retention = log_group.get('retentionInDays')
                
                evaluation = create_evaluation(
                    resource_id=log_group_name,
                    resource_type='AWS::Logs::LogGroup',
                    current_retention=current_retention,
                    required_retention_days=required_retention_days,
                    event=event
                )
                evaluations.append(evaluation)
                
    except botocore.exceptions.ClientError as e:
        print(f"Error describing log groups: {e}")
        raise e
        
    print(f"Evaluated {len(evaluations)} log groups")
    return evaluations


def evaluate_single_log_group(configuration_item, required_retention_days):
    """Evaluate a single log group from configuration change"""
    log_group_name = configuration_item['resourceId']
    log_group_config = configuration_item['configuration']
    current_retention = log_group_config.get('retentionInDays')
    
    return {
        'ComplianceResourceType': configuration_item['resourceType'],
        'ComplianceResourceId': log_group_name,
        'ComplianceType': determine_compliance(current_retention, required_retention_days),
        'Annotation': create_annotation(log_group_name, current_retention, required_retention_days),
        'OrderingTimestamp': configuration_item['configurationItemCaptureTime']
    }


def create_evaluation(resource_id, resource_type, current_retention, required_retention_days, event):
    """Create a Config evaluation for a log group"""
    return {
        'ComplianceResourceType': resource_type,
        'ComplianceResourceId': resource_id,
        'ComplianceType': determine_compliance(current_retention, required_retention_days),
        'Annotation': create_annotation(resource_id, current_retention, required_retention_days),
        'OrderingTimestamp': json.loads(event['invokingEvent'])['notificationCreationTime']
    }


def determine_compliance(current_retention, required_retention_days):
    """Determine compliance status based on minimum retention values"""
    if current_retention is None:
        return 'NON_COMPLIANT'  # Infinite retention
    elif current_retention < required_retention_days:
        return 'NON_COMPLIANT'  # Below minimum retention period
    else:
        return 'COMPLIANT'      # Meets or exceeds minimum retention period


def create_annotation(log_group_name, current_retention, required_retention_days):
    """Create annotation message for the evaluation"""
    if current_retention is None:
        return f"Log group '{log_group_name}' has infinite retention (null). Minimum required: {required_retention_days} days."
    elif current_retention < required_retention_days:
        return f"Log group '{log_group_name}' has {current_retention} days retention. Minimum required: {required_retention_days} days."
    else:
        return f"Log group '{log_group_name}' has {current_retention} days retention, meets minimum requirement of {required_retention_days} days."


def get_configuration_item(invoking_event, config_client):
    """Get configuration item from invoking event or API call"""
    if invoking_event['messageType'] == 'OversizedConfigurationItemChangeNotification':
        # Get configuration item via API for oversized notifications
        configuration_item_summary = invoking_event['configurationItemSummary']
        response = config_client.get_resource_config_history(
            resourceType=configuration_item_summary['resourceType'],
            resourceId=configuration_item_summary['resourceId'],
            laterTime=configuration_item_summary['configurationItemCaptureTime'],
            limit=1
        )
        if response['configurationItems']:
            config_item = response['configurationItems'][0]
            # Convert API format to invoking event format
            config_item['configuration'] = json.loads(config_item['configuration'])
            return config_item
    else:
        # Standard configuration item in invoking event
        return invoking_event.get('configurationItem')
    
    return None


def submit_evaluations(config_client, evaluations, event):
    """Submit evaluations to AWS Config in batches"""
    result_token = event['resultToken']
    
    # Config accepts maximum 100 evaluations per request
    batch_size = 100
    for i in range(0, len(evaluations), batch_size):
        batch = evaluations[i:i + batch_size]
        
        # Convert datetime objects to strings for JSON serialization
        for evaluation in batch:
            if isinstance(evaluation['OrderingTimestamp'], datetime):
                evaluation['OrderingTimestamp'] = evaluation['OrderingTimestamp'].isoformat()
        
        try:
            config_client.put_evaluations(
                Evaluations=batch,
                ResultToken=result_token
            )
            print(f"Submitted {len(batch)} evaluations to Config")
        except Exception as e:
            print(f"Error submitting evaluations: {str(e)}")
            raise e