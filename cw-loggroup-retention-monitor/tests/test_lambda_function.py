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


class TestLambdaHandler:
    """Test main lambda handler function"""
    
    @patch('lambda_function.boto3.client')
    def test_lambda_handler_scheduled_notification(self, mock_boto_client):
        """Test lambda handler with scheduled notification"""
        # Mock clients
        mock_logs_client = Mock()
        mock_config_client = Mock()
        mock_boto_client.side_effect = [mock_config_client, mock_logs_client]
        
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
        
        # Test event
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
        
        result = lambda_handler(event, {})
        
        # Verify result
        assert result['statusCode'] == 200
        body = json.loads(result['body'])
        assert body['evaluations_count'] == 2
        
        # Verify put_evaluations was called
        mock_config_client.put_evaluations.assert_called_once()
        args = mock_config_client.put_evaluations.call_args
        evaluations = args[1]['Evaluations']
        
        # Check evaluations
        assert len(evaluations) == 2
        assert evaluations[0]['ComplianceType'] == 'NON_COMPLIANT'  # 7 days < 30
        assert evaluations[1]['ComplianceType'] == 'NON_COMPLIANT'  # infinite
    
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