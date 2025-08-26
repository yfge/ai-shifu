# AI-Shifu SaaS Migration Plan Design

## Overview

This document outlines the comprehensive migration strategy for transforming the current AI-Shifu platform into a multi-tenant SaaS system. The migration plan ensures zero-downtime transition, data integrity, and seamless user experience while implementing all the architectural changes defined in previous design documents.

## 1. Migration Strategy Overview

### 1.1 Migration Approach

```
Current State → Transition State → Target SaaS State
     │                │                    │
 Single-Tenant   Hybrid System      Multi-Tenant SaaS
 Monolithic      (Parallel Run)     Microservices
     │                │                    │
     └────────────────┼────────────────────┘
                      │
               Migration Bridge
            (Data Sync & Routing)
```

### 1.2 Migration Principles

- **Zero-Downtime Migration**: Maintain service availability throughout
- **Incremental Approach**: Migrate in phases with rollback capabilities
- **Data Integrity**: Ensure no data loss during migration
- **User Experience**: Transparent migration for end users
- **Scalability First**: Design for future growth from day one
- **Security By Design**: Implement security controls from the start

### 1.3 Migration Timeline

```
Phase 1: Foundation     │ 4 weeks  │ Infrastructure & Core Services
Phase 2: Data Migration │ 3 weeks  │ Database Schema & Data Transfer
Phase 3: Application    │ 4 weeks  │ Multi-tenant Application Layer
Phase 4: Integration    │ 3 weeks  │ OAuth, Billing, Monitoring
Phase 5: Go-Live        │ 2 weeks  │ Final Migration & Cleanup
Total Duration: 16 weeks
```

## 2. Pre-Migration Assessment

### 2.1 Current System Analysis

```sql
-- Current System Inventory
SELECT
    'Users' as entity,
    COUNT(*) as count,
    MIN(created_at) as earliest_record,
    MAX(created_at) as latest_record
FROM user_users
UNION ALL
SELECT
    'Orders' as entity,
    COUNT(*) as count,
    MIN(created_at) as earliest_record,
    MAX(created_at) as latest_record
FROM order_orders
UNION ALL
SELECT
    'Study Records' as entity,
    COUNT(*) as count,
    MIN(created_at) as earliest_record,
    MAX(created_at) as latest_record
FROM study_records
UNION ALL
SELECT
    'Shifu Outlines' as entity,
    COUNT(*) as count,
    MIN(created_at) as earliest_record,
    MAX(created_at) as latest_record
FROM shifu_outlines;
```

```python
# Migration Assessment Script
import pymysql
from typing import Dict, List
import logging

class MigrationAssessment:
    def __init__(self, db_config: dict):
        self.db_config = db_config
        self.logger = logging.getLogger(__name__)

    def analyze_current_system(self) -> Dict:
        """Analyze current system for migration planning"""

        connection = pymysql.connect(**self.db_config)
        cursor = connection.cursor()

        assessment = {
            'database_size': self._get_database_size(cursor),
            'table_analysis': self._analyze_tables(cursor),
            'data_volume': self._analyze_data_volume(cursor),
            'foreign_keys': self._analyze_foreign_keys(cursor),
            'indexes': self._analyze_indexes(cursor),
            'migration_complexity': {},
            'estimated_duration': {}
        }

        # Analyze migration complexity for each table
        for table in assessment['table_analysis']:
            complexity = self._assess_table_complexity(cursor, table['name'])
            assessment['migration_complexity'][table['name']] = complexity

        connection.close()
        return assessment

    def _get_database_size(self, cursor) -> Dict:
        """Get current database size information"""
        cursor.execute("""
            SELECT
                table_schema as 'database',
                ROUND(SUM(data_length + index_length) / 1024 / 1024, 1) as 'size_mb'
            FROM information_schema.tables
            WHERE table_schema = DATABASE()
            GROUP BY table_schema
        """)
        result = cursor.fetchone()
        return {'database': result[0], 'size_mb': result[1]} if result else {}

    def _analyze_tables(self, cursor) -> List[Dict]:
        """Analyze all tables for migration planning"""
        cursor.execute("""
            SELECT
                table_name,
                table_rows,
                ROUND((data_length + index_length) / 1024 / 1024, 2) as size_mb,
                data_length,
                index_length,
                create_time,
                update_time
            FROM information_schema.tables
            WHERE table_schema = DATABASE()
            AND table_type = 'BASE TABLE'
            ORDER BY (data_length + index_length) DESC
        """)

        tables = []
        for row in cursor.fetchall():
            tables.append({
                'name': row[0],
                'rows': row[1] or 0,
                'size_mb': row[2] or 0,
                'data_length': row[3] or 0,
                'index_length': row[4] or 0,
                'created_at': row[5],
                'updated_at': row[6]
            })

        return tables

    def _assess_table_complexity(self, cursor, table_name: str) -> Dict:
        """Assess migration complexity for a specific table"""

        # Check for tenant identification columns
        cursor.execute(f"""
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = '{table_name}'
            AND COLUMN_NAME LIKE '%tenant%' OR COLUMN_NAME LIKE '%user_bid%'
        """)
        tenant_columns = [row[0] for row in cursor.fetchall()]

        # Check for foreign key dependencies
        cursor.execute(f"""
            SELECT COUNT(*) as fk_count
            FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = '{table_name}'
            AND REFERENCED_TABLE_NAME IS NOT NULL
        """)
        fk_count = cursor.fetchone()[0]

        # Determine complexity level
        complexity_score = 0
        factors = []

        if not tenant_columns:
            complexity_score += 3
            factors.append("No tenant identification columns")

        if fk_count > 5:
            complexity_score += 2
            factors.append(f"High foreign key dependencies ({fk_count})")
        elif fk_count > 0:
            complexity_score += 1
            factors.append(f"Moderate foreign key dependencies ({fk_count})")

        if table_name.startswith('user_'):
            complexity_score += 2
            factors.append("User-related table requiring special handling")

        complexity_levels = {
            0: 'Low',
            1: 'Low',
            2: 'Medium',
            3: 'Medium',
            4: 'High',
            5: 'High'
        }

        return {
            'score': complexity_score,
            'level': complexity_levels.get(complexity_score, 'Very High'),
            'factors': factors
        }

# Usage
assessor = MigrationAssessment({
    'host': 'localhost',
    'user': 'root',
    'password': 'password',
    'database': 'ai_shifu'
})

assessment_result = assessor.analyze_current_system()
```

## 3. Phase 1: Foundation Infrastructure (Weeks 1-4)

### 3.1 Infrastructure Setup

```yaml
# Migration Infrastructure Deployment
apiVersion: v1
kind: Namespace
metadata:
  name: ai-shifu-migration
  labels:
    purpose: migration
    stage: foundation

---
# Migration Database (Temporary)
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: migration-mysql
  namespace: ai-shifu-migration
spec:
  serviceName: migration-mysql
  replicas: 1
  selector:
    matchLabels:
      app: migration-mysql
  template:
    metadata:
      labels:
        app: migration-mysql
    spec:
      containers:
      - name: mysql
        image: mysql:8.0
        env:
        - name: MYSQL_ROOT_PASSWORD
          valueFrom:
            secretKeyRef:
              name: migration-mysql-secret
              key: root-password
        - name: MYSQL_DATABASE
          value: ai_shifu_migration
        ports:
        - containerPort: 3306
        volumeMounts:
        - name: mysql-data
          mountPath: /var/lib/mysql
        - name: mysql-config
          mountPath: /etc/mysql/conf.d
        resources:
          requests:
            cpu: 1000m
            memory: 2Gi
          limits:
            cpu: 2000m
            memory: 4Gi
      volumes:
      - name: mysql-config
        configMap:
          name: migration-mysql-config
  volumeClaimTemplates:
  - metadata:
      name: mysql-data
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 100Gi

---
# Migration Service
apiVersion: apps/v1
kind: Deployment
metadata:
  name: migration-service
  namespace: ai-shifu-migration
spec:
  replicas: 1
  selector:
    matchLabels:
      app: migration-service
  template:
    metadata:
      labels:
        app: migration-service
    spec:
      containers:
      - name: migration-service
        image: ai-shifu-migration:latest
        env:
        - name: SOURCE_DB_URL
          valueFrom:
            secretKeyRef:
              name: source-db-credentials
              key: url
        - name: TARGET_DB_URL
          valueFrom:
            secretKeyRef:
              name: target-db-credentials
              key: url
        - name: MIGRATION_MODE
          value: "phase1"
        resources:
          requests:
            cpu: 500m
            memory: 1Gi
          limits:
            cpu: 1000m
            memory: 2Gi
        volumeMounts:
        - name: migration-scripts
          mountPath: /app/scripts
      volumes:
      - name: migration-scripts
        configMap:
          name: migration-scripts
```

### 3.2 Database Schema Migration

```sql
-- Phase 1: Create new tenant-aware schema
-- 1. Create tenant management tables
CREATE TABLE tenant_tenants (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_bid VARCHAR(32) NOT NULL UNIQUE INDEX,
    name VARCHAR(100) NOT NULL,
    domain VARCHAR(100) UNIQUE,
    tier VARCHAR(20) NOT NULL DEFAULT 'standard',
    status SMALLINT NOT NULL DEFAULT 1,
    settings JSON,
    subscription_plan VARCHAR(50),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted SMALLINT NOT NULL DEFAULT 0 INDEX
);

-- 2. Create default tenant for existing data
INSERT INTO tenant_tenants (tenant_bid, name, domain, tier, status)
VALUES ('default', 'Default Tenant', 'default.ai-shifu.com', 'enterprise', 1);

-- 3. Add tenant_bid columns to existing tables (Phase 1)
ALTER TABLE user_users
ADD COLUMN tenant_bid VARCHAR(32) NOT NULL DEFAULT 'default' AFTER user_bid,
ADD INDEX idx_tenant_user (tenant_bid, user_bid);

ALTER TABLE order_orders
ADD COLUMN tenant_bid VARCHAR(32) NOT NULL DEFAULT 'default' AFTER order_bid,
ADD INDEX idx_tenant_order (tenant_bid, order_bid);

ALTER TABLE shifu_outlines
ADD COLUMN tenant_bid VARCHAR(32) NOT NULL DEFAULT 'default' AFTER outline_bid,
ADD INDEX idx_tenant_outline (tenant_bid, outline_bid);

ALTER TABLE study_records
ADD COLUMN tenant_bid VARCHAR(32) NOT NULL DEFAULT 'default' AFTER record_bid,
ADD INDEX idx_tenant_record (tenant_bid, record_bid);

-- 4. Update existing data with default tenant
UPDATE user_users SET tenant_bid = 'default' WHERE tenant_bid = '';
UPDATE order_orders SET tenant_bid = 'default' WHERE tenant_bid = '';
UPDATE shifu_outlines SET tenant_bid = 'default' WHERE tenant_bid = '';
UPDATE study_records SET tenant_bid = 'default' WHERE tenant_bid = '';

-- 5. Create migration tracking table
CREATE TABLE migration_progress (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    phase VARCHAR(20) NOT NULL,
    table_name VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    started_at DATETIME,
    completed_at DATETIME,
    records_total BIGINT DEFAULT 0,
    records_migrated BIGINT DEFAULT 0,
    error_message TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_phase_table (phase, table_name)
);
```

### 3.3 Migration Service Implementation

```python
# Migration Service Core
from dataclasses import dataclass
from typing import Dict, List, Optional, Callable
from datetime import datetime
import logging
import asyncio
import pymysql
from contextlib import contextmanager

@dataclass
class MigrationTask:
    phase: str
    name: str
    table_name: str
    priority: int
    depends_on: List[str]
    migration_func: Callable
    rollback_func: Optional[Callable] = None
    validation_func: Optional[Callable] = None

class MigrationOrchestrator:
    def __init__(self, source_db_config: dict, target_db_config: dict):
        self.source_db = source_db_config
        self.target_db = target_db_config
        self.logger = logging.getLogger(__name__)
        self.tasks = []
        self.current_phase = None

    @contextmanager
    def get_db_connection(self, config: dict):
        """Get database connection with proper cleanup"""
        connection = pymysql.connect(**config)
        try:
            yield connection
        finally:
            connection.close()

    def register_migration_task(self, task: MigrationTask):
        """Register a migration task"""
        self.tasks.append(task)
        self.logger.info(f"Registered migration task: {task.name}")

    async def execute_phase(self, phase: str) -> bool:
        """Execute all tasks for a specific phase"""
        self.current_phase = phase
        phase_tasks = [task for task in self.tasks if task.phase == phase]
        phase_tasks.sort(key=lambda x: x.priority)

        self.logger.info(f"Starting migration phase: {phase} with {len(phase_tasks)} tasks")

        # Track phase progress
        self._update_migration_progress(phase, 'phase_start', 'in_progress')

        try:
            for task in phase_tasks:
                # Check dependencies
                if not self._check_dependencies(task):
                    self.logger.error(f"Dependencies not met for task: {task.name}")
                    return False

                # Execute task
                success = await self._execute_task(task)
                if not success:
                    self.logger.error(f"Task failed: {task.name}")
                    await self._rollback_phase(phase, task)
                    return False

            self.logger.info(f"Phase {phase} completed successfully")
            self._update_migration_progress(phase, 'phase_complete', 'completed')
            return True

        except Exception as e:
            self.logger.error(f"Phase {phase} failed with error: {str(e)}")
            self._update_migration_progress(phase, 'phase_error', 'failed', str(e))
            return False

    async def _execute_task(self, task: MigrationTask) -> bool:
        """Execute a single migration task"""

        self.logger.info(f"Executing task: {task.name}")
        self._update_migration_progress(
            task.phase, task.table_name, 'in_progress',
            started_at=datetime.utcnow()
        )

        try:
            # Execute the migration function
            result = await task.migration_func()

            # Validate if validation function provided
            if task.validation_func:
                validation_result = await task.validation_func()
                if not validation_result:
                    raise Exception("Task validation failed")

            self.logger.info(f"Task completed: {task.name}")
            self._update_migration_progress(
                task.phase, task.table_name, 'completed',
                completed_at=datetime.utcnow()
            )
            return True

        except Exception as e:
            self.logger.error(f"Task {task.name} failed: {str(e)}")
            self._update_migration_progress(
                task.phase, task.table_name, 'failed',
                error_message=str(e)
            )
            return False

    async def _rollback_phase(self, phase: str, failed_task: MigrationTask):
        """Rollback all completed tasks in a phase"""

        self.logger.info(f"Rolling back phase: {phase}")
        phase_tasks = [task for task in self.tasks if task.phase == phase]

        # Find tasks that were completed before the failure
        completed_tasks = []
        for task in phase_tasks:
            if task.priority < failed_task.priority and task.rollback_func:
                completed_tasks.append(task)

        # Rollback in reverse order
        completed_tasks.reverse()

        for task in completed_tasks:
            try:
                await task.rollback_func()
                self.logger.info(f"Rolled back task: {task.name}")
            except Exception as e:
                self.logger.error(f"Rollback failed for task {task.name}: {str(e)}")

    def _update_migration_progress(self, phase: str, table_name: str,
                                 status: str, error_message: str = None,
                                 started_at: datetime = None,
                                 completed_at: datetime = None):
        """Update migration progress in database"""

        with self.get_db_connection(self.target_db) as conn:
            cursor = conn.cursor()

            # Insert or update progress record
            sql = """
                INSERT INTO migration_progress
                (phase, table_name, status, started_at, completed_at, error_message)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    status = VALUES(status),
                    started_at = COALESCE(VALUES(started_at), started_at),
                    completed_at = VALUES(completed_at),
                    error_message = VALUES(error_message),
                    updated_at = CURRENT_TIMESTAMP
            """

            cursor.execute(sql, (
                phase, table_name, status, started_at, completed_at, error_message
            ))
            conn.commit()

# Phase 1 Migration Tasks Implementation
class Phase1Migration:
    def __init__(self, orchestrator: MigrationOrchestrator):
        self.orchestrator = orchestrator
        self.logger = logging.getLogger(__name__)
        self._register_tasks()

    def _register_tasks(self):
        """Register Phase 1 migration tasks"""

        # Task 1: Create tenant management schema
        self.orchestrator.register_migration_task(MigrationTask(
            phase='phase1',
            name='Create Tenant Schema',
            table_name='tenant_tenants',
            priority=1,
            depends_on=[],
            migration_func=self._create_tenant_schema,
            rollback_func=self._rollback_tenant_schema,
            validation_func=self._validate_tenant_schema
        ))

        # Task 2: Add tenant columns to existing tables
        self.orchestrator.register_migration_task(MigrationTask(
            phase='phase1',
            name='Add Tenant Columns',
            table_name='user_users',
            priority=2,
            depends_on=['tenant_tenants'],
            migration_func=self._add_tenant_columns,
            rollback_func=self._rollback_tenant_columns,
            validation_func=self._validate_tenant_columns
        ))

        # Task 3: Populate default tenant data
        self.orchestrator.register_migration_task(MigrationTask(
            phase='phase1',
            name='Populate Default Tenant',
            table_name='default_data',
            priority=3,
            depends_on=['user_users'],
            migration_func=self._populate_default_tenant,
            validation_func=self._validate_default_tenant_data
        ))

    async def _create_tenant_schema(self) -> bool:
        """Create tenant management schema"""

        with self.orchestrator.get_db_connection(self.orchestrator.target_db) as conn:
            cursor = conn.cursor()

            # Read schema creation script
            schema_sql = self._read_sql_file('phase1/01_create_tenant_schema.sql')

            # Execute schema creation
            for statement in schema_sql.split(';'):
                if statement.strip():
                    cursor.execute(statement)

            conn.commit()
            self.logger.info("Tenant schema created successfully")
            return True

    async def _add_tenant_columns(self) -> bool:
        """Add tenant_bid columns to existing tables"""

        tables_to_modify = [
            'user_users',
            'order_orders',
            'shifu_outlines',
            'study_records'
        ]

        with self.orchestrator.get_db_connection(self.orchestrator.target_db) as conn:
            cursor = conn.cursor()

            for table in tables_to_modify:
                # Check if column already exists
                cursor.execute(f"""
                    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_SCHEMA = DATABASE()
                    AND TABLE_NAME = '{table}'
                    AND COLUMN_NAME = 'tenant_bid'
                """)

                if cursor.fetchone()[0] == 0:
                    # Add tenant_bid column
                    alter_sql = f"""
                        ALTER TABLE {table}
                        ADD COLUMN tenant_bid VARCHAR(32) NOT NULL DEFAULT 'default'
                        AFTER {self._get_primary_bid_column(table)},
                        ADD INDEX idx_tenant_{table.split('_')[1]} (tenant_bid, {self._get_primary_bid_column(table)})
                    """
                    cursor.execute(alter_sql)
                    self.logger.info(f"Added tenant_bid column to {table}")

            conn.commit()
            return True

    def _get_primary_bid_column(self, table_name: str) -> str:
        """Get primary business ID column name for table"""
        mapping = {
            'user_users': 'user_bid',
            'order_orders': 'order_bid',
            'shifu_outlines': 'outline_bid',
            'study_records': 'record_bid'
        }
        return mapping.get(table_name, 'id')
```

## 4. Phase 2: Data Migration (Weeks 5-7)

### 4.1 Data Migration Strategy

```python
# Data Migration Service
from typing import Iterator, Tuple
import asyncio
from dataclasses import dataclass
import hashlib

@dataclass
class DataMigrationConfig:
    table_name: str
    batch_size: int = 1000
    tenant_column: str = 'tenant_bid'
    primary_key: str = 'id'
    tenant_mapping_rules: dict = None

class DataMigrator:
    def __init__(self, orchestrator: MigrationOrchestrator):
        self.orchestrator = orchestrator
        self.logger = logging.getLogger(__name__)
        self.batch_size = 1000

    async def migrate_table_data(self, config: DataMigrationConfig) -> bool:
        """Migrate data for a specific table"""

        self.logger.info(f"Starting data migration for table: {config.table_name}")

        # Get total record count
        total_records = self._get_record_count(config.table_name)
        self.logger.info(f"Total records to migrate: {total_records}")

        if total_records == 0:
            return True

        # Update progress tracking
        self._update_table_progress(config.table_name, total_records, 0)

        migrated_count = 0
        batch_number = 1

        # Process data in batches
        async for batch_data in self._get_data_batches(config):
            self.logger.info(f"Processing batch {batch_number} for {config.table_name}")

            # Apply tenant mapping rules
            processed_batch = self._apply_tenant_mapping(batch_data, config)

            # Insert batch into target database
            success = await self._insert_batch(config.table_name, processed_batch)

            if not success:
                self.logger.error(f"Failed to insert batch {batch_number}")
                return False

            migrated_count += len(processed_batch)
            self._update_table_progress(config.table_name, total_records, migrated_count)

            batch_number += 1

        # Validate migration
        if await self._validate_table_migration(config):
            self.logger.info(f"Data migration completed for {config.table_name}")
            return True
        else:
            self.logger.error(f"Data validation failed for {config.table_name}")
            return False

    async def _get_data_batches(self, config: DataMigrationConfig) -> Iterator[List[Dict]]:
        """Get data from source database in batches"""

        with self.orchestrator.get_db_connection(self.orchestrator.source_db) as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)

            offset = 0
            while True:
                sql = f"""
                    SELECT * FROM {config.table_name}
                    ORDER BY {config.primary_key}
                    LIMIT {config.batch_size} OFFSET {offset}
                """

                cursor.execute(sql)
                batch = cursor.fetchall()

                if not batch:
                    break

                yield batch
                offset += config.batch_size

    def _apply_tenant_mapping(self, batch_data: List[Dict],
                            config: DataMigrationConfig) -> List[Dict]:
        """Apply tenant mapping rules to batch data"""

        processed_batch = []

        for record in batch_data:
            # Apply tenant mapping logic
            if config.tenant_mapping_rules:
                tenant_bid = self._determine_tenant_bid(record, config.tenant_mapping_rules)
            else:
                tenant_bid = 'default'  # Default tenant for existing data

            # Add tenant_bid to record
            record[config.tenant_column] = tenant_bid
            processed_batch.append(record)

        return processed_batch

    def _determine_tenant_bid(self, record: Dict, mapping_rules: Dict) -> str:
        """Determine tenant_bid based on mapping rules"""

        # Example mapping rules:
        # {
        #     "user_email_domain": {
        #         "company1.com": "tenant_001",
        #         "company2.com": "tenant_002"
        #     },
        #     "user_organization": {
        #         "Organization A": "tenant_003"
        #     }
        # }

        for rule_type, rule_mapping in mapping_rules.items():
            if rule_type == "user_email_domain" and 'email' in record:
                domain = record['email'].split('@')[-1]
                if domain in rule_mapping:
                    return rule_mapping[domain]

            elif rule_type == "user_organization" and 'organization' in record:
                org = record.get('organization')
                if org in rule_mapping:
                    return rule_mapping[org]

        return 'default'

    async def _validate_table_migration(self, config: DataMigrationConfig) -> bool:
        """Validate that data migration was successful"""

        # Compare record counts
        source_count = self._get_record_count_from_source(config.table_name)
        target_count = self._get_record_count_from_target(config.table_name)

        if source_count != target_count:
            self.logger.error(f"Record count mismatch: source={source_count}, target={target_count}")
            return False

        # Sample validation - compare checksums of random records
        validation_sample_size = min(1000, source_count)
        return await self._validate_data_integrity(config, validation_sample_size)

    async def _validate_data_integrity(self, config: DataMigrationConfig,
                                     sample_size: int) -> bool:
        """Validate data integrity using checksums"""

        # Get random sample from source
        with self.orchestrator.get_db_connection(self.orchestrator.source_db) as source_conn:
            source_cursor = source_conn.cursor(pymysql.cursors.DictCursor)
            source_cursor.execute(f"""
                SELECT * FROM {config.table_name}
                ORDER BY RAND()
                LIMIT {sample_size}
            """)
            source_sample = source_cursor.fetchall()

        # Validate each record in target
        with self.orchestrator.get_db_connection(self.orchestrator.target_db) as target_conn:
            target_cursor = target_conn.cursor(pymysql.cursors.DictCursor)

            for source_record in source_sample:
                # Find corresponding record in target
                primary_key_value = source_record[config.primary_key]
                target_cursor.execute(f"""
                    SELECT * FROM {config.table_name}
                    WHERE {config.primary_key} = %s
                """, (primary_key_value,))

                target_record = target_cursor.fetchone()

                if not target_record:
                    self.logger.error(f"Record not found in target: {primary_key_value}")
                    return False

                # Compare relevant fields (excluding tenant_bid and timestamps)
                if not self._compare_records(source_record, target_record, config):
                    return False

        return True

    def _compare_records(self, source_record: Dict, target_record: Dict,
                        config: DataMigrationConfig) -> bool:
        """Compare source and target records for data integrity"""

        exclude_fields = {config.tenant_column, 'updated_at', 'created_at'}

        for key, source_value in source_record.items():
            if key in exclude_fields:
                continue

            target_value = target_record.get(key)

            # Handle different data types and null values
            if source_value != target_value:
                # Special handling for datetime fields that might have precision differences
                if isinstance(source_value, datetime) and isinstance(target_value, datetime):
                    if abs((source_value - target_value).total_seconds()) > 1:
                        self.logger.error(f"DateTime mismatch for {key}: {source_value} != {target_value}")
                        return False
                else:
                    self.logger.error(f"Data mismatch for {key}: {source_value} != {target_value}")
                    return False

        return True

# Phase 2 Migration Tasks
class Phase2Migration:
    def __init__(self, orchestrator: MigrationOrchestrator):
        self.orchestrator = orchestrator
        self.migrator = DataMigrator(orchestrator)
        self.logger = logging.getLogger(__name__)
        self._register_tasks()

    def _register_tasks(self):
        """Register Phase 2 migration tasks"""

        # Define migration order based on dependencies
        migration_configs = [
            DataMigrationConfig(
                table_name='user_users',
                batch_size=500,
                tenant_mapping_rules={
                    'user_email_domain': {
                        'company1.com': 'tenant_001',
                        'company2.com': 'tenant_002'
                    }
                }
            ),
            DataMigrationConfig(
                table_name='shifu_outlines',
                batch_size=100
            ),
            DataMigrationConfig(
                table_name='order_orders',
                batch_size=1000
            ),
            DataMigrationConfig(
                table_name='study_records',
                batch_size=2000
            )
        ]

        for i, config in enumerate(migration_configs):
            self.orchestrator.register_migration_task(MigrationTask(
                phase='phase2',
                name=f'Migrate {config.table_name}',
                table_name=config.table_name,
                priority=i + 1,
                depends_on=[] if i == 0 else [migration_configs[i-1].table_name],
                migration_func=lambda cfg=config: self.migrator.migrate_table_data(cfg),
                validation_func=lambda cfg=config: self.migrator._validate_table_migration(cfg)
            ))
```

## 5. Phase 3: Application Migration (Weeks 8-11)

### 5.1 Multi-Tenant Application Deployment

```yaml
# Multi-Tenant Application Configuration
apiVersion: v1
kind: ConfigMap
metadata:
  name: ai-shifu-mt-config
  namespace: ai-shifu-production
data:
  application.yml: |
    multi_tenant:
      enabled: true
      isolation_strategy: "row_level"
      default_tenant: "default"
      tenant_resolution:
        - header: "X-Tenant-ID"
        - subdomain: true
        - domain_mapping: true

    database:
      pool_size: 20
      max_overflow: 30
      tenant_aware: true

    redis:
      tenant_prefix: true
      isolation_enabled: true

    features:
      tenant_signup: true
      self_service: true
      admin_portal: true

---
# Application Deployment with Migration Support
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ai-shifu-api-mt
  namespace: ai-shifu-production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ai-shifu-api-mt
      version: multi-tenant
  template:
    metadata:
      labels:
        app: ai-shifu-api-mt
        version: multi-tenant
    spec:
      containers:
      - name: api
        image: ai-shifu-api:multi-tenant
        env:
        - name: MIGRATION_MODE
          value: "true"
        - name: MULTI_TENANT_ENABLED
          value: "true"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: database-credentials
              key: url
        - name: LEGACY_DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: legacy-database-credentials
              key: url
        ports:
        - containerPort: 5000
        livenessProbe:
          httpGet:
            path: /health
            port: 5000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 5000
          initialDelaySeconds: 5
          periodSeconds: 5
        resources:
          requests:
            cpu: 500m
            memory: 1Gi
          limits:
            cpu: 1000m
            memory: 2Gi

---
# Traffic Splitting Service (Canary Deployment)
apiVersion: v1
kind: Service
metadata:
  name: ai-shifu-api-split
  namespace: ai-shifu-production
spec:
  selector:
    app: ai-shifu-api
  ports:
  - port: 5000
    targetPort: 5000
  type: ClusterIP

---
# Istio VirtualService for Traffic Management
apiVersion: networking.istio.io/v1alpha3
kind: VirtualService
metadata:
  name: ai-shifu-api-vs
  namespace: ai-shifu-production
spec:
  hosts:
  - ai-shifu-api-split
  http:
  - match:
    - headers:
        migration-mode:
          exact: "true"
    route:
    - destination:
        host: ai-shifu-api-split
        subset: multi-tenant
      weight: 100
  - route:
    - destination:
        host: ai-shifu-api-split
        subset: legacy
      weight: 90
    - destination:
        host: ai-shifu-api-split
        subset: multi-tenant
      weight: 10

---
apiVersion: networking.istio.io/v1alpha3
kind: DestinationRule
metadata:
  name: ai-shifu-api-dr
  namespace: ai-shifu-production
spec:
  host: ai-shifu-api-split
  subsets:
  - name: legacy
    labels:
      version: legacy
  - name: multi-tenant
    labels:
      version: multi-tenant
```

### 5.2 Request Routing and Data Bridge

```python
# Migration Request Router
from flask import request, g
import logging

class MigrationRequestRouter:
    def __init__(self, app):
        self.app = app
        self.logger = logging.getLogger(__name__)
        self.migration_mode = get_config("MIGRATION_MODE", "false").lower() == "true"
        self.multi_tenant_enabled = get_config("MULTI_TENANT_ENABLED", "false").lower() == "true"

        if self.migration_mode:
            self._setup_migration_routing()

    def _setup_migration_routing(self):
        """Setup request routing for migration"""

        @self.app.before_request
        def route_request():
            # Determine routing strategy
            routing_decision = self._make_routing_decision()

            # Set routing information in request context
            g.routing_target = routing_decision['target']
            g.tenant_bid = routing_decision.get('tenant_bid')
            g.migration_mode = routing_decision.get('migration_mode', False)

            self.logger.info(f"Request routed to: {g.routing_target}")

    def _make_routing_decision(self) -> Dict[str, str]:
        """Decide where to route the request"""

        # Check for explicit migration mode header
        if request.headers.get('Migration-Mode') == 'true':
            return {
                'target': 'multi_tenant',
                'tenant_bid': self._extract_tenant_bid(),
                'migration_mode': True
            }

        # Check user agent or other routing criteria
        user_agent = request.headers.get('User-Agent', '')
        if 'MigrationClient' in user_agent:
            return {
                'target': 'multi_tenant',
                'tenant_bid': self._extract_tenant_bid(),
                'migration_mode': True
            }

        # Check if tenant is already migrated
        tenant_bid = self._extract_tenant_bid()
        if tenant_bid and self._is_tenant_migrated(tenant_bid):
            return {
                'target': 'multi_tenant',
                'tenant_bid': tenant_bid,
                'migration_mode': False
            }

        # Default to legacy system
        return {
            'target': 'legacy',
            'tenant_bid': 'default',
            'migration_mode': False
        }

    def _extract_tenant_bid(self) -> Optional[str]:
        """Extract tenant BID from request"""

        # Try header first
        tenant_from_header = request.headers.get('X-Tenant-ID')
        if tenant_from_header:
            return tenant_from_header

        # Try subdomain
        host = request.headers.get('Host', '')
        if '.' in host:
            subdomain = host.split('.')[0]
            if subdomain != 'www' and subdomain != 'api':
                # Validate subdomain is a real tenant
                if self._validate_tenant_subdomain(subdomain):
                    return self._get_tenant_by_subdomain(subdomain)

        # Try JWT token
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            tenant_from_token = self._extract_tenant_from_jwt(token)
            if tenant_from_token:
                return tenant_from_token

        return None

    def _is_tenant_migrated(self, tenant_bid: str) -> bool:
        """Check if tenant has been migrated to multi-tenant system"""

        # Query migration status from database
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT status FROM tenant_migration_status
                WHERE tenant_bid = %s
            """, (tenant_bid,))

            result = cursor.fetchone()
            return result and result[0] == 'completed'

# Data Bridge for Cross-System Operations
class MigrationDataBridge:
    def __init__(self):
        self.legacy_db = get_legacy_db_connection()
        self.target_db = get_target_db_connection()
        self.logger = logging.getLogger(__name__)

    def sync_user_data(self, user_bid: str) -> bool:
        """Sync user data between legacy and target systems"""

        try:
            # Get user data from legacy system
            legacy_user = self._get_user_from_legacy(user_bid)
            if not legacy_user:
                return False

            # Transform for multi-tenant system
            mt_user = self._transform_user_for_mt(legacy_user)

            # Upsert to target system
            self._upsert_user_to_target(mt_user)

            # Sync related data
            self._sync_user_related_data(user_bid, legacy_user['tenant_bid'])

            self.logger.info(f"Synced user data: {user_bid}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to sync user data {user_bid}: {str(e)}")
            return False

    def _sync_user_related_data(self, user_bid: str, tenant_bid: str):
        """Sync related user data (orders, study records, etc.)"""

        # Sync orders
        legacy_orders = self._get_user_orders_from_legacy(user_bid)
        for order in legacy_orders:
            mt_order = self._transform_order_for_mt(order, tenant_bid)
            self._upsert_order_to_target(mt_order)

        # Sync study records
        legacy_records = self._get_user_study_records_from_legacy(user_bid)
        for record in legacy_records:
            mt_record = self._transform_study_record_for_mt(record, tenant_bid)
            self._upsert_study_record_to_target(mt_record)

    def write_through_sync(self, operation: str, table: str, data: Dict) -> bool:
        """Write-through sync for real-time data consistency"""

        try:
            # Write to target system first
            success = self._write_to_target(operation, table, data)
            if not success:
                return False

            # Write to legacy system for consistency
            legacy_data = self._transform_data_for_legacy(data)
            self._write_to_legacy(operation, table, legacy_data)

            return True

        except Exception as e:
            self.logger.error(f"Write-through sync failed: {str(e)}")
            return False
```

## 6. Phase 4: Integration Migration (Weeks 12-14)

### 6.1 OAuth Integration Deployment

```yaml
# OAuth Service Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ai-shifu-oauth
  namespace: ai-shifu-production
spec:
  replicas: 2
  selector:
    matchLabels:
      app: ai-shifu-oauth
  template:
    metadata:
      labels:
        app: ai-shifu-oauth
    spec:
      containers:
      - name: oauth-service
        image: ai-shifu-oauth:latest
        env:
        - name: OAUTH_PROVIDERS_CONFIG
          valueFrom:
            configMapKeyRef:
              name: oauth-config
              key: providers.json
        - name: TENANT_MAPPING_CONFIG
          valueFrom:
            configMapKeyRef:
              name: oauth-config
              key: tenant-mapping.json
        ports:
        - containerPort: 8080
        resources:
          requests:
            cpu: 200m
            memory: 512Mi
          limits:
            cpu: 500m
            memory: 1Gi

---
# Billing Service Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ai-shifu-billing
  namespace: ai-shifu-production
spec:
  replicas: 2
  selector:
    matchLabels:
      app: ai-shifu-billing
  template:
    metadata:
      labels:
        app: ai-shifu-billing
    spec:
      containers:
      - name: billing-service
        image: ai-shifu-billing:latest
        env:
        - name: STRIPE_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: stripe-credentials
              key: secret-key
        - name: WEBHOOK_SECRET
          valueFrom:
            secretKeyRef:
              name: stripe-credentials
              key: webhook-secret
        ports:
        - containerPort: 8081
        resources:
          requests:
            cpu: 300m
            memory: 512Mi
          limits:
            cpu: 600m
            memory: 1Gi
```

### 6.2 Integration Migration Scripts

```python
# Integration Migration Service
class IntegrationMigrator:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def migrate_oauth_configurations(self) -> bool:
        """Migrate OAuth configurations to multi-tenant setup"""

        # Read existing OAuth configurations
        legacy_oauth_configs = self._read_legacy_oauth_configs()

        for config in legacy_oauth_configs:
            # Create tenant-specific OAuth app
            tenant_bid = self._determine_tenant_for_oauth_config(config)

            mt_config = self._transform_oauth_config_for_mt(config, tenant_bid)

            # Register with OAuth service
            await self._register_oauth_config(mt_config)

            self.logger.info(f"Migrated OAuth config for tenant: {tenant_bid}")

        return True

    async def migrate_billing_configurations(self) -> bool:
        """Migrate billing configurations"""

        # Create default subscription plans
        default_plans = self._create_default_subscription_plans()

        for plan in default_plans:
            await self._create_subscription_plan(plan)

        # Migrate existing payment methods and subscriptions
        legacy_payments = self._get_legacy_payment_data()

        for payment_data in legacy_payments:
            tenant_bid = self._determine_tenant_for_payment(payment_data)

            mt_payment = self._transform_payment_for_mt(payment_data, tenant_bid)
            await self._migrate_payment_data(mt_payment)

        return True
```

## 7. Phase 5: Go-Live and Cleanup (Weeks 15-16)

### 7.1 Final Migration and Cutover

```python
# Final Migration Orchestrator
class FinalMigrationOrchestrator:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def execute_final_migration(self) -> bool:
        """Execute final migration and cutover"""

        # 1. Final data sync
        self.logger.info("Starting final data synchronization")
        await self._final_data_sync()

        # 2. Switch traffic to multi-tenant system
        self.logger.info("Switching traffic to multi-tenant system")
        await self._switch_traffic()

        # 3. Verify system health
        self.logger.info("Verifying system health")
        health_check_passed = await self._verify_system_health()

        if not health_check_passed:
            self.logger.error("Health check failed, initiating rollback")
            await self._rollback_traffic()
            return False

        # 4. Clean up legacy resources
        self.logger.info("Cleaning up legacy resources")
        await self._cleanup_legacy_resources()

        self.logger.info("Final migration completed successfully")
        return True

    async def _final_data_sync(self):
        """Perform final incremental data sync"""

        # Get all data modified since last sync
        last_sync_time = self._get_last_sync_timestamp()

        # Sync all tables
        tables_to_sync = [
            'user_users',
            'order_orders',
            'study_records',
            'shifu_outlines'
        ]

        for table in tables_to_sync:
            await self._sync_incremental_data(table, last_sync_time)

    async def _switch_traffic(self):
        """Switch traffic from legacy to multi-tenant system"""

        # Update Istio traffic routing
        routing_config = {
            "legacy_weight": 0,
            "multi_tenant_weight": 100
        }

        await self._update_traffic_routing(routing_config)

    async def _verify_system_health(self) -> bool:
        """Comprehensive system health verification"""

        health_checks = [
            self._check_api_health,
            self._check_database_health,
            self._check_oauth_integration,
            self._check_billing_integration,
            self._check_tenant_isolation,
            self._run_smoke_tests
        ]

        for health_check in health_checks:
            if not await health_check():
                return False

        return True

    async def _cleanup_legacy_resources(self):
        """Clean up legacy system resources"""

        # Archive legacy database
        await self._archive_legacy_database()

        # Remove legacy deployments
        await self._remove_legacy_deployments()

        # Update DNS records
        await self._update_dns_records()

        # Clean up temporary migration resources
        await self._cleanup_migration_resources()

# Migration Completion Verification
class MigrationVerifier:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def verify_migration_completion(self) -> Dict[str, bool]:
        """Comprehensive migration verification"""

        verification_results = {}

        # Data integrity verification
        verification_results['data_integrity'] = await self._verify_data_integrity()

        # Functional verification
        verification_results['api_functionality'] = await self._verify_api_functionality()

        # Performance verification
        verification_results['performance'] = await self._verify_performance()

        # Security verification
        verification_results['security'] = await self._verify_security()

        # Tenant isolation verification
        verification_results['tenant_isolation'] = await self._verify_tenant_isolation()

        return verification_results

    async def _verify_data_integrity(self) -> bool:
        """Verify data integrity across all tenants"""

        # Compare record counts between legacy and target
        integrity_checks = [
            ('user_users', 'Users'),
            ('order_orders', 'Orders'),
            ('study_records', 'Study Records'),
            ('shifu_outlines', 'Shifu Outlines')
        ]

        for table, description in integrity_checks:
            legacy_count = self._get_legacy_record_count(table)
            target_count = self._get_target_record_count(table)

            if legacy_count != target_count:
                self.logger.error(f"{description} count mismatch: legacy={legacy_count}, target={target_count}")
                return False

        self.logger.info("Data integrity verification passed")
        return True
```

## 8. Risk Management and Rollback Strategy

### 8.1 Risk Assessment Matrix

| Risk Category | Risk | Probability | Impact | Mitigation Strategy |
|---------------|------|------------|---------|-------------------|
| Data Loss | Database corruption during migration | Low | Critical | Real-time backups, point-in-time recovery |
| Performance | System slowdown during migration | Medium | High | Load testing, traffic throttling |
| Security | Authentication bypass in multi-tenant system | Low | Critical | Comprehensive security testing |
| Integration | Third-party service failures | Medium | Medium | Circuit breakers, fallback mechanisms |
| User Experience | Service interruption | Low | High | Zero-downtime deployment strategy |

### 8.2 Rollback Procedures

```python
# Rollback Service
class MigrationRollback:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def execute_rollback(self, rollback_to_phase: str) -> bool:
        """Execute rollback to specific phase"""

        self.logger.warning(f"Initiating rollback to phase: {rollback_to_phase}")

        rollback_procedures = {
            'phase5': self._rollback_from_golive,
            'phase4': self._rollback_from_integration,
            'phase3': self._rollback_from_application,
            'phase2': self._rollback_from_data_migration,
            'phase1': self._rollback_from_foundation
        }

        procedure = rollback_procedures.get(rollback_to_phase)
        if not procedure:
            self.logger.error(f"No rollback procedure for phase: {rollback_to_phase}")
            return False

        return await procedure()

    async def _rollback_from_golive(self) -> bool:
        """Rollback from go-live phase"""

        # Switch traffic back to legacy system
        await self._switch_traffic_to_legacy()

        # Restore legacy deployments if needed
        await self._restore_legacy_deployments()

        # Verify legacy system health
        return await self._verify_legacy_system_health()
```

## 9. Success Criteria and Validation

### 9.1 Technical Success Criteria

- ✅ Zero data loss during migration
- ✅ 99.9% uptime maintained throughout migration
- ✅ Multi-tenant isolation verified
- ✅ All integrations functional
- ✅ Performance meets or exceeds baseline
- ✅ Security controls validated

### 9.2 Business Success Criteria

- ✅ All existing users can access their data
- ✅ New tenant onboarding functional
- ✅ Billing and subscription management operational
- ✅ Support team trained on multi-tenant operations
- ✅ Monitoring and alerting comprehensive

## 10. Post-Migration Activities

### 10.1 Optimization and Monitoring

```python
# Post-Migration Optimization
class PostMigrationOptimizer:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def optimize_system_performance(self):
        """Optimize system performance post-migration"""

        # Database query optimization
        await self._optimize_database_queries()

        # Cache optimization
        await self._optimize_caching_strategy()

        # Resource allocation optimization
        await self._optimize_resource_allocation()

    async def generate_migration_report(self) -> Dict:
        """Generate comprehensive migration report"""

        return {
            'migration_duration': self._calculate_migration_duration(),
            'data_migrated': self._get_data_migration_stats(),
            'performance_metrics': self._get_performance_metrics(),
            'issues_encountered': self._get_migration_issues(),
            'lessons_learned': self._get_lessons_learned(),
            'recommendations': self._get_recommendations()
        }
```

## 11. Implementation Timeline Summary

| Week | Phase | Key Activities | Deliverables |
|------|-------|----------------|--------------|
| 1-4 | Foundation | Infrastructure setup, schema changes | Multi-tenant schema, migration tools |
| 5-7 | Data Migration | Data transfer and validation | Migrated datasets, validation reports |
| 8-11 | Application | Multi-tenant application deployment | MT application, traffic routing |
| 12-14 | Integration | OAuth, billing, monitoring setup | Integrated services, monitoring |
| 15-16 | Go-Live | Final cutover and cleanup | Production system, migration report |

This comprehensive migration plan ensures a systematic, risk-managed transformation of AI-Shifu into a scalable SaaS platform while maintaining service continuity and data integrity throughout the process.
