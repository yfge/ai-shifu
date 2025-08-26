# AI-Shifu SaaS Security Architecture Design

## Overview

This document outlines the comprehensive security architecture for the AI-Shifu SaaS platform, covering authentication, authorization, data protection, network security, compliance, and threat detection.

## 1. Security Framework

### 1.1 Security Principles

```
Defense in Depth
- Multiple layers of security controls
- Fail-secure mechanisms
- Zero-trust architecture

Principle of Least Privilege
- Minimal necessary access rights
- Role-based access control
- Just-in-time access

Data Protection by Design
- Encryption at rest and in transit
- Data minimization
- Privacy by default
```

### 1.2 Security Architecture Layers

```
┌─────────────────────────────────────┐
│           User Interface            │
│    (WAF, Rate Limiting, CSRF)       │
├─────────────────────────────────────┤
│        Application Layer            │
│  (Authentication, Authorization)    │
├─────────────────────────────────────┤
│         Service Layer               │
│   (Service Mesh, mTLS, JWT)         │
├─────────────────────────────────────┤
│        Infrastructure Layer         │
│  (Network Policies, Encryption)     │
├─────────────────────────────────────┤
│          Data Layer                 │
│ (Database Security, Backups)        │
└─────────────────────────────────────┘
```

## 2. Authentication & Authorization

### 2.1 Multi-Factor Authentication (MFA)

```sql
-- MFA Configuration Table
CREATE TABLE auth_mfa_configs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    config_bid VARCHAR(32) NOT NULL UNIQUE INDEX,
    user_bid VARCHAR(32) NOT NULL INDEX,
    tenant_bid VARCHAR(32) NOT NULL INDEX,
    mfa_type SMALLINT NOT NULL DEFAULT 0 COMMENT '0=TOTP, 1=SMS, 2=Email, 3=Hardware',
    secret_encrypted TEXT COMMENT 'Encrypted MFA secret',
    backup_codes JSON COMMENT 'Encrypted backup codes',
    is_verified TINYINT NOT NULL DEFAULT 0,
    last_used_at DATETIME,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted TINYINT NOT NULL DEFAULT 0 INDEX,
    INDEX idx_user_tenant (user_bid, tenant_bid)
);

-- MFA Authentication Attempts
CREATE TABLE auth_mfa_attempts (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    attempt_bid VARCHAR(32) NOT NULL UNIQUE INDEX,
    user_bid VARCHAR(32) NOT NULL INDEX,
    tenant_bid VARCHAR(32) NOT NULL INDEX,
    attempt_type SMALLINT NOT NULL COMMENT '0=TOTP, 1=SMS, 2=Email, 3=Backup',
    success TINYINT NOT NULL DEFAULT 0,
    ip_address VARCHAR(45),
    user_agent TEXT,
    attempted_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_time (user_bid, attempted_at),
    INDEX idx_tenant_time (tenant_bid, attempted_at)
);
```

### 2.2 Role-Based Access Control (RBAC)

```sql
-- Security Roles
CREATE TABLE auth_roles (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    role_bid VARCHAR(32) NOT NULL UNIQUE INDEX,
    tenant_bid VARCHAR(32) NOT NULL INDEX,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    is_system_role TINYINT NOT NULL DEFAULT 0 COMMENT 'System roles cannot be deleted',
    permissions JSON COMMENT 'Aggregated permissions for caching',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted TINYINT NOT NULL DEFAULT 0 INDEX,
    UNIQUE KEY uk_tenant_name (tenant_bid, name, deleted)
);

-- Permissions
CREATE TABLE auth_permissions (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    permission_bid VARCHAR(32) NOT NULL UNIQUE INDEX,
    resource VARCHAR(50) NOT NULL COMMENT 'Resource type (users, shifus, orders)',
    action VARCHAR(50) NOT NULL COMMENT 'Action (read, write, delete, admin)',
    scope VARCHAR(50) DEFAULT 'tenant' COMMENT 'tenant, global, own',
    description TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_resource_action_scope (resource, action, scope)
);

-- Role-Permission Mapping
CREATE TABLE auth_role_permissions (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    role_bid VARCHAR(32) NOT NULL INDEX,
    permission_bid VARCHAR(32) NOT NULL INDEX,
    granted_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    granted_by_user_bid VARCHAR(32) NOT NULL,
    UNIQUE KEY uk_role_permission (role_bid, permission_bid)
);
```

### 2.3 JWT Security Implementation

```python
# JWT Security Service
import jwt
import redis
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from flaskr.common.config import get_config

class JWTSecurityService:
    def __init__(self):
        self.redis_client = redis.Redis.from_url(get_config("REDIS_URL"))
        self.secret_key = get_config("JWT_SECRET_KEY")
        self.algorithm = "HS256"
        self.access_token_expire = timedelta(hours=1)
        self.refresh_token_expire = timedelta(days=7)
        self.cipher_suite = Fernet(get_config("ENCRYPTION_KEY").encode())

    def generate_access_token(self, user_bid: str, tenant_bid: str,
                            permissions: list) -> str:
        """Generate secure access token with permissions"""
        payload = {
            "user_bid": user_bid,
            "tenant_bid": tenant_bid,
            "permissions": permissions,
            "type": "access",
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + self.access_token_expire,
            "jti": self._generate_jti()
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def generate_refresh_token(self, user_bid: str, tenant_bid: str) -> str:
        """Generate secure refresh token"""
        payload = {
            "user_bid": user_bid,
            "tenant_bid": tenant_bid,
            "type": "refresh",
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + self.refresh_token_expire,
            "jti": self._generate_jti()
        }
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

        # Store refresh token in Redis for revocation capability
        self.redis_client.setex(
            f"refresh_token:{payload['jti']}",
            self.refresh_token_expire,
            f"{user_bid}:{tenant_bid}"
        )
        return token

    def validate_token(self, token: str) -> dict:
        """Validate and decode JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])

            # Check if token is blacklisted
            if self.is_token_blacklisted(payload.get("jti")):
                raise jwt.InvalidTokenError("Token is blacklisted")

            return payload
        except jwt.ExpiredSignatureError:
            raise jwt.InvalidTokenError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise e

    def blacklist_token(self, jti: str, exp: datetime):
        """Add token to blacklist"""
        remaining_time = exp - datetime.utcnow()
        if remaining_time.total_seconds() > 0:
            self.redis_client.setex(
                f"blacklist:{jti}",
                remaining_time,
                "blacklisted"
            )

    def is_token_blacklisted(self, jti: str) -> bool:
        """Check if token is blacklisted"""
        return self.redis_client.exists(f"blacklist:{jti}")

    def _generate_jti(self) -> str:
        """Generate unique token identifier"""
        import uuid
        return str(uuid.uuid4())
```

## 3. Data Protection

### 3.1 Encryption at Rest

```python
# Data Encryption Service
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os

class DataEncryptionService:
    def __init__(self, master_key: str):
        self.master_key = master_key.encode()
        self._cipher_cache = {}

    def get_tenant_cipher(self, tenant_bid: str) -> Fernet:
        """Get or create tenant-specific encryption cipher"""
        if tenant_bid not in self._cipher_cache:
            # Derive tenant-specific key from master key
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=tenant_bid.encode(),
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(self.master_key))
            self._cipher_cache[tenant_bid] = Fernet(key)

        return self._cipher_cache[tenant_bid]

    def encrypt_sensitive_data(self, data: str, tenant_bid: str) -> str:
        """Encrypt sensitive data with tenant-specific key"""
        cipher = self.get_tenant_cipher(tenant_bid)
        return cipher.encrypt(data.encode()).decode()

    def decrypt_sensitive_data(self, encrypted_data: str, tenant_bid: str) -> str:
        """Decrypt sensitive data with tenant-specific key"""
        cipher = self.get_tenant_cipher(tenant_bid)
        return cipher.decrypt(encrypted_data.encode()).decode()
```

### 3.2 Database Security Configuration

```sql
-- Database Security Settings
-- Enable SSL/TLS for connections
SET GLOBAL require_secure_transport = ON;

-- Create security-focused database user
CREATE USER 'ai_shifu_app'@'%'
IDENTIFIED BY 'strong_random_password'
REQUIRE SSL;

-- Grant minimal necessary privileges
GRANT SELECT, INSERT, UPDATE, DELETE ON ai_shifu.* TO 'ai_shifu_app'@'%';
GRANT EXECUTE ON PROCEDURE ai_shifu.* TO 'ai_shifu_app'@'%';

-- Enable audit logging
SET GLOBAL general_log = 'ON';
SET GLOBAL log_queries_not_using_indexes = 'ON';

-- Configure row-level security
CREATE TABLE sensitive_data (
    id BIGINT PRIMARY KEY,
    tenant_bid VARCHAR(32) NOT NULL,
    data_encrypted TEXT,
    INDEX idx_tenant_security (tenant_bid)
) ROW_FORMAT=ENCRYPTED;
```

## 4. Network Security

### 4.1 Kubernetes Network Policies

```yaml
# Default Deny Network Policy
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: ai-shifu
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress

---
# API Server Network Policy
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-server-policy
  namespace: ai-shifu
spec:
  podSelector:
    matchLabels:
      app: api-server
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: nginx-ingress
    ports:
    - protocol: TCP
      port: 5000
  - from:
    - podSelector:
        matchLabels:
          app: web-frontend
    ports:
    - protocol: TCP
      port: 5000
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: mysql
    ports:
    - protocol: TCP
      port: 3306
  - to:
    - podSelector:
        matchLabels:
          app: redis
    ports:
    - protocol: TCP
      port: 6379

---
# Database Network Policy
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: database-policy
  namespace: ai-shifu
spec:
  podSelector:
    matchLabels:
      app: mysql
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: api-server
    ports:
    - protocol: TCP
      port: 3306
```

### 4.2 Service Mesh Security (Istio)

```yaml
# Mutual TLS Policy
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
  namespace: ai-shifu
spec:
  mtls:
    mode: STRICT

---
# Authorization Policy for API
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: api-access-policy
  namespace: ai-shifu
spec:
  selector:
    matchLabels:
      app: api-server
  rules:
  - from:
    - source:
        principals: ["cluster.local/ns/ai-shifu/sa/web-frontend"]
    to:
    - operation:
        methods: ["GET", "POST", "PUT", "DELETE"]
        paths: ["/api/*"]
    when:
    - key: request.headers[authorization]
      values: ["Bearer *"]

---
# Rate Limiting Policy
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: rate-limit-filter
  namespace: ai-shifu
spec:
  configPatches:
  - applyTo: HTTP_FILTER
    match:
      context: SIDECAR_INBOUND
      listener:
        filterChain:
          filter:
            name: "envoy.filters.network.http_connection_manager"
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.filters.http.local_ratelimit
        typed_config:
          "@type": type.googleapis.com/udpa.type.v1.TypedStruct
          type_url: type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit
          value:
            stat_prefix: rate_limiter
            token_bucket:
              max_tokens: 100
              tokens_per_fill: 100
              fill_interval: 60s
```

## 5. Web Application Security

### 5.1 Web Application Firewall (WAF)

```yaml
# ModSecurity WAF Configuration
apiVersion: v1
kind: ConfigMap
metadata:
  name: modsecurity-config
  namespace: nginx-ingress
data:
  modsecurity.conf: |
    Include /etc/nginx/modsecurity/unicode.mapping
    Include /etc/nginx/modsecurity/owasp-modsecurity-crs/crs-setup.conf
    Include /etc/nginx/modsecurity/owasp-modsecurity-crs/rules/*.conf

    # Enable ModSecurity
    SecRuleEngine On

    # Request body handling
    SecRequestBodyAccess On
    SecRequestBodyLimit 13107200
    SecRequestBodyNoFilesLimit 131072

    # Response body handling
    SecResponseBodyAccess On
    SecResponseBodyMimeType text/plain text/html text/xml
    SecResponseBodyLimit 524288
    SecResponseBodyLimitAction Reject

    # Filesystem configuration
    SecTmpDir /tmp/
    SecDataDir /tmp/

    # Debug log
    SecDebugLog /var/log/nginx/modsec_debug.log
    SecDebugLogLevel 0

    # Audit log
    SecAuditEngine RelevantOnly
    SecAuditLogRelevantStatus "^(?:5|4(?!04))"
    SecAuditLogParts ABIJDEFHZ
    SecAuditLogType Serial
    SecAuditLog /var/log/nginx/modsec_audit.log

    # Custom rules for AI-Shifu
    SecRule ARGS "@detectSQLi" \
        "id:1001,\
         phase:2,\
         block,\
         msg:'SQL Injection Attack Detected',\
         logdata:'Matched Data: %{MATCHED_VAR} found within %{MATCHED_VAR_NAME}',\
         tag:'attack-sqli',\
         ctl:auditLogParts=+E,\
         ver:'OWASP_CRS/3.3.0',\
         severity:'CRITICAL',\
         setvar:'tx.anomaly_score_pl1=+%{tx.critical_anomaly_score}'"

---
# NGINX Ingress with WAF
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ai-shifu-ingress
  namespace: ai-shifu
  annotations:
    nginx.ingress.kubernetes.io/enable-modsecurity: "true"
    nginx.ingress.kubernetes.io/modsecurity-snippet: |
      SecRuleEngine On
      SecAuditEngine On
    nginx.ingress.kubernetes.io/rate-limit: "100"
    nginx.ingress.kubernetes.io/rate-limit-window: "1m"
spec:
  tls:
  - hosts:
    - api.ai-shifu.com
    secretName: ai-shifu-tls
  rules:
  - host: api.ai-shifu.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: api-server
            port:
              number: 5000
```

### 5.2 Content Security Policy (CSP)

```python
# CSP Configuration
from flask import Flask
from flask_talisman import Talisman

def configure_security_headers(app: Flask):
    """Configure security headers including CSP"""

    csp = {
        'default-src': "'self'",
        'script-src': [
            "'self'",
            "'unsafe-inline'",  # Required for React
            "https://cdnjs.cloudflare.com",
            "https://cdn.jsdelivr.net"
        ],
        'style-src': [
            "'self'",
            "'unsafe-inline'",
            "https://fonts.googleapis.com"
        ],
        'font-src': [
            "'self'",
            "https://fonts.gstatic.com"
        ],
        'img-src': [
            "'self'",
            "data:",
            "https://*.amazonaws.com",
            "https://*.cloudfront.net"
        ],
        'connect-src': [
            "'self'",
            "https://api.openai.com",
            "https://api.stripe.com"
        ],
        'frame-ancestors': "'none'",
        'base-uri': "'self'",
        'object-src': "'none'"
    }

    Talisman(
        app,
        force_https=True,
        strict_transport_security=True,
        strict_transport_security_max_age=31536000,
        content_security_policy=csp,
        referrer_policy='strict-origin-when-cross-origin',
        feature_policy={
            'geolocation': "'none'",
            'camera': "'none'",
            'microphone': "'none'"
        }
    )
```

## 6. Security Monitoring & Incident Response

### 6.1 Security Event Logging

```sql
-- Security Events Table
CREATE TABLE security_events (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    event_bid VARCHAR(32) NOT NULL UNIQUE INDEX,
    tenant_bid VARCHAR(32) INDEX,
    user_bid VARCHAR(32) INDEX,
    event_type VARCHAR(50) NOT NULL INDEX COMMENT 'login, logout, permission_denied, data_access, etc.',
    severity SMALLINT NOT NULL DEFAULT 0 COMMENT '0=info, 1=warning, 2=error, 3=critical',
    source_ip VARCHAR(45),
    user_agent TEXT,
    resource VARCHAR(100) COMMENT 'Resource being accessed',
    action VARCHAR(50) COMMENT 'Action attempted',
    result VARCHAR(20) NOT NULL COMMENT 'success, failure, blocked',
    details JSON COMMENT 'Additional event details',
    risk_score SMALLINT DEFAULT 0 COMMENT '0-100 risk assessment',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_tenant_time (tenant_bid, created_at),
    INDEX idx_user_time (user_bid, created_at),
    INDEX idx_type_time (event_type, created_at),
    INDEX idx_severity_time (severity, created_at)
);

-- Threat Intelligence
CREATE TABLE security_threat_indicators (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    indicator_bid VARCHAR(32) NOT NULL UNIQUE INDEX,
    indicator_type VARCHAR(20) NOT NULL COMMENT 'ip, domain, hash, pattern',
    indicator_value VARCHAR(255) NOT NULL INDEX,
    threat_type VARCHAR(50) NOT NULL COMMENT 'malware, phishing, brute_force, etc.',
    severity SMALLINT NOT NULL DEFAULT 0,
    source VARCHAR(100) COMMENT 'Source of threat intelligence',
    confidence SMALLINT NOT NULL DEFAULT 50 COMMENT '0-100 confidence level',
    first_seen DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    expires_at DATETIME,
    active TINYINT NOT NULL DEFAULT 1 INDEX,
    INDEX idx_type_value (indicator_type, indicator_value),
    INDEX idx_active_expires (active, expires_at)
);
```

### 6.2 Real-time Security Monitoring

```python
# Security Monitoring Service
import redis
import json
from datetime import datetime, timedelta
from collections import defaultdict
from flaskr.service.notification.service import NotificationService

class SecurityMonitoringService:
    def __init__(self):
        self.redis_client = redis.Redis.from_url(get_config("REDIS_URL"))
        self.notification_service = NotificationService()
        self.alert_thresholds = {
            "failed_login_attempts": 5,
            "permission_denied_events": 10,
            "suspicious_ip_requests": 100,
            "data_access_anomaly": 50
        }

    def log_security_event(self, tenant_bid: str, user_bid: str,
                          event_type: str, details: dict):
        """Log security event and trigger alerts if needed"""

        event = {
            "tenant_bid": tenant_bid,
            "user_bid": user_bid,
            "event_type": event_type,
            "details": details,
            "timestamp": datetime.utcnow().isoformat(),
            "source_ip": details.get("source_ip"),
            "risk_score": self._calculate_risk_score(event_type, details)
        }

        # Store in database
        self._store_security_event(event)

        # Real-time analysis
        self._analyze_event_patterns(event)

        # Check for immediate threats
        if event["risk_score"] >= 80:
            self._trigger_security_alert(event)

    def _analyze_event_patterns(self, event: dict):
        """Analyze event patterns for anomaly detection"""

        # Failed login analysis
        if event["event_type"] == "login_failed":
            key = f"failed_logins:{event['source_ip']}"
            count = self.redis_client.incr(key)
            self.redis_client.expire(key, 3600)  # 1 hour window

            if count >= self.alert_thresholds["failed_login_attempts"]:
                self._trigger_brute_force_alert(event)

        # Permission denied analysis
        elif event["event_type"] == "permission_denied":
            key = f"permission_denied:{event['user_bid']}"
            count = self.redis_client.incr(key)
            self.redis_client.expire(key, 3600)

            if count >= self.alert_thresholds["permission_denied_events"]:
                self._trigger_privilege_escalation_alert(event)

        # Suspicious IP analysis
        self._analyze_ip_behavior(event)

    def _analyze_ip_behavior(self, event: dict):
        """Analyze IP address behavior patterns"""
        source_ip = event.get("source_ip")
        if not source_ip:
            return

        # Check against threat intelligence
        if self._is_malicious_ip(source_ip):
            event["risk_score"] = 100
            self._trigger_security_alert(event)

        # Geographic anomaly detection
        if self._detect_geographic_anomaly(source_ip, event["user_bid"]):
            event["risk_score"] += 30

        # Request volume analysis
        key = f"ip_requests:{source_ip}"
        count = self.redis_client.incr(key)
        self.redis_client.expire(key, 3600)

        if count >= self.alert_thresholds["suspicious_ip_requests"]:
            self._trigger_ddos_alert(event)

    def _calculate_risk_score(self, event_type: str, details: dict) -> int:
        """Calculate risk score for security event"""
        base_scores = {
            "login_failed": 20,
            "login_success": 5,
            "permission_denied": 40,
            "data_access": 10,
            "admin_action": 30,
            "password_change": 25,
            "mfa_disabled": 80,
            "bulk_data_export": 70
        }

        score = base_scores.get(event_type, 10)

        # Adjust based on context
        if details.get("from_suspicious_ip"):
            score += 50
        if details.get("unusual_time"):
            score += 20
        if details.get("new_device"):
            score += 15

        return min(score, 100)

    def _trigger_security_alert(self, event: dict):
        """Trigger security alert for high-risk events"""
        alert = {
            "type": "security_alert",
            "severity": "critical" if event["risk_score"] >= 90 else "warning",
            "event": event,
            "timestamp": datetime.utcnow().isoformat(),
            "auto_response": self._determine_auto_response(event)
        }

        # Send alert to security team
        self.notification_service.send_security_alert(alert)

        # Trigger automated response if configured
        if alert["auto_response"]:
            self._execute_auto_response(event, alert["auto_response"])

    def _execute_auto_response(self, event: dict, response: str):
        """Execute automated security response"""
        if response == "block_ip":
            self._block_ip_address(event.get("source_ip"))
        elif response == "disable_user":
            self._disable_user_account(event["user_bid"])
        elif response == "require_mfa":
            self._require_mfa_verification(event["user_bid"])
```

## 7. Compliance & Audit

### 7.1 GDPR Compliance

```python
# GDPR Compliance Service
from datetime import datetime, timedelta

class GDPRComplianceService:
    def __init__(self):
        self.data_retention_policies = {
            "user_activity_logs": timedelta(days=365),
            "security_events": timedelta(days=1095),  # 3 years
            "audit_logs": timedelta(days=2555),  # 7 years
            "personal_data": None,  # Indefinite until deletion request
        }

    def handle_data_subject_request(self, request_type: str, user_bid: str,
                                  tenant_bid: str) -> dict:
        """Handle GDPR data subject requests"""

        if request_type == "access":
            return self._generate_data_export(user_bid, tenant_bid)
        elif request_type == "deletion":
            return self._process_deletion_request(user_bid, tenant_bid)
        elif request_type == "rectification":
            return self._process_rectification_request(user_bid, tenant_bid)
        elif request_type == "portability":
            return self._generate_portable_data(user_bid, tenant_bid)

    def _generate_data_export(self, user_bid: str, tenant_bid: str) -> dict:
        """Generate complete data export for user"""

        export_data = {
            "user_profile": self._export_user_profile(user_bid),
            "study_records": self._export_study_records(user_bid),
            "orders": self._export_orders(user_bid),
            "activity_logs": self._export_activity_logs(user_bid),
            "generated_at": datetime.utcnow().isoformat(),
            "export_format": "json"
        }

        # Log data access request
        self._log_gdpr_activity("data_export", user_bid, tenant_bid)

        return export_data

    def _process_deletion_request(self, user_bid: str, tenant_bid: str) -> dict:
        """Process right to be forgotten request"""

        deletion_plan = {
            "immediate_deletion": [
                "user_profiles",
                "user_preferences",
                "personal_messages"
            ],
            "anonymization": [
                "study_records",
                "order_history",
                "activity_logs"
            ],
            "retention_required": [
                "financial_records",  # Legal requirement
                "security_incidents"  # Security requirement
            ]
        }

        # Execute deletion/anonymization
        results = {}
        for category, tables in deletion_plan.items():
            results[category] = self._execute_deletion_category(
                category, tables, user_bid, tenant_bid
            )

        # Log deletion request
        self._log_gdpr_activity("data_deletion", user_bid, tenant_bid)

        return {
            "status": "completed",
            "deletion_results": results,
            "processed_at": datetime.utcnow().isoformat()
        }
```

### 7.2 Audit Logging

```sql
-- Comprehensive Audit Log
CREATE TABLE audit_logs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    audit_bid VARCHAR(32) NOT NULL UNIQUE INDEX,
    tenant_bid VARCHAR(32) NOT NULL INDEX,
    user_bid VARCHAR(32) INDEX,
    session_bid VARCHAR(32) INDEX,
    action VARCHAR(100) NOT NULL COMMENT 'Action performed',
    resource_type VARCHAR(50) COMMENT 'Type of resource affected',
    resource_bid VARCHAR(32) INDEX COMMENT 'Specific resource identifier',
    old_values JSON COMMENT 'Previous values (for updates)',
    new_values JSON COMMENT 'New values (for creates/updates)',
    ip_address VARCHAR(45),
    user_agent TEXT,
    request_id VARCHAR(36) INDEX,
    api_endpoint VARCHAR(200),
    http_method VARCHAR(10),
    response_status SMALLINT,
    processing_time_ms INT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_tenant_time (tenant_bid, created_at),
    INDEX idx_user_time (user_bid, created_at),
    INDEX idx_resource (resource_type, resource_bid),
    INDEX idx_action_time (action, created_at)
);

-- Audit Configuration
CREATE TABLE audit_config (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    config_bid VARCHAR(32) NOT NULL UNIQUE INDEX,
    tenant_bid VARCHAR(32) NOT NULL INDEX,
    resource_type VARCHAR(50) NOT NULL,
    actions JSON NOT NULL COMMENT 'Actions to audit for this resource',
    enabled TINYINT NOT NULL DEFAULT 1,
    retention_days INT NOT NULL DEFAULT 2555 COMMENT '7 years default',
    include_old_values TINYINT NOT NULL DEFAULT 1,
    include_new_values TINYINT NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_tenant_resource (tenant_bid, resource_type)
);
```

## 8. Security Testing & Validation

### 8.1 Automated Security Testing

```python
# Security Test Suite
import pytest
import requests
from unittest.mock import patch

class TestSecurityControls:

    def test_sql_injection_protection(self, api_client):
        """Test SQL injection protection"""
        malicious_payloads = [
            "'; DROP TABLE users; --",
            "' UNION SELECT * FROM users --",
            "1' OR '1'='1",
            "'; EXEC sp_configure 'show advanced options', 1--"
        ]

        for payload in malicious_payloads:
            response = api_client.get(f"/api/users?search={payload}")
            assert response.status_code != 500  # Should not cause server error
            assert "error" not in response.json().get("message", "").lower()

    def test_xss_protection(self, api_client):
        """Test Cross-Site Scripting protection"""
        xss_payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "';alert(String.fromCharCode(88,83,83))//'"
        ]

        for payload in xss_payloads:
            response = api_client.post("/api/users", json={
                "name": payload,
                "email": "test@example.com"
            })
            # Response should escape or reject the payload
            assert payload not in str(response.json())

    def test_authentication_bypass_attempts(self, api_client):
        """Test authentication bypass protection"""
        protected_endpoints = [
            "/api/users/profile",
            "/api/admin/settings",
            "/api/tenants/create"
        ]

        for endpoint in protected_endpoints:
            # Test without token
            response = api_client.get(endpoint)
            assert response.status_code == 401

            # Test with invalid token
            response = api_client.get(endpoint, headers={
                "Authorization": "Bearer invalid_token"
            })
            assert response.status_code == 401

    def test_rate_limiting(self, api_client):
        """Test rate limiting protection"""
        endpoint = "/api/auth/login"

        # Make requests up to limit
        for i in range(10):
            response = api_client.post(endpoint, json={
                "email": "test@example.com",
                "password": "wrong_password"
            })

        # Next request should be rate limited
        response = api_client.post(endpoint, json={
            "email": "test@example.com",
            "password": "wrong_password"
        })
        assert response.status_code == 429

    def test_privilege_escalation_protection(self, api_client, regular_user_token):
        """Test privilege escalation protection"""
        # Regular user trying to access admin endpoints
        admin_endpoints = [
            "/api/admin/users",
            "/api/admin/tenants",
            "/api/admin/settings"
        ]

        for endpoint in admin_endpoints:
            response = api_client.get(endpoint, headers={
                "Authorization": f"Bearer {regular_user_token}"
            })
            assert response.status_code in [403, 404]  # Forbidden or Not Found
```

### 8.2 Penetration Testing Checklist

```
Security Testing Checklist:

Authentication & Authorization:
□ JWT token validation and expiration
□ Multi-factor authentication bypass attempts
□ Session fixation attacks
□ Privilege escalation attempts
□ RBAC enforcement testing

Input Validation:
□ SQL injection testing (automated + manual)
□ NoSQL injection testing
□ XSS (reflected, stored, DOM-based)
□ Command injection testing
□ LDAP injection testing
□ XML/XXE injection testing

Network Security:
□ TLS configuration and cipher strength
□ Certificate validation
□ Network segmentation testing
□ Service mesh security (mTLS)
□ API gateway security controls

Data Protection:
□ Encryption at rest validation
□ Encryption in transit validation
□ Key management security
□ Data leakage testing
□ Backup security testing

Infrastructure Security:
□ Container security scanning
□ Kubernetes RBAC testing
□ Network policy enforcement
□ Secrets management testing
□ Container runtime security

Business Logic:
□ Workflow bypass attempts
□ Rate limiting effectiveness
□ Data validation bypass
□ Financial transaction security
□ Multi-tenant isolation testing
```

## 9. Security Configuration Management

### 9.1 Security Policies as Code

```yaml
# Security Policy Configuration
apiVersion: v1
kind: ConfigMap
metadata:
  name: security-policies
  namespace: ai-shifu
data:
  password-policy.json: |
    {
      "minLength": 12,
      "requireUppercase": true,
      "requireLowercase": true,
      "requireNumbers": true,
      "requireSymbols": true,
      "prohibitCommonPasswords": true,
      "prohibitPersonalInfo": true,
      "maxAge": 90,
      "historyLength": 12,
      "lockoutThreshold": 5,
      "lockoutDuration": 1800
    }

  session-policy.json: |
    {
      "accessTokenTTL": 3600,
      "refreshTokenTTL": 604800,
      "maxConcurrentSessions": 3,
      "sessionTimeoutWarning": 300,
      "requireReauthForSensitive": true,
      "ipBindingEnabled": false,
      "deviceBindingEnabled": true
    }

  mfa-policy.json: |
    {
      "required": false,
      "requiredForAdmins": true,
      "requiredForSensitiveActions": true,
      "allowedMethods": ["totp", "sms", "email"],
      "backupCodesCount": 10,
      "gracePeriodDays": 7
    }
```

## 10. Implementation Priority

### Phase 1: Foundation Security (Weeks 1-4)
- JWT-based authentication with refresh tokens
- RBAC implementation with tenant isolation
- Basic audit logging
- TLS/SSL configuration

### Phase 2: Advanced Security (Weeks 5-8)
- Multi-factor authentication
- Data encryption at rest
- Security monitoring and alerting
- WAF deployment

### Phase 3: Compliance & Monitoring (Weeks 9-12)
- GDPR compliance implementation
- Advanced threat detection
- Penetration testing
- Security policy automation

### Phase 4: Optimization (Weeks 13-16)
- Performance optimization
- Advanced analytics
- Security automation
- Continuous compliance monitoring

This comprehensive security architecture ensures that the AI-Shifu SaaS platform maintains enterprise-grade security while providing scalability and compliance with international standards.
