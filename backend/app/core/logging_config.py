"""
Logging Configuration Management for Medical AI Platform

This module provides configuration management for the unified logging system:
- Environment-based configuration
- Service-specific log levels
- Log retention policies
- Performance tracking configuration
"""

import os
import yaml
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import logging
from collections import defaultdict

from app.core.unified_logging import get_logger, LOG_DIR


class LoggingConfig:
    """Centralized logging configuration management"""
    
    def __init__(self):
        self.logger = get_logger('logging.config')
        self.config = self._load_config()
        self.performance_stats = defaultdict(lambda: {
            'count': 0,
            'total_time': 0,
            'errors': 0,
            'last_reset': datetime.now()
        })
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from environment and config files"""
        config = {
            'environment': os.getenv('ENVIRONMENT', 'development'),
            'log_level': os.getenv('LOG_LEVEL', 'INFO'),
            'log_dir': os.getenv('LOG_DIR', './logs'),
            'json_format': os.getenv('LOG_JSON', 'false').lower() == 'true',
            'console_output': os.getenv('LOG_CONSOLE', 'true').lower() == 'true',
            'file_output': os.getenv('LOG_FILE', 'true').lower() == 'true',
            'max_file_size_mb': int(os.getenv('LOG_MAX_FILE_SIZE_MB', '100')),
            'backup_count': int(os.getenv('LOG_BACKUP_COUNT', '10')),
            'retention_days': int(os.getenv('LOG_RETENTION_DAYS', '30')),
            
            # Medical-specific settings
            'hipaa_compliant': os.getenv('HIPAA_COMPLIANT', 'true').lower() == 'true',
            'mask_pii': os.getenv('MASK_PII', 'true').lower() == 'true',
            'audit_retention_days': int(os.getenv('AUDIT_RETENTION_DAYS', '2555')),  # 7 years
            
            # Performance settings
            'slow_request_threshold_ms': float(os.getenv('SLOW_REQUEST_THRESHOLD_MS', '1000')),
            'performance_tracking': os.getenv('PERFORMANCE_TRACKING', 'true').lower() == 'true',
            
            # Service-specific levels
            'service_levels': {
                'medical_mcp': os.getenv('MCP_LOG_LEVEL', 'INFO'),
                'groq_doctors': os.getenv('GROQ_LOG_LEVEL', 'INFO'),
                'database': os.getenv('DB_LOG_LEVEL', 'INFO'),
                'api': os.getenv('API_LOG_LEVEL', 'INFO'),
                'security': os.getenv('SECURITY_LOG_LEVEL', 'INFO'),
                'performance': os.getenv('PERF_LOG_LEVEL', 'INFO'),
            },
            
            # Log categories
            'categories': {
                'security': {
                    'enabled': True,
                    'file': 'security.log',
                    'retention_days': 90,
                    'level': 'INFO'
                },
                'audit': {
                    'enabled': True,
                    'file': 'audit.log',
                    'retention_days': 2555,  # 7 years for HIPAA
                    'level': 'INFO'
                },
                'performance': {
                    'enabled': True,
                    'file': 'performance.log',
                    'retention_days': 7,
                    'level': 'INFO'
                },
                'medical': {
                    'enabled': True,
                    'file': 'medical_operations.log',
                    'retention_days': 2555,  # 7 years for HIPAA
                    'level': 'INFO'
                },
                'ai_model': {
                    'enabled': True,
                    'file': 'ai_interactions.log',
                    'retention_days': 30,
                    'level': 'INFO'
                }
            }
        }
        
        # Try to load from config file if exists
        config_file = Path('logging_config.yaml')
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    file_config = yaml.safe_load(f)
                    config.update(file_config)
            except Exception as e:
                self.logger.error(f"Failed to load config file: {e}")
        
        return config
    
    def get_service_level(self, service: str) -> str:
        """Get log level for a specific service"""
        return self.config['service_levels'].get(service, self.config['log_level'])
    
    def get_category_config(self, category: str) -> Dict[str, Any]:
        """Get configuration for a log category"""
        return self.config['categories'].get(category, {})
    
    def should_mask_pii(self) -> bool:
        """Check if PII should be masked"""
        return self.config.get('mask_pii', True) and self.config.get('hipaa_compliant', True)
    
    def get_retention_policy(self, category: str) -> int:
        """Get retention days for a log category"""
        cat_config = self.get_category_config(category)
        return cat_config.get('retention_days', self.config['retention_days'])
    
    def update_performance_stats(self, operation: str, duration_ms: float, error: bool = False):
        """Update performance statistics"""
        stats = self.performance_stats[operation]
        stats['count'] += 1
        stats['total_time'] += duration_ms
        if error:
            stats['errors'] += 1
        
        # Reset stats daily
        if datetime.now() - stats['last_reset'] > timedelta(days=1):
            self.logger.info(
                f"Daily performance stats for {operation}",
                extra={
                    'performance_summary': True,
                    'operation': operation,
                    'total_requests': stats['count'],
                    'average_time_ms': stats['total_time'] / stats['count'] if stats['count'] > 0 else 0,
                    'error_rate': stats['errors'] / stats['count'] if stats['count'] > 0 else 0
                }
            )
            # Reset stats
            stats['count'] = 0
            stats['total_time'] = 0
            stats['errors'] = 0
            stats['last_reset'] = datetime.now()
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary for all operations"""
        summary = {}
        for operation, stats in self.performance_stats.items():
            if stats['count'] > 0:
                summary[operation] = {
                    'count': stats['count'],
                    'average_ms': stats['total_time'] / stats['count'],
                    'error_rate': stats['errors'] / stats['count'],
                    'since': stats['last_reset'].isoformat()
                }
        return summary
    
    def cleanup_old_logs(self):
        """Clean up logs older than retention policy"""
        self.logger.info("Starting log cleanup")
        
        for category, config in self.config['categories'].items():
            if not config.get('enabled', True):
                continue
                
            retention_days = config.get('retention_days', self.config['retention_days'])
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            
            # Find and remove old log files
            log_pattern = f"{config.get('file', category)}.*.log"
            for log_file in LOG_DIR.glob(log_pattern):
                try:
                    if datetime.fromtimestamp(log_file.stat().st_mtime) < cutoff_date:
                        log_file.unlink()
                        self.logger.info(f"Deleted old log file: {log_file}")
                except Exception as e:
                    self.logger.error(f"Failed to delete log file {log_file}: {e}")
    
    def export_config(self) -> str:
        """Export current configuration as JSON"""
        return json.dumps(self.config, indent=2, default=str)
    
    def validate_config(self) -> List[str]:
        """Validate configuration and return any issues"""
        issues = []
        
        # Check log directory exists and is writable
        try:
            test_file = LOG_DIR / '.test'
            test_file.touch()
            test_file.unlink()
        except Exception as e:
            issues.append(f"Log directory not writable: {LOG_DIR}")
        
        # Check log levels are valid
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        for service, level in self.config['service_levels'].items():
            if level.upper() not in valid_levels:
                issues.append(f"Invalid log level for {service}: {level}")
        
        # Check retention policies
        if self.config.get('hipaa_compliant', True):
            audit_retention = self.config['categories']['audit']['retention_days']
            medical_retention = self.config['categories']['medical']['retention_days']
            if audit_retention < 2555 or medical_retention < 2555:
                issues.append("HIPAA compliance requires 7-year retention for audit and medical logs")
        
        return issues


# Global configuration instance
_config_instance = None

def get_logging_config() -> LoggingConfig:
    """Get or create logging configuration instance"""
    global _config_instance
    if _config_instance is None:
        _config_instance = LoggingConfig()
    return _config_instance


def initialize_logging():
    """Initialize logging system with configuration"""
    from app.core.unified_logging import initialize_unified_logging
    
    # Initialize unified logging
    logger = initialize_unified_logging()
    
    # Get configuration
    config = get_logging_config()
    
    # Validate configuration
    issues = config.validate_config()
    if issues:
        for issue in issues:
            logger.warning(f"Configuration issue: {issue}")
    
    # Log configuration
    logger.info(
        "Logging system initialized",
        extra={
            'config': config.export_config(),
            'issues': issues
        }
    )
    
    # Schedule cleanup if in production
    if config.config['environment'] == 'production':
        import asyncio
        from datetime import time
        
        async def daily_cleanup():
            while True:
                # Wait until 2 AM
                now = datetime.now()
                next_run = now.replace(hour=2, minute=0, second=0, microsecond=0)
                if next_run <= now:
                    next_run += timedelta(days=1)
                
                wait_seconds = (next_run - now).total_seconds()
                await asyncio.sleep(wait_seconds)
                
                # Run cleanup
                config.cleanup_old_logs()
        
        # Start cleanup task
        asyncio.create_task(daily_cleanup())
    
    return logger


# Performance tracking decorator that uses config
def track_performance(operation_name: Optional[str] = None):
    """Decorator to track performance with configuration"""
    def decorator(func):
        from app.core.unified_logging import log_performance
        
        config = get_logging_config()
        if not config.config.get('performance_tracking', True):
            # Performance tracking disabled, return original function
            return func
        
        # Use the unified logging performance decorator
        return log_performance(operation_name)(func)
    
    return decorator


# HIPAA-compliant logger for medical operations
class HIPAACompliantLogger:
    """Logger that ensures HIPAA compliance for medical data"""
    
    def __init__(self, name: str):
        self.logger = get_logger(name)
        self.config = get_logging_config()
    
    def _mask_pii(self, data: Any) -> Any:
        """Mask PII in data"""
        if not self.config.should_mask_pii():
            return data
        
        if isinstance(data, dict):
            masked = {}
            pii_fields = ['ssn', 'patient_id', 'medical_record_number', 'phone', 
                         'email', 'address', 'date_of_birth', 'insurance_id']
            
            for key, value in data.items():
                if any(pii in key.lower() for pii in pii_fields):
                    if isinstance(value, str) and len(value) > 4:
                        masked[key] = f"***{value[-4:]}"
                    else:
                        masked[key] = "****"
                elif isinstance(value, (dict, list)):
                    masked[key] = self._mask_pii(value)
                else:
                    masked[key] = value
            return masked
        
        elif isinstance(data, list):
            return [self._mask_pii(item) for item in data]
        
        return data
    
    def log_medical_operation(self, operation: str, patient_data: Dict[str, Any], 
                             action: str, user_id: str):
        """Log medical operation with HIPAA compliance"""
        masked_data = self._mask_pii(patient_data)
        
        self.logger.medical_operation(
            operation,
            patient_id=masked_data.get('patient_id'),
            details={
                'action': action,
                'user': user_id,
                'data': masked_data
            },
            hipaa_compliant=True
        )
        
        # Also create audit trail
        self.logger.audit(
            action=action,
            entity='medical_record',
            entity_id=masked_data.get('patient_id', 'unknown'),
            changes={'operation': operation}
        )


def get_hipaa_logger(name: str) -> HIPAACompliantLogger:
    """Get HIPAA-compliant logger instance"""
    return HIPAACompliantLogger(name)