# 租户管理系统详细设计文档

## 1. 概述

### 1.1 系统目标

租户管理系统是AI-Shifu SaaS平台的核心组件，负责管理多租户环境下的组织结构、用户权限、配置设置和生命周期管理。

### 1.2 核心功能

- 租户注册和onboarding
- 多层级用户权限管理
- 租户配置和个性化设置
- 邀请和成员管理
- 租户生命周期管理

## 2. 系统架构

### 2.1 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                    Tenant Management API                    │
├─────────────────────────────────────────────────────────────┤
│  Registration │ User Mgmt │ Config Mgmt │ Invitation Mgmt  │
├─────────────────────────────────────────────────────────────┤
│              Tenant Management Service                      │
├─────────────────────────────────────────────────────────────┤
│    Tenant     │   User     │   Config    │   Invitation    │
│   Repository  │ Repository │ Repository  │   Repository    │
├─────────────────────────────────────────────────────────────┤
│                  Platform Database                         │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 服务组件

**TenantService**: 租户核心管理
- 租户CRUD操作
- 状态管理和生命周期控制
- 配额限制管理

**UserManagementService**: 用户权限管理
- 用户-租户关系管理
- 角色和权限分配
- 访问控制验证

**ConfigurationService**: 配置管理
- 租户个性化配置
- 品牌设置管理
- 功能开关控制

**InvitationService**: 邀请管理
- 用户邀请流程
- 邀请状态跟踪
- 自动化邮件发送

## 3. 数据模型设计

### 3.1 租户实体 (Tenant)

```sql
CREATE TABLE saas_tenants (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_bid VARCHAR(32) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    display_name VARCHAR(200) NOT NULL,
    domain VARCHAR(100) UNIQUE,
    subdomain VARCHAR(50) UNIQUE,
    logo_url VARCHAR(255) DEFAULT '',
    primary_color VARCHAR(7) DEFAULT '#1976d2',

    -- Contact Information
    contact_email VARCHAR(100) NOT NULL,
    contact_phone VARCHAR(20) DEFAULT '',
    billing_email VARCHAR(100) NOT NULL,

    -- Status Management
    status ENUM('inactive', 'active', 'suspended', 'trial') DEFAULT 'trial',
    subscription_status ENUM('none', 'trial', 'active', 'expired', 'cancelled') DEFAULT 'trial',

    -- Lifecycle Timestamps
    trial_ends_at DATETIME,
    activated_at DATETIME,
    suspended_at DATETIME,

    -- Quotas and Limits
    max_users INT DEFAULT 10,
    max_shifus INT DEFAULT 5,
    max_api_calls_per_month INT DEFAULT 1000,
    storage_limit_gb INT DEFAULT 1,

    -- Metadata
    metadata JSON,

    -- Standard Fields
    deleted SMALLINT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_user_bid VARCHAR(32) DEFAULT '',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    updated_user_bid VARCHAR(32) DEFAULT '',

    INDEX idx_tenant_bid (tenant_bid),
    INDEX idx_domain (domain),
    INDEX idx_subdomain (subdomain),
    INDEX idx_status (status),
    INDEX idx_subscription_status (subscription_status),
    INDEX idx_created_at (created_at)
);
```

### 3.2 租户用户关系 (TenantUser)

```sql
CREATE TABLE saas_tenant_users (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_user_bid VARCHAR(32) NOT NULL UNIQUE,
    tenant_bid VARCHAR(32) NOT NULL,
    user_bid VARCHAR(32) NOT NULL,

    -- Role and Permissions
    role ENUM('owner', 'admin', 'editor', 'member', 'viewer') DEFAULT 'member',
    permissions JSON NOT NULL,
    custom_role_name VARCHAR(50) DEFAULT '',

    -- Status Management
    status ENUM('inactive', 'active', 'invited', 'suspended') DEFAULT 'invited',

    -- Invitation Information
    invited_by_user_bid VARCHAR(32) DEFAULT '',
    invited_at DATETIME,
    invitation_accepted_at DATETIME,

    -- Activity Tracking
    last_activity_at DATETIME,
    last_login_at DATETIME,
    login_count INT DEFAULT 0,

    -- Standard Fields
    deleted SMALLINT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE KEY uk_tenant_user (tenant_bid, user_bid),
    INDEX idx_tenant_bid (tenant_bid),
    INDEX idx_user_bid (user_bid),
    INDEX idx_role (role),
    INDEX idx_status (status),
    INDEX idx_last_activity (last_activity_at)
);
```

### 3.3 租户配置 (TenantConfig)

```sql
CREATE TABLE saas_tenant_configs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    config_bid VARCHAR(32) NOT NULL UNIQUE,
    tenant_bid VARCHAR(32) NOT NULL,

    -- Configuration Details
    config_category VARCHAR(50) NOT NULL,
    config_key VARCHAR(100) NOT NULL,
    config_value TEXT,
    config_type ENUM('string', 'int', 'bool', 'json', 'array', 'encrypted') DEFAULT 'string',

    -- Metadata
    description VARCHAR(500) DEFAULT '',
    is_required BOOLEAN DEFAULT FALSE,
    is_readonly BOOLEAN DEFAULT FALSE,
    is_encrypted BOOLEAN DEFAULT FALSE,
    default_value TEXT,
    validation_rules JSON,

    -- Standard Fields
    deleted SMALLINT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE KEY uk_tenant_config (tenant_bid, config_category, config_key),
    INDEX idx_tenant_bid (tenant_bid),
    INDEX idx_category (config_category),
    INDEX idx_key (config_key)
);
```

### 3.4 邀请管理 (TenantInvitation)

```sql
CREATE TABLE saas_tenant_invitations (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    invitation_bid VARCHAR(32) NOT NULL UNIQUE,
    tenant_bid VARCHAR(32) NOT NULL,

    -- Invitation Details
    email VARCHAR(100) NOT NULL,
    role ENUM('admin', 'editor', 'member', 'viewer') DEFAULT 'member',
    custom_role_name VARCHAR(50) DEFAULT '',
    permissions JSON,

    -- Invitation Process
    invited_by_user_bid VARCHAR(32) NOT NULL,
    invitation_token VARCHAR(100) NOT NULL UNIQUE,
    message TEXT DEFAULT '',

    -- Status and Lifecycle
    status ENUM('pending', 'accepted', 'declined', 'expired', 'cancelled') DEFAULT 'pending',
    expires_at DATETIME NOT NULL,
    sent_at DATETIME,
    reminder_sent_at DATETIME,
    accepted_at DATETIME,
    declined_at DATETIME,

    -- Response Information
    accepted_user_bid VARCHAR(32) DEFAULT '',
    decline_reason TEXT DEFAULT '',

    -- Standard Fields
    deleted SMALLINT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_tenant_bid (tenant_bid),
    INDEX idx_email (email),
    INDEX idx_token (invitation_token),
    INDEX idx_status (status),
    INDEX idx_expires_at (expires_at),
    INDEX idx_invited_by (invited_by_user_bid)
);
```

## 4. 业务流程设计

### 4.1 租户注册流程

```
用户访问注册页面
         ↓
填写基本信息 (组织名称、联系方式)
         ↓
选择订阅计划和配置
         ↓
域名/子域名可用性检查
         ↓
支付信息设置 (如需要)
         ↓
创建租户和管理员账户
         ↓
初始化租户配置
         ↓
发送欢迎邮件和onboarding引导
         ↓
重定向到租户管理后台
```

**注册API设计**
```python
class TenantRegistrationRequest:
    organization_name: str
    display_name: str
    admin_email: str
    admin_name: str
    subdomain: str
    custom_domain: Optional[str]
    subscription_plan: str
    contact_phone: Optional[str]
    billing_email: Optional[str]
    initial_config: Optional[Dict]

class TenantRegistrationService:
    async def register_tenant(self, request: TenantRegistrationRequest):
        # 1. 验证输入数据
        await self.validate_registration_data(request)

        # 2. 检查域名可用性
        await self.check_domain_availability(request.subdomain, request.custom_domain)

        # 3. 创建租户
        tenant = await self.create_tenant(request)

        # 4. 创建管理员用户
        admin_user = await self.create_admin_user(tenant, request)

        # 5. 初始化默认配置
        await self.initialize_tenant_config(tenant, request.initial_config)

        # 6. 设置试用期
        await self.setup_trial_period(tenant)

        # 7. 发送欢迎邮件
        await self.send_welcome_email(admin_user, tenant)

        return tenant
```

### 4.2 用户邀请流程

```
管理员发起邀请
         ↓
验证权限和邀请配额
         ↓
生成邀请Token和链接
         ↓
发送邀请邮件
         ↓
被邀请用户点击链接
         ↓
验证邀请有效性
         ↓
用户注册/登录
         ↓
接受邀请并分配角色
         ↓
更新租户用户关系
         ↓
发送欢迎通知
```

**邀请API设计**
```python
class UserInvitationRequest:
    email: str
    role: str
    custom_role_name: Optional[str]
    permissions: Optional[Dict]
    message: Optional[str]
    expires_in_days: int = 7

class InvitationService:
    async def invite_user(self, tenant_bid: str, inviter_user_bid: str, request: UserInvitationRequest):
        # 1. 验证邀请权限
        await self.validate_invitation_permission(tenant_bid, inviter_user_bid)

        # 2. 检查用户配额
        await self.check_user_quota(tenant_bid)

        # 3. 检查重复邀请
        existing = await self.check_existing_invitation(tenant_bid, request.email)
        if existing:
            return await self.resend_invitation(existing.invitation_bid)

        # 4. 创建邀请记录
        invitation = await self.create_invitation(tenant_bid, inviter_user_bid, request)

        # 5. 发送邀请邮件
        await self.send_invitation_email(invitation)

        return invitation

    async def accept_invitation(self, invitation_token: str, user_bid: str):
        # 1. 验证邀请有效性
        invitation = await self.validate_invitation_token(invitation_token)

        # 2. 创建用户-租户关系
        tenant_user = await self.create_tenant_user(invitation, user_bid)

        # 3. 更新邀请状态
        await self.mark_invitation_accepted(invitation, user_bid)

        # 4. 发送欢迎通知
        await self.send_welcome_notification(tenant_user)

        return tenant_user
```

### 4.3 权限管理流程

**角色权限矩阵**
```python
ROLE_PERMISSIONS = {
    'owner': {
        'tenant_management': ['read', 'write', 'delete'],
        'user_management': ['read', 'write', 'delete', 'invite'],
        'shifu_management': ['read', 'write', 'delete', 'publish'],
        'billing_management': ['read', 'write'],
        'analytics': ['read', 'export'],
        'settings': ['read', 'write']
    },
    'admin': {
        'tenant_management': ['read', 'write'],
        'user_management': ['read', 'write', 'invite'],
        'shifu_management': ['read', 'write', 'delete', 'publish'],
        'billing_management': ['read'],
        'analytics': ['read', 'export'],
        'settings': ['read', 'write']
    },
    'editor': {
        'tenant_management': ['read'],
        'user_management': ['read'],
        'shifu_management': ['read', 'write', 'publish'],
        'billing_management': [],
        'analytics': ['read'],
        'settings': ['read']
    },
    'member': {
        'tenant_management': ['read'],
        'user_management': ['read'],
        'shifu_management': ['read', 'write'],
        'billing_management': [],
        'analytics': ['read'],
        'settings': ['read']
    },
    'viewer': {
        'tenant_management': ['read'],
        'user_management': ['read'],
        'shifu_management': ['read'],
        'billing_management': [],
        'analytics': ['read'],
        'settings': ['read']
    }
}
```

**权限验证中间件**
```python
class PermissionMiddleware:
    async def check_permission(self, user_bid: str, tenant_bid: str, resource: str, action: str):
        # 1. 获取用户在租户中的角色
        tenant_user = await self.get_tenant_user(user_bid, tenant_bid)
        if not tenant_user or tenant_user.status != 'active':
            raise PermissionDeniedError("User not found or inactive in tenant")

        # 2. 检查基础角色权限
        role_permissions = ROLE_PERMISSIONS.get(tenant_user.role, {})
        resource_permissions = role_permissions.get(resource, [])

        if action in resource_permissions:
            return True

        # 3. 检查自定义权限
        custom_permissions = tenant_user.permissions or {}
        custom_resource_permissions = custom_permissions.get(resource, [])

        if action in custom_resource_permissions:
            return True

        raise PermissionDeniedError(f"Permission denied for action '{action}' on resource '{resource}'")
```

## 5. 配置管理系统

### 5.1 配置分类

**Brand Configuration (品牌配置)**
```json
{
  "logo_url": "https://cdn.example.com/logo.png",
  "primary_color": "#1976d2",
  "secondary_color": "#424242",
  "font_family": "Inter, sans-serif",
  "custom_css": ".custom-style { color: red; }",
  "favicon_url": "https://cdn.example.com/favicon.ico"
}
```

**Feature Configuration (功能配置)**
```json
{
  "sso_enabled": true,
  "api_access_enabled": false,
  "advanced_analytics": true,
  "custom_domain_enabled": true,
  "white_label": false,
  "max_shifu_per_user": 10,
  "allowed_file_types": ["pdf", "docx", "txt"],
  "max_file_size_mb": 50
}
```

**Integration Configuration (集成配置)**
```json
{
  "oauth_providers": ["google", "microsoft", "okta"],
  "webhook_urls": {
    "user_created": "https://api.client.com/webhooks/user_created",
    "subscription_changed": "https://api.client.com/webhooks/subscription"
  },
  "api_keys": {
    "openai_key": "encrypted:sk-...",
    "custom_llm_endpoint": "https://api.custom.com/v1"
  }
}
```

**Security Configuration (安全配置)**
```json
{
  "password_policy": {
    "min_length": 8,
    "require_uppercase": true,
    "require_lowercase": true,
    "require_numbers": true,
    "require_special_chars": true
  },
  "session_timeout_minutes": 480,
  "max_login_attempts": 5,
  "lockout_duration_minutes": 30,
  "two_factor_required": false,
  "ip_whitelist": ["192.168.1.0/24"]
}
```

### 5.2 配置管理API

```python
class ConfigurationService:
    async def get_config(self, tenant_bid: str, category: str, key: str = None):
        if key:
            config = await self.config_repository.get_by_key(tenant_bid, category, key)
            return self.decrypt_if_needed(config)
        else:
            configs = await self.config_repository.get_by_category(tenant_bid, category)
            return {c.config_key: self.decrypt_if_needed(c) for c in configs}

    async def set_config(self, tenant_bid: str, category: str, key: str, value: Any,
                        config_type: str = 'string', encrypted: bool = False):
        # 1. 验证配置规则
        await self.validate_config_value(category, key, value)

        # 2. 加密敏感配置
        if encrypted:
            value = await self.encrypt_config_value(value)

        # 3. 保存配置
        config = TenantConfig(
            tenant_bid=tenant_bid,
            config_category=category,
            config_key=key,
            config_value=json.dumps(value) if config_type == 'json' else str(value),
            config_type=config_type,
            is_encrypted=encrypted
        )

        await self.config_repository.upsert(config)

        # 4. 清理缓存
        await self.cache.delete(f"config:{tenant_bid}:{category}")

        return config

    async def get_merged_config(self, tenant_bid: str):
        """获取租户的完整配置，包括默认值"""
        # 1. 获取默认配置
        default_config = await self.get_default_config()

        # 2. 获取租户配置
        tenant_config = await self.get_all_tenant_config(tenant_bid)

        # 3. 合并配置
        merged = deep_merge(default_config, tenant_config)

        return merged
```

## 6. 生命周期管理

### 6.1 租户状态机

```
     创建
      ↓
  Trial (试用期)
      ↓
   ┌─ Active (激活) ←→ Suspended (暂停)
   │     ↓
   └→ Cancelled (取消) → Deleted (删除)
```

**状态转换规则**
```python
STATE_TRANSITIONS = {
    'trial': ['active', 'cancelled', 'deleted'],
    'active': ['suspended', 'cancelled'],
    'suspended': ['active', 'cancelled'],
    'cancelled': ['deleted'],
    'deleted': []  # 终态
}

class TenantLifecycleService:
    async def transition_state(self, tenant_bid: str, new_state: str, reason: str = '', operator_user_bid: str = ''):
        tenant = await self.get_tenant(tenant_bid)
        current_state = tenant.status

        # 1. 验证状态转换
        if new_state not in STATE_TRANSITIONS.get(current_state, []):
            raise InvalidStateTransitionError(f"Cannot transition from {current_state} to {new_state}")

        # 2. 执行状态转换前的动作
        await self.before_state_transition(tenant, current_state, new_state)

        # 3. 更新状态
        tenant.status = new_state
        await self.tenant_repository.update(tenant)

        # 4. 记录状态变更日志
        await self.log_state_change(tenant_bid, current_state, new_state, reason, operator_user_bid)

        # 5. 执行状态转换后的动作
        await self.after_state_transition(tenant, current_state, new_state)

        return tenant
```

### 6.2 试用期管理

```python
class TrialManagementService:
    async def setup_trial(self, tenant_bid: str, duration_days: int = 14):
        trial_end = datetime.utcnow() + timedelta(days=duration_days)

        await self.tenant_repository.update_trial_period(tenant_bid, trial_end)

        # 设置试用期提醒任务
        await self.schedule_trial_reminders(tenant_bid, trial_end)

    async def check_trial_expiry(self):
        """定时任务：检查试用期到期"""
        expiring_tenants = await self.tenant_repository.get_expiring_trials()

        for tenant in expiring_tenants:
            if tenant.trial_ends_at <= datetime.utcnow():
                # 试用期已到期
                await self.handle_trial_expired(tenant)
            elif tenant.trial_ends_at <= datetime.utcnow() + timedelta(days=3):
                # 3天内到期，发送提醒
                await self.send_trial_expiry_reminder(tenant)

    async def handle_trial_expired(self, tenant):
        # 检查是否已设置付费订阅
        subscription = await self.billing_service.get_active_subscription(tenant.tenant_bid)

        if subscription:
            # 有付费订阅，转为正式用户
            await self.lifecycle_service.transition_state(tenant.tenant_bid, 'active', 'Trial converted to paid')
        else:
            # 无付费订阅，暂停账户
            await self.lifecycle_service.transition_state(tenant.tenant_bid, 'suspended', 'Trial expired')
            await self.send_trial_expired_notification(tenant)
```

## 7. API接口设计

### 7.1 租户管理API

```yaml
# OpenAPI 3.0 Specification
paths:
  /api/v1/tenants:
    post:
      summary: 创建租户
      requestBody:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/CreateTenantRequest'
      responses:
        201:
          description: 租户创建成功
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/TenantResponse'

    get:
      summary: 获取租户列表 (平台管理员)
      parameters:
        - name: status
          in: query
          schema:
            type: string
            enum: [trial, active, suspended, cancelled]
        - name: page
          in: query
          schema:
            type: integer
            default: 1
        - name: limit
          in: query
          schema:
            type: integer
            default: 20
      responses:
        200:
          description: 租户列表
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/PaginatedTenantList'

  /api/v1/tenants/{tenant_bid}:
    get:
      summary: 获取租户详情
      parameters:
        - name: tenant_bid
          in: path
          required: true
          schema:
            type: string
      responses:
        200:
          description: 租户详情
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/TenantResponse'

    put:
      summary: 更新租户信息
      parameters:
        - name: tenant_bid
          in: path
          required: true
          schema:
            type: string
      requestBody:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/UpdateTenantRequest'
      responses:
        200:
          description: 更新成功
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/TenantResponse'

  /api/v1/tenants/{tenant_bid}/users:
    get:
      summary: 获取租户用户列表
      parameters:
        - name: tenant_bid
          in: path
          required: true
          schema:
            type: string
        - name: role
          in: query
          schema:
            type: string
            enum: [owner, admin, editor, member, viewer]
        - name: status
          in: query
          schema:
            type: string
            enum: [active, inactive, invited, suspended]
      responses:
        200:
          description: 用户列表
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/TenantUserResponse'

  /api/v1/tenants/{tenant_bid}/invitations:
    post:
      summary: 邀请用户
      parameters:
        - name: tenant_bid
          in: path
          required: true
          schema:
            type: string
      requestBody:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/InviteUserRequest'
      responses:
        201:
          description: 邀请发送成功
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/InvitationResponse'

    get:
      summary: 获取邀请列表
      parameters:
        - name: tenant_bid
          in: path
          required: true
          schema:
            type: string
        - name: status
          in: query
          schema:
            type: string
            enum: [pending, accepted, declined, expired]
      responses:
        200:
          description: 邀请列表
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/InvitationResponse'

components:
  schemas:
    CreateTenantRequest:
      type: object
      required:
        - name
        - admin_email
        - subdomain
      properties:
        name:
          type: string
          maxLength: 100
        display_name:
          type: string
          maxLength: 200
        admin_email:
          type: string
          format: email
        admin_name:
          type: string
        subdomain:
          type: string
          pattern: '^[a-z0-9-]+$'
        custom_domain:
          type: string
        contact_phone:
          type: string
        billing_email:
          type: string
          format: email
        subscription_plan:
          type: string
          enum: [starter, professional, enterprise]

    TenantResponse:
      type: object
      properties:
        tenant_bid:
          type: string
        name:
          type: string
        display_name:
          type: string
        domain:
          type: string
        subdomain:
          type: string
        logo_url:
          type: string
        primary_color:
          type: string
        status:
          type: string
          enum: [inactive, active, suspended, trial]
        subscription_status:
          type: string
          enum: [none, trial, active, expired, cancelled]
        trial_ends_at:
          type: string
          format: date-time
        max_users:
          type: integer
        max_shifus:
          type: integer
        max_api_calls_per_month:
          type: integer
        storage_limit_gb:
          type: integer
        created_at:
          type: string
          format: date-time
        updated_at:
          type: string
          format: date-time
```

### 7.2 配置管理API

```python
# 配置管理路由
@router.get("/tenants/{tenant_bid}/config")
async def get_tenant_config(tenant_bid: str, category: str = None):
    """获取租户配置"""
    if category:
        config = await config_service.get_config(tenant_bid, category)
    else:
        config = await config_service.get_merged_config(tenant_bid)
    return {"data": config}

@router.put("/tenants/{tenant_bid}/config/{category}/{key}")
async def update_config(tenant_bid: str, category: str, key: str, request: ConfigUpdateRequest):
    """更新配置项"""
    config = await config_service.set_config(
        tenant_bid=tenant_bid,
        category=category,
        key=key,
        value=request.value,
        config_type=request.config_type,
        encrypted=request.encrypted
    )
    return {"data": config}

@router.get("/tenants/{tenant_bid}/config/schema")
async def get_config_schema(tenant_bid: str):
    """获取配置模式定义"""
    schema = await config_service.get_config_schema(tenant_bid)
    return {"data": schema}
```

## 8. 安全考虑

### 8.1 数据隔离

- 所有租户相关数据严格基于tenant_bid隔离
- API层面的租户上下文验证
- 数据库查询自动注入租户过滤条件

### 8.2 权限控制

- 基于角色的访问控制 (RBAC)
- 细粒度的功能权限管理
- API接口级别的权限验证

### 8.3 敏感信息保护

- 配置项加密存储
- API密钥安全管理
- 审计日志记录

## 9. 性能优化

### 9.1 缓存策略

```python
class TenantCacheService:
    async def get_tenant_with_cache(self, tenant_bid: str):
        cache_key = f"tenant:{tenant_bid}"
        cached = await self.redis.get(cache_key)

        if cached:
            return json.loads(cached)

        tenant = await self.tenant_repository.get_by_bid(tenant_bid)
        await self.redis.setex(cache_key, 3600, json.dumps(tenant.dict()))

        return tenant

    async def invalidate_tenant_cache(self, tenant_bid: str):
        cache_keys = [
            f"tenant:{tenant_bid}",
            f"tenant_config:{tenant_bid}:*",
            f"tenant_users:{tenant_bid}"
        ]
        await self.redis.delete(*cache_keys)
```

### 9.2 数据库优化

- 合理的索引设计
- 分页查询优化
- 批量操作支持
- 连接池配置优化

## 10. 监控和告警

### 10.1 关键指标

- 租户注册转化率
- 试用期转付费率
- 用户邀请接受率
- API响应时间
- 错误率

### 10.2 告警配置

- 租户状态异常变更
- 配额使用超限
- 邀请发送失败
- 数据库连接异常

这个租户管理系统设计提供了完整的多租户管理能力，支持租户的整个生命周期，并具备良好的扩展性和安全性。
