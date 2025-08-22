"""
Unit tests for CloudWatch Log Group Retention Monitor Lambda function
"""
import sys
import os
import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from lambda_function import (
    determine_compliance,
    create_annotation,
    create_evaluation,
    evaluate_single_log_group,
    evaluate_all_log_groups,
    get_configuration_item,
    submit_evaluations,
    lambda_handler
)


class TestComplianceLogic:
    """Test compliance determination logic"""
    
    def test_determine_compliance_infinite_retention(self):
        """Test that infinite retention (None) is NON_COMPLIANT"""
        result = determine_compliance(None, 30)
        assert result == 'NON_COMPLIANT'
    
    def test_determine_compliance_below_minimum(self):
        """Test that retention below minimum is NON_COMPLIANT"""
        result = determine_compliance(7, 30)
        assert result == 'NON_COMPLIANT'
    
    def test_determine_compliance_meets_minimum(self):
        """Test that retention meeting minimum is COMPLIANT"""
        result = determine_compliance(30, 30)
        assert result == 'COMPLIANT'
    
    def test_determine_compliance_exceeds_minimum(self):
        """Test that retention exceeding minimum is COMPLIANT"""
        result = determine_compliance(365, 30)
        assert result == 'COMPLIANT'
    
    def test_determine_compliance_edge_cases(self):
        """Test edge cases for compliance determination"""
        # Zero retention
        assert determine_compliance(0, 1) == 'NON_COMPLIANT'
        
        # Minimum possible values
        assert determine_compliance(1, 1) == 'COMPLIANT'
        
        # Large values
        assert determine_compliance(3653, 1) == 'COMPLIANT'


class TestAnnotations:
    """Test annotation message generation"""
    
    def test_create_annotation_infinite(self):
        """Test annotation for infinite retention"""
        annotation = create_annotation('/test/log', None, 30)
        assert 'infinite retention (null)' in annotation
        assert 'Minimum required: 30 days' in annotation
        assert '/test/log' in annotation
    
    def test_create_annotation_below_minimum(self):
        """Test annotation for below minimum retention"""
        annotation = create_annotation('/aws/lambda/test', 7, 30)
        assert '7 days retention' in annotation
        assert 'Minimum required: 30 days' in annotation
        assert '/aws/lambda/test' in annotation
    
    def test_create_annotation_compliant(self):
        """Test annotation for compliant retention"""
        annotation = create_annotation('/custom/app', 365, 30)
        assert '365 days retention' in annotation
        assert 'meets minimum requirement of 30 days' in annotation
        assert '/custom/app' in annotation
    
    def test_create_annotation_edge_cases(self):
        """Test annotation edge cases"""
        # Empty log group name
        annotation = create_annotation('', 30, 7)
        assert "has 30 days retention" in annotation
        
        # Special characters in log group name
        annotation = create_annotation('/aws/lambda/my-test_function.v1', None, 1)
        assert '/aws/lambda/my-test_function.v1' in annotation


class TestEvaluationCreation:
    """Test evaluation object creation"""
    
    def test_create_evaluation_compliant(self):
        """Test creating a compliant evaluation"""
        event = {
            'invokingEvent': json.dumps({
                'notificationCreationTime': '2024-01-01T00:00:00Z'
            })
        }
        
        evaluation = create_evaluation(
            resource_id='/test/log',
            resource_type='AWS::Logs::LogGroup',
            current_retention=30,
            required_retention_days=7,
            event=event
        )
        
        assert evaluation['ComplianceResourceType'] == 'AWS::Logs::LogGroup'
        assert evaluation['ComplianceResourceId'] == '/test/log'
        assert evaluation['ComplianceType'] == 'COMPLIANT'
        assert 'meets minimum requirement' in evaluation['Annotation']
        assert evaluation['OrderingTimestamp'] == '2024-01-01T00:00:00Z'
    
    def test_create_evaluation_non_compliant(self):
        """Test creating a non-compliant evaluation"""
        event = {
            'invokingEvent': json.dumps({
                'notificationCreationTime': '2024-01-01T00:00:00Z'
            })
        }
        
        evaluation = create_evaluation(
            resource_id='/test/log',
            resource_type='AWS::Logs::LogGroup',
            current_retention=None,
            required_retention_days=30,
            event=event
        )
        
        assert evaluation['ComplianceType'] == 'NON_COMPLIANT'
        assert 'infinite retention' in evaluation['Annotation']


class TestSingleLogGroupEvaluation:
    """Test single log group evaluation"""
    
    def test_evaluate_single_log_group(self):
        """Test evaluating a single log group from configuration item"""
        configuration_item = {
            'resourceId': '/aws/lambda/test',
            'resourceType': 'AWS::Logs::LogGroup',
            'configurationItemCaptureTime': '2024-01-01T00:00:00Z',
            'configuration': {
                'retentionInDays': 7
            }
        }
        
        evaluation = evaluate_single_log_group(configuration_item, 30)
        
        assert evaluation['ComplianceResourceType'] == 'AWS::Logs::LogGroup'
        assert evaluation['ComplianceResourceId'] == '/aws/lambda/test'
        assert evaluation['ComplianceType'] == 'NON_COMPLIANT'
        assert evaluation['OrderingTimestamp'] == '2024-01-01T00:00:00Z'
    
    def test_evaluate_single_log_group_no_retention(self):
        """Test evaluating log group with no retention set"""
        configuration_item = {
            'resourceId': '/test/infinite',
            'resourceType': 'AWS::Logs::LogGroup',
            'configurationItemCaptureTime': '2024-01-01T00:00:00Z',
            'configuration': {}
        }
        
        evaluation = evaluate_single_log_group(configuration_item, 1)
        assert evaluation['ComplianceType'] == 'NON_COMPLIANT'
    
    def test_evaluate_deleted_log_group(self):
        """Test evaluating a deleted log group"""
        configuration_item = {
            'resourceId': '/aws/lambda/deleted',
            'resourceType': 'AWS::Logs::LogGroup',
            'configurationItemCaptureTime': '2024-01-01T00:00:00Z',
            'configurationItemStatus': 'ResourceDeleted',
            'configuration': {}
        }
        
        evaluation = evaluate_single_log_group(configuration_item, 30)
        
        assert evaluation['ComplianceType'] == 'NOT_APPLICABLE'
        assert 'deleted' in evaluation['Annotation'].lower()
    
    def test_evaluate_log_group_out_of_scope(self):
        """Test evaluating log group that left scope"""
        configuration_item = {
            'resourceId': '/aws/lambda/out-of-scope',
            'resourceType': 'AWS::Logs::LogGroup',
            'configurationItemCaptureTime': '2024-01-01T00:00:00Z',
            'eventLeftScope': True,
            'configuration': {'retentionInDays': 30}
        }
        
        evaluation = evaluate_single_log_group(configuration_item, 7)
        
        assert evaluation['ComplianceType'] == 'NOT_APPLICABLE'
        assert 'out of scope' in evaluation['Annotation'].lower()
    
    def test_evaluate_resource_deleted_not_recorded(self):
        """Test evaluating resource with ResourceDeletedNotRecorded status"""
        configuration_item = {
            'resourceId': '/test/deleted-not-recorded',
            'resourceType': 'AWS::Logs::LogGroup',
            'configurationItemCaptureTime': '2024-01-01T00:00:00Z',
            'configurationItemStatus': 'ResourceDeletedNotRecorded',
            'configuration': {}
        }
        
        evaluation = evaluate_single_log_group(configuration_item, 30)
        assert evaluation['ComplianceType'] == 'NOT_APPLICABLE'


class TestStaleEvaluationCleanup:
    """Test stale evaluation cleanup functionality"""
    
    @patch('lambda_function.boto3.client')
    def test_evaluate_all_with_deleted_resources(self, mock_boto_client):
        """Test that deleted resources are marked as NOT_APPLICABLE"""
        # Mock logs client and config client
        mock_logs_client = Mock()
        mock_config_client = Mock()
        
        # boto3.client is called to create config client inside evaluate_all_log_groups
        mock_boto_client.return_value = mock_config_client
        
        # Mock paginator for existing log groups
        mock_paginator = Mock()
        mock_logs_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [
            {
                'logGroups': [
                    {'logGroupName': '/existing/log', 'retentionInDays': 30}
                ]
            }
        ]
        
        # Mock config client for previous evaluations
        mock_config_client.get_compliance_details_by_config_rule.return_value = {
            'EvaluationResults': [
                {
                    'EvaluationResultIdentifier': {
                        'EvaluationResultQualifier': {
                            'ResourceId': '/existing/log'
                        }
                    }
                },
                {
                    'EvaluationResultIdentifier': {
                        'EvaluationResultQualifier': {
                            'ResourceId': '/deleted/log'  # This one no longer exists
                        }
                    }
                }
            ]
        }
        
        event = {
            'configRuleName': 'test-rule',
            'invokingEvent': json.dumps({
                'notificationCreationTime': '2024-01-01T00:00:00Z'
            })
        }
        
        evaluations = evaluate_all_log_groups(mock_logs_client, 30, event)
        
        # Should have 2 evaluations: 1 existing, 1 deleted
        assert len(evaluations) == 2
        
        # Find the evaluations
        existing_eval = next(e for e in evaluations if e['ComplianceResourceId'] == '/existing/log')
        deleted_eval = next(e for e in evaluations if e['ComplianceResourceId'] == '/deleted/log')
        
        assert existing_eval['ComplianceType'] == 'COMPLIANT'
        assert deleted_eval['ComplianceType'] == 'NOT_APPLICABLE'
        assert 'no longer exists' in deleted_eval['Annotation']
    
    @patch('lambda_function.boto3.client')
    def test_evaluate_all_with_pagination(self, mock_boto_client):
        """Test handling of paginated Config API responses"""
        mock_logs_client = Mock()
        mock_config_client = Mock()
        
        # boto3.client is called to create config client inside evaluate_all_log_groups
        mock_boto_client.return_value = mock_config_client
        
        # Mock empty log groups (all deleted)
        mock_paginator = Mock()
        mock_logs_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [{'logGroups': []}]
        
        # Mock paginated previous evaluations
        mock_config_client.get_compliance_details_by_config_rule.side_effect = [
            {
                'EvaluationResults': [
                    {
                        'EvaluationResultIdentifier': {
                            'EvaluationResultQualifier': {'ResourceId': '/deleted/log1'}
                        }
                    }
                ],
                'NextToken': 'token1'
            },
            {
                'EvaluationResults': [
                    {
                        'EvaluationResultIdentifier': {
                            'EvaluationResultQualifier': {'ResourceId': '/deleted/log2'}
                        }
                    }
                ]
            }
        ]
        
        event = {
            'configRuleName': 'test-rule',
            'invokingEvent': json.dumps({
                'notificationCreationTime': '2024-01-01T00:00:00Z'
            })
        }
        
        evaluations = evaluate_all_log_groups(mock_logs_client, 30, event)
        
        # Should have marked both as NOT_APPLICABLE
        assert len(evaluations) == 2
        assert all(e['ComplianceType'] == 'NOT_APPLICABLE' for e in evaluations)
    
    @patch('lambda_function.boto3.client')
    def test_evaluate_all_config_api_failure(self, mock_boto_client):
        """Test graceful handling when Config API fails"""
        mock_logs_client = Mock()
        mock_config_client = Mock()
        
        # boto3.client is called to create config client inside evaluate_all_log_groups
        mock_boto_client.return_value = mock_config_client
        
        # Mock log groups
        mock_paginator = Mock()
        mock_logs_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [
            {
                'logGroups': [
                    {'logGroupName': '/test/log', 'retentionInDays': 30}
                ]
            }
        ]
        
        # Mock Config API failure
        mock_config_client.get_compliance_details_by_config_rule.side_effect = Exception("Config API error")
        
        event = {
            'configRuleName': 'test-rule',
            'invokingEvent': json.dumps({
                'notificationCreationTime': '2024-01-01T00:00:00Z'
            })
        }
        
        # Should not fail, just skip stale cleanup
        evaluations = evaluate_all_log_groups(mock_logs_client, 30, event)
        
        # Should still have the existing log group evaluation
        assert len(evaluations) == 1
        assert evaluations[0]['ComplianceResourceId'] == '/test/log'


class TestConfigurationItem:
    """Test configuration item handling"""
    
    @patch('lambda_function.boto3.client')
    def test_get_configuration_item_oversized(self, mock_boto_client):
        """Test handling of oversized configuration items"""
        mock_config_client = Mock()
        mock_boto_client.return_value = mock_config_client
        
        # Mock API response for oversized item
        mock_config_client.get_resource_config_history.return_value = {
            'configurationItems': [
                {
                    'resourceId': '/test/log',
                    'resourceType': 'AWS::Logs::LogGroup',
                    'configurationItemCaptureTime': '2024-01-01T00:00:00Z',
                    'configuration': '{"retentionInDays": 30}'
                }
            ]
        }
        
        invoking_event = {
            'messageType': 'OversizedConfigurationItemChangeNotification',
            'configurationItemSummary': {
                'resourceType': 'AWS::Logs::LogGroup',
                'resourceId': '/test/log',
                'configurationItemCaptureTime': '2024-01-01T00:00:00Z'
            }
        }
        
        result = get_configuration_item(invoking_event, mock_config_client)
        
        assert result is not None
        assert result['resourceId'] == '/test/log'
        assert result['configuration']['retentionInDays'] == 30
    
    def test_get_configuration_item_standard(self):
        """Test handling of standard configuration items"""
        invoking_event = {
            'messageType': 'ConfigurationItemChangeNotification',
            'configurationItem': {
                'resourceId': '/test/log',
                'resourceType': 'AWS::Logs::LogGroup',
                'configuration': {'retentionInDays': 7}
            }
        }
        
        result = get_configuration_item(invoking_event, None)
        
        assert result is not None
        assert result['resourceId'] == '/test/log'
        assert result['configuration']['retentionInDays'] == 7
    
    @patch('lambda_function.boto3.client')
    def test_get_configuration_item_no_history(self, mock_boto_client):
        """Test handling when no configuration history is available"""
        mock_config_client = Mock()
        mock_boto_client.return_value = mock_config_client
        
        # Mock empty API response
        mock_config_client.get_resource_config_history.return_value = {
            'configurationItems': []
        }
        
        invoking_event = {
            'messageType': 'OversizedConfigurationItemChangeNotification',
            'configurationItemSummary': {
                'resourceType': 'AWS::Logs::LogGroup',
                'resourceId': '/test/log',
                'configurationItemCaptureTime': '2024-01-01T00:00:00Z'
            }
        }
        
        result = get_configuration_item(invoking_event, mock_config_client)
        assert result is None


class TestSubmitEvaluations:
    """Test evaluation submission"""
    
    @patch('lambda_function.boto3.client')
    def test_submit_evaluations_batching(self, mock_boto_client):
        """Test that evaluations are submitted in batches of 100"""
        mock_config_client = Mock()
        
        # Create 250 evaluations to test batching
        evaluations = []
        for i in range(250):
            evaluations.append({
                'ComplianceResourceType': 'AWS::Logs::LogGroup',
                'ComplianceResourceId': f'/test/log{i}',
                'ComplianceType': 'COMPLIANT',
                'Annotation': 'Test',
                'OrderingTimestamp': datetime.now()
            })
        
        event = {'resultToken': 'test-token'}
        
        submit_evaluations(mock_config_client, evaluations, event)
        
        # Should have been called 3 times (100, 100, 50)
        assert mock_config_client.put_evaluations.call_count == 3
        
        # Check batch sizes
        calls = mock_config_client.put_evaluations.call_args_list
        assert len(calls[0][1]['Evaluations']) == 100
        assert len(calls[1][1]['Evaluations']) == 100
        assert len(calls[2][1]['Evaluations']) == 50
    
    @patch('lambda_function.boto3.client')
    def test_submit_evaluations_datetime_conversion(self, mock_boto_client):
        """Test that datetime objects are converted to strings"""
        mock_config_client = Mock()
        
        evaluations = [{
            'ComplianceResourceType': 'AWS::Logs::LogGroup',
            'ComplianceResourceId': '/test/log',
            'ComplianceType': 'COMPLIANT',
            'Annotation': 'Test',
            'OrderingTimestamp': datetime(2024, 1, 1, 12, 0, 0)
        }]
        
        event = {'resultToken': 'test-token'}
        
        submit_evaluations(mock_config_client, evaluations, event)
        
        # Check that datetime was converted to string
        args = mock_config_client.put_evaluations.call_args
        submitted_eval = args[1]['Evaluations'][0]
        assert isinstance(submitted_eval['OrderingTimestamp'], str)
        assert submitted_eval['OrderingTimestamp'] == '2024-01-01T12:00:00'


class TestLambdaHandler:
    """Test main lambda handler function"""
    
    @patch('lambda_function.boto3.client')
    def test_lambda_handler_scheduled_notification(self, mock_boto_client):
        """Test lambda handler with scheduled notification"""
        # Mock clients
        mock_logs_client = Mock()
        mock_config_client = Mock()
        mock_boto_client.side_effect = [mock_config_client, mock_logs_client, mock_config_client]  # Need config client twice now
        
        # Mock paginator
        mock_paginator = Mock()
        mock_logs_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [
            {
                'logGroups': [
                    {
                        'logGroupName': '/aws/lambda/test',
                        'retentionInDays': 7
                    },
                    {
                        'logGroupName': '/test/infinite'
                        # No retentionInDays = infinite retention
                    }
                ]
            }
        ]
        
        # Mock empty previous evaluations (no stale cleanup needed)
        mock_config_client.get_compliance_details_by_config_rule.return_value = {
            'EvaluationResults': []
        }
        
        # Test event
        event = {
            'invokingEvent': json.dumps({
                'messageType': 'ScheduledNotification',
                'notificationCreationTime': '2024-01-01T00:00:00Z'
            }),
            'ruleParameters': json.dumps({
                'MinimumRetentionDays': '30'
            }),
            'resultToken': 'test-token',
            'configRuleName': 'test-rule'
        }
        
        result = lambda_handler(event, {})
        
        # Verify result
        assert result['statusCode'] == 200
        body = json.loads(result['body'])
        assert body['evaluations_count'] >= 2  # May have more if stale cleanup occurs
        
        # Verify put_evaluations was called
        mock_config_client.put_evaluations.assert_called_once()
        args = mock_config_client.put_evaluations.call_args
        evaluations = args[1]['Evaluations']
        
        # Check evaluations - find the specific ones we care about
        test_eval = next((e for e in evaluations if e['ComplianceResourceId'] == '/aws/lambda/test'), None)
        infinite_eval = next((e for e in evaluations if e['ComplianceResourceId'] == '/test/infinite'), None)
        
        assert test_eval is not None
        assert test_eval['ComplianceType'] == 'NON_COMPLIANT'  # 7 days < 30
        assert infinite_eval is not None
        assert infinite_eval['ComplianceType'] == 'NON_COMPLIANT'  # infinite
    
    @patch('lambda_function.boto3.client')
    def test_lambda_handler_error_handling(self, mock_boto_client):
        """Test lambda handler error handling"""
        mock_config_client = Mock()
        mock_logs_client = Mock()
        mock_boto_client.side_effect = [mock_config_client, mock_logs_client]
        
        # Make logs client raise an exception
        mock_logs_client.get_paginator.side_effect = Exception("AWS Error")
        
        event = {
            'invokingEvent': json.dumps({
                'messageType': 'ScheduledNotification',
                'notificationCreationTime': '2024-01-01T00:00:00Z'
            }),
            'accountId': '123456789012',
            'resultToken': 'test-token'
        }
        
        result = lambda_handler(event, {})
        
        # Should still return 200 but with error evaluation
        assert result['statusCode'] == 200
        
        # Should submit NOT_APPLICABLE evaluation
        mock_config_client.put_evaluations.assert_called_once()
        args = mock_config_client.put_evaluations.call_args
        evaluations = args[1]['Evaluations']
        
        assert len(evaluations) == 1
        assert evaluations[0]['ComplianceType'] == 'NOT_APPLICABLE'
        assert 'Error during evaluation' in evaluations[0]['Annotation']
    
    @patch('lambda_function.boto3.client')
    def test_lambda_handler_configuration_change(self, mock_boto_client):
        """Test lambda handler with configuration change notification"""
        mock_config_client = Mock()
        mock_boto_client.return_value = mock_config_client
        
        event = {
            'invokingEvent': json.dumps({
                'messageType': 'ConfigurationItemChangeNotification',
                'configurationItem': {
                    'resourceId': '/test/log',
                    'resourceType': 'AWS::Logs::LogGroup',
                    'configurationItemCaptureTime': '2024-01-01T00:00:00Z',
                    'configuration': {
                        'retentionInDays': 7
                    }
                }
            }),
            'ruleParameters': json.dumps({
                'MinimumRetentionDays': '30'
            }),
            'resultToken': 'test-token'
        }
        
        result = lambda_handler(event, {})
        
        assert result['statusCode'] == 200
        body = json.loads(result['body'])
        assert body['evaluations_count'] == 1
        
        # Verify evaluation was submitted
        mock_config_client.put_evaluations.assert_called_once()
        args = mock_config_client.put_evaluations.call_args
        evaluations = args[1]['Evaluations']
        
        assert len(evaluations) == 1
        assert evaluations[0]['ComplianceResourceId'] == '/test/log'
        assert evaluations[0]['ComplianceType'] == 'NON_COMPLIANT'
    
    def test_lambda_handler_parameter_parsing(self):
        """Test parameter parsing from event"""
        with patch.dict(os.environ, {'REQUIRED_RETENTION_DAYS': '14'}):
            event = {
                'invokingEvent': json.dumps({
                    'messageType': 'ScheduledNotification',
                    'notificationCreationTime': '2024-01-01T00:00:00Z'
                }),
                'ruleParameters': json.dumps({
                    'MinimumRetentionDays': '30'
                }),
                'resultToken': 'test-token'
            }
            
            with patch('lambda_function.boto3.client'), \
                 patch('lambda_function.evaluate_all_log_groups') as mock_eval:
                mock_eval.return_value = []
                
                lambda_handler(event, {})
                
                # Should use rule parameter (30) over environment variable (14)
                mock_eval.assert_called_once()
                args = mock_eval.call_args[0]
                required_retention = args[1]  # Second argument
                assert required_retention == 30


if __name__ == '__main__':
    pytest.main([__file__, '-v'])