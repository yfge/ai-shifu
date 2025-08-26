# AI-Shifu SaaS 1.0 分库架构设计

## 概述

本文档设计AI-Shifu SaaS 1.0版本的分库架构方案，基于现有系统进行渐进式改造，实现：

1. **分库管理** - 将系统拆分为统一系统库和租户业务库
2. **保留现有用户系统** - 用户数据保留在系统库，增加SaaS租户管理
3. **域名路由** - 通过不同域名路由到不同租户数据库

## 1. 架构设计原则

### 1.1 设计目标

```
现有单体架构 → SaaS 1.0分库架构
     │                    │
  单一数据库          系统库 + 租户库
     │                    │
  所有数据混合        用户系统 + 租户数据
     │                    │
  单域名访问          多域名租户路由
```

### 1.2 核心原则

- **渐进式改造** - 最小化对现有系统的影响
- **向后兼容** - 现有功能保持正常工作
- **数据一致性** - 确保用户数据和租户数据的关联正确性
- **性能优先** - 分库后性能不能下降
- **运维友好** - 简化数据库运维复杂度

## 2. 数据库架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────┐
│                   AI-Shifu SaaS 1.0                    │
├─────────────────────────────────────────────────────────┤
│                  应用层 (Flask)                         │
├──────────────────┬──────────────────────────────────────┤
│    路由层        │         数据访问层                   │
│  (Domain Router) │    (Database Router)                │
├──────────────────┼──────────────────────────────────────┤
│   域名解析       │       数据库连接池                   │
│   tenant1.com    │     (Connection Pool)               │
│   tenant2.com    │                                     │
│   app.com        │                                     │
└──────────────────┴──────────────────────────────────────┘
                            │
      ┌─────────────────────┼─────────────────────┐
      │                     │                     │
┌─────▼─────┐        ┌─────▼─────┐        ┌─────▼─────┐
│  系统库   │        │  租户库A  │        │  租户库B  │
│ ai_shifu  │        │ai_shifu_  │        │ai_shifu_  │
│  _system  │        │ tenant_a  │        │ tenant_b  │
├───────────┤        ├───────────┤        ├───────────┤
│用户管理   │        │业务数据   │        │业务数据   │
│租户管理   │        │订单数据   │        │订单数据   │
│系统配置   │        │学习记录   │        │学习记录   │
│认证信息   │        │Shifu内容  │        │Shifu内容  │
└───────────┘        └───────────┘        └───────────┘
```

### 2.2 系统库设计 (ai_shifu_system)

```sql
-- 系统库：仅保留用户管理和租户管理核心功能
-- 数据库名: ai_shifu_system

-- 1. 用户核心表（保持现有结构）
CREATE TABLE user_info (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT 'Unique ID',
    user_id VARCHAR(36) NOT NULL INDEX DEFAULT '' COMMENT 'User UUID',
    username VARCHAR(255) NOT NULL DEFAULT '' COMMENT 'Login username',
    name VARCHAR(255) NOT NULL DEFAULT '' COMMENT 'User real name',
    email VARCHAR(255) NOT NULL DEFAULT '' COMMENT 'Email',
    mobile VARCHAR(20) NOT NULL INDEX DEFAULT '' COMMENT 'Mobile',
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Creation time',
    updated TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Update time',
    user_state INTEGER DEFAULT 0 COMMENT 'User state',
    user_sex INTEGER DEFAULT 0 COMMENT 'User sex',
    user_birth DATE DEFAULT '2003-1-1' COMMENT 'User birth',
    user_avatar VARCHAR(255) DEFAULT '' COMMENT 'User avatar',
    user_open_id VARCHAR(255) INDEX DEFAULT '' COMMENT 'User open id',
    user_unicon_id VARCHAR(255) INDEX DEFAULT '' COMMENT 'User unicon id',
    user_language VARCHAR(30) DEFAULT 'zh-CN' COMMENT 'User language',
    is_admin BOOLEAN NOT NULL DEFAULT FALSE COMMENT 'Is admin',
    is_creator BOOLEAN NOT NULL DEFAULT FALSE COMMENT 'Is creator',
    extra_data TEXT DEFAULT '' COMMENT 'Extra data'
);

-- 2. 用户认证相关表
CREATE TABLE user_token (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT 'Unique ID',
    user_id VARCHAR(36) NOT NULL DEFAULT '' COMMENT 'User UUID',
    token VARCHAR(255) NOT NULL DEFAULT '' COMMENT 'Token',
    token_type INTEGER NOT NULL DEFAULT 0 COMMENT 'Token type',
    token_expired_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Token expired time',
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Creation time',
    updated TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Update time'
);

CREATE TABLE user_verify_code (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT 'Unique ID',
    phone VARCHAR(36) NOT NULL DEFAULT '' COMMENT 'User phone',
    mail VARCHAR(36) NOT NULL DEFAULT '' COMMENT 'User mail',
    verify_code VARCHAR(10) NOT NULL DEFAULT '' COMMENT 'Verify code',
    verify_code_type INTEGER NOT NULL DEFAULT 0 COMMENT 'Verify code type',
    verify_code_send INTEGER NOT NULL DEFAULT 0 COMMENT 'Verification code send state',
    verify_code_used INTEGER NOT NULL DEFAULT 0 COMMENT 'Verification code used state',
    user_ip VARCHAR(100) NOT NULL DEFAULT '' COMMENT 'User ip',
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Creation time',
    updated TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Update time'
);

CREATE TABLE user_conversion (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT 'Unique ID',
    user_id VARCHAR(36) NOT NULL DEFAULT '' COMMENT 'User UUID',
    conversion_id VARCHAR(36) NOT NULL DEFAULT '' COMMENT 'Conversion UUID',
    conversion_source VARCHAR(36) NOT NULL DEFAULT 0 COMMENT 'Conversion type',
    conversion_status INTEGER NOT NULL DEFAULT 0 COMMENT 'Conversion state',
    conversion_uuid VARCHAR(36) NOT NULL DEFAULT '' COMMENT 'Conversion UUID',
    conversion_third_platform VARCHAR(255) NOT NULL DEFAULT '' COMMENT 'Conversion third platform',
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Creation time',
    updated TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Update time'
);

-- 3. SaaS租户管理表
CREATE TABLE saas_tenants (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id VARCHAR(32) NOT NULL UNIQUE INDEX COMMENT '租户唯一标识',
    tenant_name VARCHAR(100) NOT NULL COMMENT '租户名称',
    tenant_domain VARCHAR(100) UNIQUE COMMENT '租户域名',
    database_name VARCHAR(100) NOT NULL COMMENT '租户数据库名',
    database_host VARCHAR(200) DEFAULT 'localhost' COMMENT '数据库主机',
    database_port INT DEFAULT 3306 COMMENT '数据库端口',
    status SMALLINT NOT NULL DEFAULT 1 COMMENT '状态: 0=停用, 1=正常, 2=维护',
    plan_type VARCHAR(50) DEFAULT 'basic' COMMENT '套餐类型',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted SMALLINT NOT NULL DEFAULT 0 INDEX,
    INDEX idx_domain (tenant_domain),
    INDEX idx_status (status),
    INDEX idx_deleted (deleted)
) COMMENT '租户信息表';

-- 3. 新增：租户用户关联表
CREATE TABLE saas_tenant_users (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id VARCHAR(32) NOT NULL INDEX COMMENT '租户标识',
    user_id VARCHAR(36) NOT NULL INDEX COMMENT '用户UUID (关联user_info.user_id)',
    role VARCHAR(50) DEFAULT 'user' COMMENT '用户在租户中的角色: admin, user, viewer',
    permissions JSON COMMENT '权限配置',
    status SMALLINT NOT NULL DEFAULT 1 COMMENT '状态: 0=停用, 1=正常',
    joined_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '加入时间',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted SMALLINT NOT NULL DEFAULT 0 INDEX,
    UNIQUE KEY uk_tenant_user (tenant_id, user_id, deleted),
    INDEX idx_tenant (tenant_id),
    INDEX idx_user (user_id),
    INDEX idx_role (role)
) COMMENT '租户用户关联表';

-- 4. 新增：系统配置表
CREATE TABLE saas_system_config (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    config_key VARCHAR(100) NOT NULL UNIQUE INDEX COMMENT '配置键',
    config_value TEXT COMMENT '配置值',
    config_type VARCHAR(20) DEFAULT 'string' COMMENT '配置类型: string, json, number, boolean',
    description VARCHAR(200) COMMENT '配置描述',
    is_public TINYINT DEFAULT 0 COMMENT '是否公开配置',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) COMMENT '系统配置表';

-- 5. 新增：租户数据库连接配置
CREATE TABLE saas_tenant_databases (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id VARCHAR(32) NOT NULL INDEX COMMENT '租户标识',
    db_type VARCHAR(20) DEFAULT 'mysql' COMMENT '数据库类型',
    db_host VARCHAR(200) NOT NULL COMMENT '数据库主机',
    db_port INT NOT NULL DEFAULT 3306 COMMENT '数据库端口',
    db_name VARCHAR(100) NOT NULL COMMENT '数据库名',
    db_username VARCHAR(100) NOT NULL COMMENT '数据库用户名',
    db_password_encrypted TEXT NOT NULL COMMENT '加密的数据库密码',
    max_connections INT DEFAULT 20 COMMENT '最大连接数',
    is_active TINYINT NOT NULL DEFAULT 1 COMMENT '是否激活',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_tenant_db (tenant_id),
    INDEX idx_active (is_active)
) COMMENT '租户数据库配置表';

-- 6. 新增：API访问日志表（用于监控和统计）
CREATE TABLE saas_access_logs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id VARCHAR(32) INDEX COMMENT '租户标识',
    user_id VARCHAR(36) INDEX COMMENT '用户标识',
    request_id VARCHAR(36) INDEX COMMENT '请求ID',
    method VARCHAR(10) COMMENT '请求方法',
    path VARCHAR(500) COMMENT '请求路径',
    status_code INT COMMENT '响应状态码',
    response_time INT COMMENT '响应时间(ms)',
    ip_address VARCHAR(45) COMMENT 'IP地址',
    user_agent TEXT COMMENT 'User Agent',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_tenant_time (tenant_id, created_at),
    INDEX idx_user_time (user_id, created_at),
    INDEX idx_request_time (created_at)
) COMMENT 'API访问日志表';

-- 插入默认数据
INSERT INTO saas_system_config (config_key, config_value, config_type, description) VALUES
('system.default_tenant', 'default', 'string', '默认租户ID'),
('system.multi_tenant_enabled', 'true', 'boolean', '是否启用多租户'),
('system.tenant_signup_enabled', 'false', 'boolean', '是否允许租户自助注册'),
('database.default_max_connections', '50', 'number', '数据库默认最大连接数');

-- 创建默认租户（用于现有数据）
INSERT INTO saas_tenants (tenant_id, tenant_name, tenant_domain, database_name, status) VALUES
('default', '默认租户', 'app.ai-shifu.com', 'ai_shifu_default', 1);
```

### 2.3 租户库设计模板 (ai_shifu_tenant_{tenant_id})

```sql
-- 租户数据库：包含所有业务数据
-- 例如：ai_shifu_tenant_default, ai_shifu_tenant_company1

-- 1. 订单相关表
CREATE TABLE order_orders (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    order_bid VARCHAR(36) NOT NULL DEFAULT '' COMMENT 'Order business identifier',
    shifu_bid VARCHAR(36) NOT NULL DEFAULT '' COMMENT 'Shifu business identifier',
    user_id VARCHAR(36) NOT NULL DEFAULT '' COMMENT 'User identifier (关联系统库user_info.user_id)',
    payable_price DECIMAL(10,2) NOT NULL DEFAULT 0.00 COMMENT 'Shifu original price',
    paid_price DECIMAL(10,2) NOT NULL DEFAULT 0.00 COMMENT 'Paid price',
    status SMALLINT NOT NULL DEFAULT 501 COMMENT 'Status: 501=init, 502=paid, 503=refunded, 504=unpaid, 505=timeout',
    deleted SMALLINT NOT NULL DEFAULT 0 COMMENT 'Deletion flag: 0=active, 1=deleted',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Creation time',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Update time',
    INDEX idx_order_bid (order_bid),
    INDEX idx_shifu_bid (shifu_bid),
    INDEX idx_user_id (user_id),
    INDEX idx_status (status),
    INDEX idx_deleted (deleted)
) COMMENT 'Order orders';

CREATE TABLE order_pingxx_orders (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    pingxx_order_bid VARCHAR(36) NOT NULL DEFAULT '' COMMENT 'Pingxx order business identifier',
    user_id VARCHAR(36) NOT NULL DEFAULT '' COMMENT 'User identifier',
    shifu_bid VARCHAR(36) NOT NULL DEFAULT '' COMMENT 'Shifu business identifier',
    order_bid VARCHAR(36) NOT NULL DEFAULT '' COMMENT 'Order business identifier',
    transaction_no VARCHAR(36) NOT NULL DEFAULT '' COMMENT 'Pingxx transaction number',
    app_id VARCHAR(36) NOT NULL DEFAULT '' COMMENT 'Pingxx app identifier',
    channel VARCHAR(36) NOT NULL DEFAULT '' COMMENT 'Payment channel',
    amount BIGINT NOT NULL DEFAULT 0 COMMENT 'Payment amount',
    currency VARCHAR(36) NOT NULL DEFAULT 'CNY' COMMENT 'Currency',
    subject VARCHAR(255) NOT NULL DEFAULT '' COMMENT 'Payment subject',
    body VARCHAR(255) NOT NULL DEFAULT '' COMMENT 'Payment body',
    client_ip VARCHAR(255) NOT NULL DEFAULT '' COMMENT 'Client IP',
    extra TEXT COMMENT 'Extra information',
    status SMALLINT NOT NULL DEFAULT 0 COMMENT 'Status: 0=unpaid, 1=paid, 2=refunded, 3=closed, 4=failed',
    charge_id VARCHAR(255) NOT NULL DEFAULT '' COMMENT 'Charge identifier',
    paid_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'Payment time',
    refunded_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'Refund time',
    closed_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'Close time',
    failed_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'Failed time',
    refund_id VARCHAR(255) NOT NULL DEFAULT '' COMMENT 'Refund identifier',
    failure_code VARCHAR(255) NOT NULL DEFAULT '' COMMENT 'Failure code',
    failure_msg VARCHAR(255) NOT NULL DEFAULT '' COMMENT 'Failure message',
    charge_object TEXT COMMENT 'Pingxx raw charge object',
    deleted SMALLINT NOT NULL DEFAULT 0 COMMENT 'Deletion flag: 0=active, 1=deleted',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Creation time',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Update time',
    INDEX idx_pingxx_order_bid (pingxx_order_bid),
    INDEX idx_user_id (user_id),
    INDEX idx_shifu_bid (shifu_bid),
    INDEX idx_order_bid (order_bid),
    INDEX idx_transaction_no (transaction_no),
    INDEX idx_charge_id (charge_id),
    INDEX idx_refund_id (refund_id),
    INDEX idx_deleted (deleted)
) COMMENT 'Order pingxx orders';

-- 2. Shifu相关表（包含所有Shifu业务数据）

-- 2.1 草稿Shifu表
CREATE TABLE shifu_draft_shifus (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    shifu_bid VARCHAR(32) NOT NULL INDEX DEFAULT '' COMMENT 'Shifu business identifier',
    title VARCHAR(100) NOT NULL DEFAULT '' COMMENT 'Shifu title',
    keywords VARCHAR(100) NOT NULL DEFAULT '' COMMENT 'Associated keywords',
    description VARCHAR(500) NOT NULL DEFAULT '' COMMENT 'Shifu description',
    avatar_res_bid VARCHAR(32) NOT NULL DEFAULT '' COMMENT 'Avatar resource business identifier',
    llm VARCHAR(100) NOT NULL DEFAULT '' COMMENT 'LLM model name',
    llm_temperature DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT 'LLM temperature parameter',
    llm_system_prompt TEXT NOT NULL DEFAULT '' COMMENT 'LLM system prompt',
    ask_enabled_status SMALLINT NOT NULL DEFAULT 5101 COMMENT 'Ask agent status: 5101=default, 5102=disabled, 5103=enabled',
    ask_llm VARCHAR(100) NOT NULL DEFAULT '' COMMENT 'Ask agent LLM model',
    ask_llm_temperature DECIMAL(10,2) NOT NULL DEFAULT 0.0 COMMENT 'Ask agent LLM temperature',
    ask_llm_system_prompt TEXT NOT NULL DEFAULT '' COMMENT 'Ask agent LLM system prompt',
    price DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT 'Shifu price',
    deleted SMALLINT NOT NULL DEFAULT 0 COMMENT 'Deletion flag: 0=active, 1=deleted',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Creation timestamp',
    created_user_bid VARCHAR(32) NOT NULL INDEX DEFAULT '' COMMENT 'Creator user business identifier',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Last update timestamp',
    updated_user_bid VARCHAR(32) NOT NULL INDEX DEFAULT '' COMMENT 'Last updater user business identifier',
    INDEX idx_shifu_bid (shifu_bid),
    INDEX idx_creator (created_user_bid),
    INDEX idx_deleted (deleted)
) COMMENT 'Shifu draft shifus';

-- 2.2 已发布Shifu表
CREATE TABLE shifu_published_shifus (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    shifu_bid VARCHAR(32) NOT NULL INDEX DEFAULT '' COMMENT 'Shifu business identifier',
    title VARCHAR(100) NOT NULL DEFAULT '' COMMENT 'Shifu title',
    keywords VARCHAR(100) NOT NULL DEFAULT '' COMMENT 'Associated keywords',
    description VARCHAR(500) NOT NULL DEFAULT '' COMMENT 'Shifu description',
    avatar_res_bid VARCHAR(32) NOT NULL DEFAULT '' COMMENT 'Avatar resource business identifier',
    llm VARCHAR(100) NOT NULL DEFAULT '' COMMENT 'LLM model name',
    llm_temperature DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT 'LLM temperature parameter',
    llm_system_prompt TEXT NOT NULL DEFAULT '' COMMENT 'LLM system prompt',
    ask_enabled_status SMALLINT NOT NULL DEFAULT 5101 COMMENT 'Ask agent status: 5101=default, 5102=disabled, 5103=enabled',
    ask_llm VARCHAR(100) NOT NULL DEFAULT '' COMMENT 'Ask agent LLM model',
    ask_llm_temperature DECIMAL(10,2) NOT NULL DEFAULT 0.0 COMMENT 'Ask agent LLM temperature',
    ask_llm_system_prompt TEXT NOT NULL DEFAULT '' COMMENT 'Ask agent LLM system prompt',
    price DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT 'Shifu price',
    deleted SMALLINT NOT NULL DEFAULT 0 COMMENT 'Deletion flag: 0=active, 1=deleted',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Creation timestamp',
    created_user_bid VARCHAR(32) NOT NULL INDEX DEFAULT '' COMMENT 'Creator user business identifier',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Last update timestamp',
    updated_user_bid VARCHAR(32) NOT NULL INDEX DEFAULT '' COMMENT 'Last updater user business identifier',
    INDEX idx_shifu_bid (shifu_bid),
    INDEX idx_creator (created_user_bid),
    INDEX idx_deleted (deleted)
) COMMENT 'Shifu published shifus';

-- 2.3 草稿大纲项表
CREATE TABLE shifu_draft_outline_items (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    outline_item_bid VARCHAR(32) NOT NULL INDEX DEFAULT '' COMMENT 'Outline item business identifier',
    shifu_bid VARCHAR(32) NOT NULL INDEX DEFAULT '' COMMENT 'Shifu business identifier',
    title VARCHAR(100) NOT NULL DEFAULT '' COMMENT 'Outline item title',
    type SMALLINT NOT NULL DEFAULT 0 COMMENT 'Outline item type: 401=trial, 402=normal',
    hidden SMALLINT NOT NULL DEFAULT 0 COMMENT 'Hidden flag: 0=visible, 1=hidden',
    parent_bid VARCHAR(32) NOT NULL INDEX DEFAULT '' COMMENT 'Parent outline item business identifier',
    position VARCHAR(10) NOT NULL INDEX DEFAULT '' COMMENT 'Position in outline',
    prerequisite_item_bids VARCHAR(500) NOT NULL DEFAULT '' COMMENT 'Prerequisite outline item business identifiers',
    llm VARCHAR(100) NOT NULL DEFAULT '' COMMENT 'LLM model name',
    llm_temperature DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT 'LLM temperature parameter',
    llm_system_prompt TEXT NOT NULL DEFAULT '' COMMENT 'LLM system prompt',
    ask_enabled_status SMALLINT NOT NULL DEFAULT 5101 COMMENT 'Ask agent status: 5101=default, 5102=disabled, 5103=enabled',
    ask_llm VARCHAR(100) NOT NULL DEFAULT '' COMMENT 'Ask agent LLM model',
    ask_llm_temperature DECIMAL(10,2) NOT NULL DEFAULT 0.0 COMMENT 'Ask mode LLM temperature',
    ask_llm_system_prompt TEXT NOT NULL DEFAULT '' COMMENT 'Ask mode LLM system prompt',
    deleted SMALLINT NOT NULL DEFAULT 0 COMMENT 'Deletion flag: 0=active, 1=deleted',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Creation timestamp',
    created_user_bid VARCHAR(32) NOT NULL DEFAULT '' COMMENT 'Creator user business identifier',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Last update timestamp',
    updated_user_bid VARCHAR(32) NOT NULL DEFAULT '' COMMENT 'Last updater user business identifier',
    INDEX idx_outline_item_bid (outline_item_bid),
    INDEX idx_shifu_bid (shifu_bid),
    INDEX idx_parent_bid (parent_bid),
    INDEX idx_position (position),
    INDEX idx_deleted (deleted)
) COMMENT 'Shifu draft outline items';

-- 2.4 已发布大纲项表
CREATE TABLE shifu_published_outline_items (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    outline_item_bid VARCHAR(32) NOT NULL INDEX DEFAULT '' COMMENT 'Outline item business identifier',
    shifu_bid VARCHAR(32) NOT NULL INDEX DEFAULT '' COMMENT 'Shifu business identifier',
    title VARCHAR(100) NOT NULL DEFAULT '' COMMENT 'Outline item title',
    type SMALLINT NOT NULL DEFAULT 0 COMMENT 'Outline item type: 401=trial, 402=normal',
    hidden SMALLINT NOT NULL DEFAULT 0 COMMENT 'Hidden flag: 0=visible, 1=hidden',
    parent_bid VARCHAR(32) NOT NULL DEFAULT '' COMMENT 'Parent outline item business identifier',
    position VARCHAR(10) NOT NULL DEFAULT '' COMMENT 'Outline position',
    prerequisite_item_bids VARCHAR(500) NOT NULL DEFAULT '' COMMENT 'Prerequisite outline item business identifiers',
    llm VARCHAR(100) NOT NULL DEFAULT '' COMMENT 'LLM model name',
    llm_temperature DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT 'LLM temperature parameter',
    llm_system_prompt TEXT NOT NULL DEFAULT '' COMMENT 'LLM system prompt',
    ask_enabled_status SMALLINT NOT NULL DEFAULT 5101 COMMENT 'Ask agent status: 5101=default, 5102=disabled, 5103=enabled',
    ask_llm VARCHAR(100) NOT NULL DEFAULT '' COMMENT 'Ask agent LLM model',
    ask_llm_temperature DECIMAL(10,2) NOT NULL DEFAULT 0.0 COMMENT 'Ask agent LLM temperature',
    ask_llm_system_prompt TEXT NOT NULL DEFAULT '' COMMENT 'Ask agent LLM system prompt',
    deleted SMALLINT NOT NULL DEFAULT 0 COMMENT 'Deletion flag: 0=active, 1=deleted',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Creation timestamp',
    created_user_bid VARCHAR(32) NOT NULL INDEX DEFAULT '' COMMENT 'Creator user business identifier',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Last update timestamp',
    updated_user_bid VARCHAR(32) NOT NULL DEFAULT '' COMMENT 'Last updater user business identifier',
    INDEX idx_outline_item_bid (outline_item_bid),
    INDEX idx_shifu_bid (shifu_bid),
    INDEX idx_creator (created_user_bid),
    INDEX idx_deleted (deleted)
) COMMENT 'Shifu published outline items';

-- 2.5 草稿区块表
CREATE TABLE shifu_draft_blocks (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    block_bid VARCHAR(32) NOT NULL INDEX DEFAULT '' COMMENT 'Block business identifier',
    shifu_bid VARCHAR(32) NOT NULL INDEX DEFAULT '' COMMENT 'Shifu business identifier',
    outline_item_bid VARCHAR(32) NOT NULL INDEX DEFAULT '' COMMENT 'Outline item business identifier',
    type SMALLINT NOT NULL DEFAULT 0 COMMENT 'Block type',
    position SMALLINT NOT NULL INDEX DEFAULT 0 COMMENT 'Block position within outline',
    variable_bids VARCHAR(500) NOT NULL DEFAULT '' COMMENT 'Variable business identifiers used in block',
    resource_bids VARCHAR(500) NOT NULL DEFAULT '' COMMENT 'Resource business identifiers used in block',
    content TEXT NOT NULL DEFAULT '' COMMENT 'Block content',
    deleted SMALLINT NOT NULL DEFAULT 0 COMMENT 'Deletion flag: 0=active, 1=deleted',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Creation timestamp',
    created_user_bid VARCHAR(32) NOT NULL DEFAULT '' COMMENT 'Creator user business identifier',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Last update timestamp',
    updated_user_bid VARCHAR(32) NOT NULL DEFAULT '' COMMENT 'Last updater user business identifier',
    INDEX idx_block_bid (block_bid),
    INDEX idx_shifu_bid (shifu_bid),
    INDEX idx_outline_item_bid (outline_item_bid),
    INDEX idx_position (position),
    INDEX idx_deleted (deleted)
) COMMENT 'Shifu draft blocks';

-- 2.6 已发布区块表
CREATE TABLE shifu_published_blocks (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    block_bid VARCHAR(32) NOT NULL INDEX DEFAULT '' COMMENT 'Block business identifier',
    shifu_bid VARCHAR(32) NOT NULL INDEX DEFAULT '' COMMENT 'Shifu business identifier',
    outline_item_bid VARCHAR(32) NOT NULL INDEX DEFAULT '' COMMENT 'Outline item business identifier',
    type SMALLINT NOT NULL DEFAULT 0 COMMENT 'Block type',
    position SMALLINT NOT NULL DEFAULT 0 COMMENT 'Block position within outline',
    variable_bids VARCHAR(500) NOT NULL DEFAULT '' COMMENT 'Variable business identifiers used in block',
    resource_bids VARCHAR(500) NOT NULL DEFAULT '' COMMENT 'Resource business identifiers used in block',
    content TEXT NOT NULL DEFAULT '' COMMENT 'Block content',
    deleted SMALLINT NOT NULL DEFAULT 0 COMMENT 'Deletion flag: 0=active, 1=deleted',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Creation timestamp',
    created_user_bid VARCHAR(32) NOT NULL DEFAULT '' COMMENT 'Creator user business identifier',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Last update timestamp',
    updated_user_bid VARCHAR(32) NOT NULL DEFAULT '' COMMENT 'Last updater user business identifier',
    INDEX idx_block_bid (block_bid),
    INDEX idx_shifu_bid (shifu_bid),
    INDEX idx_outline_item_bid (outline_item_bid),
    INDEX idx_deleted (deleted)
) COMMENT 'Shifu published blocks';

-- 2.7 其他Shifu相关表
CREATE TABLE shifu_log_draft_structs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    struct_bid VARCHAR(32) NOT NULL INDEX UNIQUE DEFAULT '' COMMENT 'Content business identifier',
    shifu_bid VARCHAR(32) NOT NULL INDEX DEFAULT '' COMMENT 'Shifu business identifier',
    struct TEXT NOT NULL DEFAULT '' COMMENT 'JSON serialized shifu struct',
    deleted SMALLINT NOT NULL DEFAULT 0 COMMENT 'Deletion flag: 0=active, 1=deleted',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Creation timestamp',
    created_user_bid VARCHAR(32) NOT NULL DEFAULT '' COMMENT 'Creator user business identifier',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Last update timestamp',
    updated_user_bid VARCHAR(32) NOT NULL DEFAULT '' COMMENT 'Last updater user business identifier'
) COMMENT 'Shifu log draft structs';

CREATE TABLE shifu_log_published_structs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    struct_bid VARCHAR(32) NOT NULL INDEX UNIQUE DEFAULT '' COMMENT 'Content business identifier',
    shifu_bid VARCHAR(32) NOT NULL INDEX DEFAULT '' COMMENT 'Shifu business identifier',
    struct TEXT NOT NULL DEFAULT '' COMMENT 'JSON serialized struct of published shifu',
    deleted SMALLINT NOT NULL DEFAULT 0 COMMENT 'Deletion flag: 0=active, 1=deleted',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Creation timestamp',
    created_user_bid VARCHAR(32) NOT NULL DEFAULT '' COMMENT 'Creator user business identifier',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Last update timestamp',
    updated_user_bid VARCHAR(32) NOT NULL DEFAULT '' COMMENT 'Last updater user business identifier'
) COMMENT 'Shifu log published structs';

CREATE TABLE scenario_favorite (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    scenario_id VARCHAR(36) NOT NULL DEFAULT '' COMMENT 'Scenario UUID',
    user_id VARCHAR(36) NOT NULL DEFAULT '' COMMENT 'User UUID',
    status INTEGER NOT NULL DEFAULT 0 COMMENT 'Status',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Creation time',
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Update time'
) COMMENT 'Favorite scenario';

CREATE TABLE scenario_resource (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    resource_resource_id VARCHAR(36) NOT NULL DEFAULT '' INDEX COMMENT 'Resource UUID',
    scenario_id VARCHAR(36) NOT NULL DEFAULT '' INDEX COMMENT 'Scenario UUID',
    chapter_id VARCHAR(36) NOT NULL DEFAULT '' INDEX COMMENT 'Chapter UUID',
    resource_type INTEGER NOT NULL DEFAULT 0 COMMENT 'Resource type',
    resource_id VARCHAR(36) NOT NULL DEFAULT '' INDEX COMMENT 'Resource UUID',
    is_deleted INTEGER NOT NULL DEFAULT 0 COMMENT 'Is deleted',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Creation time'
) COMMENT 'Scenario resource';

CREATE TABLE ai_course_auth (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    course_auth_id VARCHAR(36) NOT NULL DEFAULT '' INDEX COMMENT 'course_auth_id UUID',
    course_id VARCHAR(36) NOT NULL DEFAULT '' COMMENT 'course_id UUID',
    user_id VARCHAR(36) NOT NULL DEFAULT '' COMMENT 'User UUID',
    auth_type VARCHAR(255) NOT NULL DEFAULT '[]' COMMENT 'auth_info',
    status INTEGER NOT NULL DEFAULT 0 COMMENT 'Status',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Creation time',
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Update time'
) COMMENT 'Ai course auth';

-- 3. 学习记录表
CREATE TABLE learn_progress_records (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    progress_record_bid VARCHAR(36) NOT NULL DEFAULT '' COMMENT 'Learn outline item business identifier',
    shifu_bid VARCHAR(36) NOT NULL DEFAULT '' COMMENT 'Shifu business identifier',
    outline_item_bid VARCHAR(36) NOT NULL DEFAULT '' COMMENT 'Outline business identifier',
    user_bid VARCHAR(36) NOT NULL DEFAULT '' COMMENT 'User business identifier',
    outline_item_updated INTEGER NOT NULL DEFAULT 0 COMMENT 'Outline is updated',
    status SMALLINT NOT NULL DEFAULT 605 COMMENT 'Status: 601=not started, 602=in progress, 603=completed, 604=refund, 605=locked, 606=unavailable, 607=branch, 608=reset',
    block_position INTEGER NOT NULL DEFAULT 0 COMMENT 'Block position index of the outlineitem',
    deleted SMALLINT NOT NULL DEFAULT 0 COMMENT 'Deletion flag: 0=active, 1=deleted',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Creation time',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Update time',
    INDEX idx_progress_record_bid (progress_record_bid),
    INDEX idx_shifu_bid (shifu_bid),
    INDEX idx_outline_item_bid (outline_item_bid),
    INDEX idx_user_bid (user_bid),
    INDEX idx_status (status),
    INDEX idx_deleted (deleted)
) COMMENT 'Learn progress records';

CREATE TABLE learn_generated_blocks (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    generated_block_bid VARCHAR(36) NOT NULL DEFAULT '' COMMENT 'Learn block log business identifier',
    progress_record_bid VARCHAR(36) NOT NULL DEFAULT '' COMMENT 'Learn outline item business identifier',
    user_bid VARCHAR(36) NOT NULL DEFAULT '' COMMENT 'User business identifier',
    block_bid VARCHAR(36) NOT NULL DEFAULT '' COMMENT 'Block business identifier',
    outline_item_bid VARCHAR(36) NOT NULL DEFAULT '' COMMENT 'Outline business identifier',
    shifu_bid VARCHAR(36) NOT NULL DEFAULT '' COMMENT 'Shifu business identifier',
    type INTEGER NOT NULL DEFAULT 0 COMMENT 'Block content type',
    role INTEGER NOT NULL DEFAULT 0 COMMENT 'Block role',
    generated_content TEXT NOT NULL DEFAULT '' COMMENT 'Block generate content',
    position INTEGER NOT NULL DEFAULT 0 COMMENT 'Block position index',
    block_content_conf TEXT NOT NULL DEFAULT '' COMMENT 'Block content config(used for re-generate)',
    liked INTEGER NOT NULL DEFAULT 0 COMMENT 'Interaction type: -1=disliked, 0=not available, 1=liked',
    deleted SMALLINT NOT NULL DEFAULT 0 COMMENT 'Deletion flag: 0=active, 1=deleted',
    status INTEGER NOT NULL DEFAULT 0 COMMENT 'Status of the record: 1=active, 0=history',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Creation time',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Update time',
    INDEX idx_generated_block_bid (generated_block_bid),
    INDEX idx_progress_record_bid (progress_record_bid),
    INDEX idx_user_bid (user_bid),
    INDEX idx_block_bid (block_bid),
    INDEX idx_outline_item_bid (outline_item_bid),
    INDEX idx_shifu_bid (shifu_bid),
    INDEX idx_deleted (deleted)
) COMMENT 'Learn generated blocks';

-- 4. 活动推广表
CREATE TABLE active (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    active_id VARCHAR(36) NOT NULL DEFAULT '' COMMENT 'Active UUID',
    active_name VARCHAR(255) NOT NULL DEFAULT '' COMMENT 'Active name',
    active_desc TEXT NOT NULL DEFAULT '' COMMENT 'Active description',
    active_type INTEGER NOT NULL DEFAULT 0 COMMENT 'Active type',
    active_join_type INTEGER NOT NULL DEFAULT 0 COMMENT 'Active join type',
    active_status INTEGER NOT NULL DEFAULT 0 COMMENT 'Active status',
    active_start_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Active start time',
    active_end_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Active end time',
    active_price DECIMAL(10,2) NOT NULL DEFAULT '0.00' COMMENT 'Active price',
    active_discount DECIMAL(10,2) NOT NULL DEFAULT '0.00' COMMENT 'Active discount',
    active_discount_type INTEGER NOT NULL DEFAULT 0 COMMENT 'Active discount type',
    active_discount_desc TEXT NOT NULL DEFAULT '' COMMENT 'Active discount description',
    active_filter TEXT NOT NULL DEFAULT '' COMMENT 'Active filter',
    active_course VARCHAR(36) NOT NULL DEFAULT '' COMMENT 'Active course',
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Creation time',
    updated TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Update time',
    INDEX idx_active_id (active_id),
    INDEX idx_active_status (active_status),
    INDEX idx_active_start_time (active_start_time),
    INDEX idx_active_end_time (active_end_time)
) COMMENT 'Active promotions';

CREATE TABLE active_user_record (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    record_id VARCHAR(36) NOT NULL DEFAULT '' COMMENT 'Record UUID',
    active_id VARCHAR(36) NOT NULL DEFAULT '' COMMENT 'Active UUID',
    active_name VARCHAR(255) NOT NULL DEFAULT '' COMMENT 'Active name',
    user_id VARCHAR(36) NOT NULL DEFAULT '' COMMENT 'User UUID',
    price DECIMAL(10,2) NOT NULL DEFAULT '0.00' COMMENT 'Price of the active',
    order_id VARCHAR(36) NOT NULL DEFAULT '' COMMENT 'Order UUID',
    status INTEGER NOT NULL DEFAULT 0 COMMENT 'Status of the record',
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Creation time',
    updated TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Update time',
    INDEX idx_record_id (record_id),
    INDEX idx_active_id (active_id),
    INDEX idx_user_id (user_id),
    INDEX idx_order_id (order_id)
) COMMENT 'Active user records';

-- 5. 优惠券表
CREATE TABLE promo_coupons (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    coupon_bid VARCHAR(36) NOT NULL DEFAULT '' COMMENT 'Coupon business identifier',
    code VARCHAR(36) NOT NULL DEFAULT '' COMMENT 'Coupon code',
    discount_type SMALLINT NOT NULL DEFAULT 701 COMMENT 'Coupon type: 701=fixed, 702=percent',
    usage_type SMALLINT NOT NULL DEFAULT 801 COMMENT 'Coupon apply type: 801=one coupon code for multiple times, 802=one coupon code for one time',
    value DECIMAL(10,2) NOT NULL DEFAULT '0.00' COMMENT 'Coupon value: would be calculated to amount by coupon type',
    start DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Coupon start time',
    end DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Coupon end time',
    channel VARCHAR(36) NOT NULL DEFAULT '' COMMENT 'Coupon channel',
    filter TEXT NOT NULL COMMENT 'Coupon filter: would be used to filter user and shifu',
    total_count BIGINT NOT NULL DEFAULT 0 COMMENT 'Coupon total count',
    used_count BIGINT NOT NULL DEFAULT 0 COMMENT 'Coupon used count',
    status SMALLINT NOT NULL DEFAULT 0 COMMENT 'Status of the discount: 0=inactive, 1=active',
    deleted SMALLINT NOT NULL DEFAULT 0 COMMENT 'Deletion flag: 0=active, 1=deleted',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Creation timestamp',
    created_user_bid VARCHAR(36) NOT NULL DEFAULT '' COMMENT 'Creator user business identifier',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Update timestamp',
    INDEX idx_coupon_bid (coupon_bid),
    INDEX idx_code (code),
    INDEX idx_deleted (deleted)
) COMMENT 'Promo coupons';

CREATE TABLE promo_coupon_usages (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    coupon_usage_bid VARCHAR(36) NOT NULL DEFAULT '' COMMENT 'Coupon usage business identifier',
    coupon_bid VARCHAR(36) NOT NULL DEFAULT '' COMMENT 'Coupon business identifier',
    name VARCHAR(255) NOT NULL DEFAULT '' COMMENT 'Coupon name',
    user_bid VARCHAR(36) NOT NULL DEFAULT '' COMMENT 'User business identifier',
    shifu_bid VARCHAR(36) NOT NULL DEFAULT '' COMMENT 'Shifu business identifier',
    order_bid VARCHAR(36) NOT NULL DEFAULT '' COMMENT 'Order business identifier',
    code VARCHAR(36) NOT NULL DEFAULT '' COMMENT 'Coupon code',
    discount_type SMALLINT NOT NULL DEFAULT 701 COMMENT 'Coupon Type: 701=fixed, 702=percent',
    value DECIMAL(10,2) NOT NULL DEFAULT '0.00' COMMENT 'Coupon value: would be calculated to amount by coupon type',
    status SMALLINT NOT NULL DEFAULT 902 COMMENT 'Status of the record: 901=inactive, 902=active, 903=used, 904=timeout',
    deleted SMALLINT NOT NULL DEFAULT 0 COMMENT 'Deletion flag: 0=active, 1=deleted',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Creation timestamp',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Update timestamp',
    INDEX idx_coupon_usage_bid (coupon_usage_bid),
    INDEX idx_coupon_bid (coupon_bid),
    INDEX idx_user_bid (user_bid),
    INDEX idx_shifu_bid (shifu_bid),
    INDEX idx_order_bid (order_bid),
    INDEX idx_deleted (deleted)
) COMMENT 'Promo coupon usages';

-- 6. 租户配置表（每个租户独有的配置）
CREATE TABLE tenant_config (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    config_key VARCHAR(100) NOT NULL INDEX COMMENT '配置键',
    config_value TEXT COMMENT '配置值',
    config_type VARCHAR(20) DEFAULT 'string' COMMENT '配置类型',
    description VARCHAR(200) COMMENT '配置描述',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_config_key (config_key)
) COMMENT '租户配置表';

-- 7. 租户级别的统计表
CREATE TABLE tenant_statistics (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    stat_date DATE NOT NULL COMMENT '统计日期',
    total_users INT DEFAULT 0 COMMENT '总用户数',
    active_users INT DEFAULT 0 COMMENT '活跃用户数',
    total_orders INT DEFAULT 0 COMMENT '总订单数',
    total_revenue DECIMAL(12,2) DEFAULT 0.00 COMMENT '总收入',
    total_study_records INT DEFAULT 0 COMMENT '总学习记录数',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_stat_date (stat_date),
    INDEX idx_date (stat_date)
) COMMENT '租户统计表';

-- 插入默认租户配置
INSERT INTO tenant_config (config_key, config_value, config_type, description) VALUES
('tenant.name', '默认租户', 'string', '租户名称'),
('tenant.logo_url', '', 'string', '租户Logo URL'),
('tenant.theme_color', '#1890ff', 'string', '租户主题色'),
('tenant.contact_email', '', 'string', '联系邮箱'),
('features.payment_enabled', 'true', 'boolean', '是否启用支付功能'),
('features.study_tracking', 'true', 'boolean', '是否启用学习跟踪');
```

## 3. 数据库路由设计

### 3.1 连接池管理

```python
# 数据库连接管理器
from typing import Dict, Optional
import pymysql
from sqlalchemy import create_engine, pool
from sqlalchemy.orm import sessionmaker
import threading
import redis
from cryptography.fernet import Fernet

class DatabaseManager:
    """数据库连接管理器 - SaaS 1.0版本"""

    def __init__(self, system_db_url: str, redis_url: str, encryption_key: str):
        self.system_db_url = system_db_url
        self.redis_client = redis.Redis.from_url(redis_url)
        self.cipher_suite = Fernet(encryption_key.encode())

        # 系统库连接（固定）
        self.system_engine = create_engine(
            system_db_url,
            poolclass=pool.QueuePool,
            pool_size=20,
            max_overflow=30,
            pool_recycle=3600,
            echo=False
        )
        self.SystemSession = sessionmaker(bind=self.system_engine)

        # 租户数据库连接池缓存
        self.tenant_engines: Dict[str, any] = {}
        self.tenant_sessions: Dict[str, any] = {}
        self._lock = threading.RLock()

        # 预加载租户连接配置
        self._load_tenant_connections()

    def get_system_session(self):
        """获取系统库会话"""
        return self.SystemSession()

    def get_tenant_session(self, tenant_id: str):
        """获取租户数据库会话"""
        if tenant_id not in self.tenant_sessions:
            self._create_tenant_connection(tenant_id)

        if tenant_id in self.tenant_sessions:
            return self.tenant_sessions[tenant_id]()
        else:
            raise Exception(f"无法创建租户 {tenant_id} 的数据库连接")

    def _load_tenant_connections(self):
        """预加载所有活跃租户的数据库连接"""
        try:
            system_session = self.get_system_session()

            # 查询所有活跃租户的数据库配置
            tenants_query = """
                SELECT t.tenant_id, td.db_host, td.db_port, td.db_name,
                       td.db_username, td.db_password_encrypted, td.max_connections
                FROM saas_tenants t
                JOIN saas_tenant_databases td ON t.tenant_id = td.tenant_id
                WHERE t.status = 1 AND td.is_active = 1
            """

            result = system_session.execute(tenants_query)

            for row in result:
                tenant_id, db_host, db_port, db_name, db_username, encrypted_password, max_connections = row

                # 解密数据库密码
                db_password = self.cipher_suite.decrypt(encrypted_password.encode()).decode()

                # 创建租户数据库连接
                self._create_tenant_connection_with_config(
                    tenant_id, db_host, db_port, db_name,
                    db_username, db_password, max_connections or 20
                )

            system_session.close()

        except Exception as e:
            print(f"加载租户数据库连接失败: {str(e)}")

    def _create_tenant_connection(self, tenant_id: str):
        """为指定租户创建数据库连接"""
        with self._lock:
            if tenant_id in self.tenant_sessions:
                return

            try:
                system_session = self.get_system_session()

                # 查询租户数据库配置
                config_query = """
                    SELECT td.db_host, td.db_port, td.db_name,
                           td.db_username, td.db_password_encrypted, td.max_connections
                    FROM saas_tenants t
                    JOIN saas_tenant_databases td ON t.tenant_id = td.tenant_id
                    WHERE t.tenant_id = %s AND t.status = 1 AND td.is_active = 1
                """

                result = system_session.execute(config_query, (tenant_id,))
                row = result.fetchone()

                if not row:
                    system_session.close()
                    raise Exception(f"租户 {tenant_id} 的数据库配置不存在或未激活")

                db_host, db_port, db_name, db_username, encrypted_password, max_connections = row

                # 解密密码
                db_password = self.cipher_suite.decrypt(encrypted_password.encode()).decode()

                # 创建连接
                self._create_tenant_connection_with_config(
                    tenant_id, db_host, db_port, db_name,
                    db_username, db_password, max_connections or 20
                )

                system_session.close()

            except Exception as e:
                raise Exception(f"创建租户 {tenant_id} 数据库连接失败: {str(e)}")

    def _create_tenant_connection_with_config(self, tenant_id: str, db_host: str,
                                            db_port: int, db_name: str,
                                            db_username: str, db_password: str,
                                            max_connections: int):
        """使用指定配置创建租户数据库连接"""

        # 构建连接URL
        db_url = f"mysql+pymysql://{db_username}:{db_password}@{db_host}:{db_port}/{db_name}?charset=utf8mb4"

        # 创建引擎
        engine = create_engine(
            db_url,
            poolclass=pool.QueuePool,
            pool_size=min(max_connections, 50),
            max_overflow=10,
            pool_recycle=3600,
            echo=False
        )

        # 创建会话工厂
        SessionFactory = sessionmaker(bind=engine)

        # 缓存连接
        self.tenant_engines[tenant_id] = engine
        self.tenant_sessions[tenant_id] = SessionFactory

        print(f"已创建租户 {tenant_id} 的数据库连接")

    def refresh_tenant_connection(self, tenant_id: str):
        """刷新租户数据库连接（当配置发生变化时）"""
        with self._lock:
            # 关闭现有连接
            if tenant_id in self.tenant_engines:
                self.tenant_engines[tenant_id].dispose()
                del self.tenant_engines[tenant_id]

            if tenant_id in self.tenant_sessions:
                del self.tenant_sessions[tenant_id]

        # 重新创建连接
        self._create_tenant_connection(tenant_id)

    def get_tenant_database_info(self, tenant_id: str) -> Optional[Dict]:
        """获取租户数据库信息"""
        try:
            # 先从Redis缓存获取
            cache_key = f"tenant_db_info:{tenant_id}"
            cached_info = self.redis_client.get(cache_key)

            if cached_info:
                import json
                return json.loads(cached_info)

            # 从数据库查询
            system_session = self.get_system_session()

            query = """
                SELECT t.tenant_id, t.tenant_name, t.tenant_domain, t.database_name,
                       td.db_host, td.db_port, td.db_name, td.max_connections
                FROM saas_tenants t
                JOIN saas_tenant_databases td ON t.tenant_id = td.tenant_id
                WHERE t.tenant_id = %s AND t.status = 1
            """

            result = system_session.execute(query, (tenant_id,))
            row = result.fetchone()
            system_session.close()

            if row:
                info = {
                    'tenant_id': row[0],
                    'tenant_name': row[1],
                    'tenant_domain': row[2],
                    'database_name': row[3],
                    'db_host': row[4],
                    'db_port': row[5],
                    'db_name': row[6],
                    'max_connections': row[7]
                }

                # 缓存5分钟
                self.redis_client.setex(cache_key, 300, json.dumps(info))
                return info

            return None

        except Exception as e:
            print(f"获取租户 {tenant_id} 数据库信息失败: {str(e)}")
            return None

# 全局数据库管理器实例
db_manager = None

def init_database_manager(system_db_url: str, redis_url: str, encryption_key: str):
    """初始化数据库管理器"""
    global db_manager
    db_manager = DatabaseManager(system_db_url, redis_url, encryption_key)
    return db_manager

def get_db_manager() -> DatabaseManager:
    """获取数据库管理器实例"""
    global db_manager
    if not db_manager:
        raise Exception("数据库管理器未初始化")
    return db_manager
```

### 3.2 域名路由解析

```python
# 租户路由解析器
from typing import Optional, Dict
from urllib.parse import urlparse
import re

class TenantRouter:
    """租户路由解析器 - SaaS 1.0版本"""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.domain_tenant_cache = {}  # 域名到租户的映射缓存

    def resolve_tenant_from_request(self, request) -> Optional[str]:
        """从请求中解析租户ID"""

        # 1. 优先从Header获取
        tenant_id = self._get_tenant_from_header(request)
        if tenant_id:
            return tenant_id

        # 2. 从域名解析
        tenant_id = self._get_tenant_from_domain(request)
        if tenant_id:
            return tenant_id

        # 3. 从子域名解析
        tenant_id = self._get_tenant_from_subdomain(request)
        if tenant_id:
            return tenant_id

        # 4. 默认租户
        return 'default'

    def _get_tenant_from_header(self, request) -> Optional[str]:
        """从HTTP Header获取租户ID"""
        return request.headers.get('X-Tenant-ID') or request.headers.get('Tenant-ID')

    def _get_tenant_from_domain(self, request) -> Optional[str]:
        """从完整域名获取租户ID"""
        host = request.headers.get('Host', '')
        if not host:
            return None

        # 从缓存获取
        if host in self.domain_tenant_cache:
            return self.domain_tenant_cache[host]

        # 从数据库查询
        try:
            system_session = self.db_manager.get_system_session()

            query = """
                SELECT tenant_id FROM saas_tenants
                WHERE tenant_domain = %s AND status = 1 AND deleted = 0
            """

            result = system_session.execute(query, (host,))
            row = result.fetchone()
            system_session.close()

            if row:
                tenant_id = row[0]
                # 缓存结果
                self.domain_tenant_cache[host] = tenant_id
                return tenant_id

        except Exception as e:
            print(f"域名解析租户失败: {str(e)}")

        return None

    def _get_tenant_from_subdomain(self, request) -> Optional[str]:
        """从子域名获取租户ID"""
        host = request.headers.get('Host', '')
        if not host or '.' not in host:
            return None

        # 提取子域名
        parts = host.split('.')
        if len(parts) < 3:  # 至少需要 subdomain.domain.com
            return None

        subdomain = parts[0]

        # 跳过常见的系统子域名
        if subdomain in ['www', 'api', 'admin', 'cdn', 'static']:
            return None

        # 验证子域名格式（租户ID格式）
        if not re.match(r'^[a-z0-9][a-z0-9-]*[a-z0-9]$', subdomain):
            return None

        # 验证租户是否存在
        if self._validate_tenant_exists(subdomain):
            return subdomain

        return None

    def _validate_tenant_exists(self, tenant_id: str) -> bool:
        """验证租户是否存在"""
        try:
            system_session = self.db_manager.get_system_session()

            query = """
                SELECT 1 FROM saas_tenants
                WHERE tenant_id = %s AND status = 1 AND deleted = 0
            """

            result = system_session.execute(query, (tenant_id,))
            exists = result.fetchone() is not None
            system_session.close()

            return exists

        except Exception as e:
            print(f"验证租户存在性失败: {str(e)}")
            return False

    def get_tenant_info(self, tenant_id: str) -> Optional[Dict]:
        """获取租户详细信息"""
        return self.db_manager.get_tenant_database_info(tenant_id)

    def register_tenant_domain(self, tenant_id: str, domain: str) -> bool:
        """注册租户域名"""
        try:
            system_session = self.db_manager.get_system_session()

            # 更新租户域名
            update_query = """
                UPDATE saas_tenants
                SET tenant_domain = %s, updated_at = CURRENT_TIMESTAMP
                WHERE tenant_id = %s AND deleted = 0
            """

            result = system_session.execute(update_query, (domain, tenant_id))
            system_session.commit()

            if result.rowcount > 0:
                # 清除缓存
                if domain in self.domain_tenant_cache:
                    del self.domain_tenant_cache[domain]

                system_session.close()
                return True

            system_session.close()
            return False

        except Exception as e:
            print(f"注册租户域名失败: {str(e)}")
            return False
```

## 4. 应用层适配设计

### 4.1 Flask集成

```python
# Flask应用适配器
from flask import Flask, request, g, jsonify
from functools import wraps

class SaaSFlaskApp:
    """SaaS版本Flask应用包装器"""

    def __init__(self, app: Flask, db_manager: DatabaseManager):
        self.app = app
        self.db_manager = db_manager
        self.tenant_router = TenantRouter(db_manager)

        # 注册请求处理中间件
        self._setup_request_middleware()

    def _setup_request_middleware(self):
        """设置请求处理中间件"""

        @self.app.before_request
        def before_request():
            # 解析租户
            tenant_id = self.tenant_router.resolve_tenant_from_request(request)
            g.tenant_id = tenant_id

            # 获取租户信息
            g.tenant_info = self.tenant_router.get_tenant_info(tenant_id)

            # 设置数据库会话
            g.system_session = self.db_manager.get_system_session()

            try:
                g.tenant_session = self.db_manager.get_tenant_session(tenant_id)
            except Exception as e:
                # 租户数据库连接失败，返回错误
                return jsonify({
                    'error': 'tenant_unavailable',
                    'message': f'租户 {tenant_id} 服务不可用'
                }), 503

        @self.app.teardown_request
        def teardown_request(exception=None):
            # 关闭数据库会话
            if hasattr(g, 'system_session'):
                g.system_session.close()

            if hasattr(g, 'tenant_session'):
                g.tenant_session.close()

        @self.app.errorhandler(404)
        def handle_tenant_not_found(e):
            return jsonify({
                'error': 'not_found',
                'message': '请求的资源不存在',
                'tenant_id': getattr(g, 'tenant_id', None)
            }), 404

def require_tenant(f):
    """装饰器：要求有效的租户上下文"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(g, 'tenant_id') or not g.tenant_id:
            return jsonify({
                'error': 'tenant_required',
                'message': '需要有效的租户上下文'
            }), 400

        if not hasattr(g, 'tenant_session') or not g.tenant_session:
            return jsonify({
                'error': 'tenant_unavailable',
                'message': '租户服务不可用'
            }), 503

        return f(*args, **kwargs)

    return decorated_function

def system_only(f):
    """装饰器：仅系统管理接口"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 验证是否为系统管理请求
        admin_token = request.headers.get('X-Admin-Token')
        if not admin_token or not validate_admin_token(admin_token):
            return jsonify({
                'error': 'admin_required',
                'message': '需要系统管理员权限'
            }), 403

        return f(*args, **kwargs)

    return decorated_function

def validate_admin_token(token: str) -> bool:
    """验证系统管理员token"""
    # 实现token验证逻辑
    return True  # 简化实现

# 使用示例
def create_saas_app(system_db_url: str, redis_url: str, encryption_key: str) -> Flask:
    """创建SaaS版本的Flask应用"""
    app = Flask(__name__)

    # 初始化数据库管理器
    db_manager = init_database_manager(system_db_url, redis_url, encryption_key)

    # 创建SaaS应用包装器
    saas_app = SaaSFlaskApp(app, db_manager)

    # 注册路由
    register_routes(app)

    return app

def register_routes(app: Flask):
    """注册路由"""

    # 租户业务接口
    @app.route('/api/orders', methods=['GET'])
    @require_tenant
    def get_orders():
        """获取订单列表（租户隔离）"""
        tenant_session = g.tenant_session

        # 查询当前租户的订单
        orders = tenant_session.execute("""
            SELECT order_bid, shifu_bid, user_id, payable_price, paid_price, status, created_at
            FROM order_orders
            WHERE deleted = 0
            ORDER BY created_at DESC
        """).fetchall()

        return jsonify({
            'tenant_id': g.tenant_id,
            'orders': [dict(order) for order in orders]
        })

    @app.route('/api/users/<user_id>/orders', methods=['GET'])
    @require_tenant
    def get_user_orders(user_id):
        """获取用户订单（跨库关联）"""
        system_session = g.system_session
        tenant_session = g.tenant_session

        # 从系统库验证用户
        user = system_session.execute("""
            SELECT user_id, username, name, email FROM user_info
            WHERE user_id = %s
        """, (user_id,)).fetchone()

        if not user:
            return jsonify({'error': 'user_not_found'}), 404

        # 验证用户是否属于当前租户
        tenant_user = system_session.execute("""
            SELECT role FROM saas_tenant_users
            WHERE tenant_id = %s AND user_id = %s AND deleted = 0 AND status = 1
        """, (g.tenant_id, user_id)).fetchone()

        if not tenant_user:
            return jsonify({'error': 'user_not_in_tenant'}), 403

        # 从租户库获取订单
        orders = tenant_session.execute("""
            SELECT order_bid, shifu_bid, payable_price, paid_price, status, created_at
            FROM order_orders
            WHERE user_id = %s AND deleted = 0
            ORDER BY created_at DESC
        """, (user_id,)).fetchall()

        return jsonify({
            'tenant_id': g.tenant_id,
            'user': dict(user),
            'role': tenant_user[0],
            'orders': [dict(order) for order in orders]
        })

    # 系统管理接口
    @app.route('/admin/tenants', methods=['GET'])
    @system_only
    def list_tenants():
        """列出所有租户（系统管理）"""
        system_session = g.system_session

        tenants = system_session.execute("""
            SELECT t.tenant_id, t.tenant_name, t.tenant_domain, t.status,
                   t.plan_type, t.created_at,
                   td.db_host, td.db_name, td.max_connections
            FROM saas_tenants t
            LEFT JOIN saas_tenant_databases td ON t.tenant_id = td.tenant_id
            WHERE t.deleted = 0
            ORDER BY t.created_at DESC
        """).fetchall()

        return jsonify({
            'tenants': [dict(tenant) for tenant in tenants]
        })

    @app.route('/admin/tenants/<tenant_id>/stats', methods=['GET'])
    @system_only
    def get_tenant_stats(tenant_id):
        """获取租户统计信息（系统管理）"""
        try:
            tenant_session = db_manager.get_tenant_session(tenant_id)

            # 获取租户统计数据
            stats = tenant_session.execute("""
                SELECT
                    COUNT(DISTINCT user_id) as total_users,
                    COUNT(DISTINCT CASE WHEN status IN (502) THEN order_bid END) as paid_orders,
                    SUM(CASE WHEN status IN (502) THEN paid_price ELSE 0 END) as total_revenue,
                    COUNT(DISTINCT sr.record_bid) as total_study_records
                FROM order_orders o
                LEFT JOIN study_records sr ON o.user_id = sr.user_id
                WHERE o.deleted = 0
            """).fetchone()

            tenant_session.close()

            return jsonify({
                'tenant_id': tenant_id,
                'stats': dict(stats) if stats else {}
            })

        except Exception as e:
            return jsonify({
                'error': 'tenant_stats_error',
                'message': str(e)
            }), 500
```

## 5. 数据迁移策略

### 5.1 现有数据迁移方案

```python
# 数据迁移脚本
import pymysql
from typing import Dict, List
import logging
from datetime import datetime

class SaaSV1DataMigrator:
    """SaaS 1.0 数据迁移器"""

    def __init__(self, legacy_db_config: Dict, system_db_config: Dict):
        self.legacy_db = legacy_db_config  # 现有数据库配置
        self.system_db = system_db_config  # 新系统库配置
        self.logger = logging.getLogger(__name__)

    def execute_migration(self) -> bool:
        """执行完整的数据迁移"""
        try:
            self.logger.info("开始SaaS 1.0数据迁移")

            # 第1步：创建系统库和默认租户库
            self._create_system_database()
            self._create_default_tenant_database()

            # 第2步：迁移用户数据到系统库
            self._migrate_user_data()

            # 第3步：迁移业务数据到默认租户库
            self._migrate_business_data()

            # 第4步：建立用户-租户关联
            self._create_user_tenant_associations()

            # 第5步：验证迁移结果
            migration_valid = self._validate_migration()

            if migration_valid:
                self.logger.info("数据迁移完成")
                return True
            else:
                self.logger.error("数据迁移验证失败")
                return False

        except Exception as e:
            self.logger.error(f"数据迁移失败: {str(e)}")
            return False

    def _create_system_database(self):
        """创建系统库结构"""
        self.logger.info("创建系统库结构")

        with self._get_connection(self.system_db) as conn:
            cursor = conn.cursor()

            # 读取并执行系统库SQL脚本
            system_sql_script = self._read_sql_file('system_database_schema.sql')

            # 分别执行每个SQL语句
            statements = system_sql_script.split(';')
            for statement in statements:
                if statement.strip():
                    cursor.execute(statement)

            conn.commit()

    def _create_default_tenant_database(self):
        """创建默认租户库"""
        self.logger.info("创建默认租户数据库")

        # 创建数据库
        with self._get_connection(self.system_db) as conn:
            cursor = conn.cursor()
            cursor.execute("CREATE DATABASE IF NOT EXISTS ai_shifu_tenant_default CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            conn.commit()

        # 创建表结构
        default_tenant_config = self.system_db.copy()
        default_tenant_config['database'] = 'ai_shifu_tenant_default'

        with self._get_connection(default_tenant_config) as conn:
            cursor = conn.cursor()

            tenant_sql_script = self._read_sql_file('tenant_database_schema.sql')
            statements = tenant_sql_script.split(';')

            for statement in statements:
                if statement.strip():
                    cursor.execute(statement)

            conn.commit()

    def _migrate_user_data(self):
        """迁移用户数据到系统库"""
        self.logger.info("迁移用户数据到系统库")

        # 获取原始用户数据
        with self._get_connection(self.legacy_db) as legacy_conn:
            cursor = legacy_conn.cursor(pymysql.cursors.DictCursor)

            # 迁移user_info表
            cursor.execute("""
                SELECT id, user_id, username, name, email, mobile, created, updated,
                       user_state, user_sex, user_birth, user_avatar, user_open_id,
                       user_unicon_id, user_language, is_admin, is_creator, extra_data
                FROM user_info
                WHERE user_id IS NOT NULL AND user_id != ''
            """)

            users = cursor.fetchall()

            # 迁移到系统库
            with self._get_connection(self.system_db) as system_conn:
                system_cursor = system_conn.cursor()

                for user in users:
                    system_cursor.execute("""
                        INSERT INTO user_info (
                            id, user_id, username, name, email, mobile, created, updated,
                            user_state, user_sex, user_birth, user_avatar, user_open_id,
                            user_unicon_id, user_language, is_admin, is_creator, extra_data
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        )
                    """, (
                        user['id'], user['user_id'], user['username'], user['name'],
                        user['email'], user['mobile'], user['created'], user['updated'],
                        user['user_state'], user['user_sex'], user['user_birth'],
                        user['user_avatar'], user['user_open_id'], user['user_unicon_id'],
                        user['user_language'], user['is_admin'], user['is_creator'], user['extra_data']
                    ))

                system_conn.commit()
                self.logger.info(f"迁移了 {len(users)} 个用户")

            # 迁移其他用户相关表
            self._migrate_user_tokens(legacy_conn)
            self._migrate_user_verify_codes(legacy_conn)
            self._migrate_user_conversions(legacy_conn)

    def _migrate_business_data(self):
        """迁移业务数据到默认租户库"""
        self.logger.info("迁移业务数据到默认租户库")

        default_tenant_config = self.system_db.copy()
        default_tenant_config['database'] = 'ai_shifu_tenant_default'

        with self._get_connection(self.legacy_db) as legacy_conn:

            # 迁移订单数据
            self._migrate_orders_data(legacy_conn, default_tenant_config)

            # 迁移Shifu数据
            self._migrate_shifu_data(legacy_conn, default_tenant_config)

            # 迁移学习记录
            self._migrate_study_records(legacy_conn, default_tenant_config)

            # 迁移活动数据
            self._migrate_active_data(legacy_conn, default_tenant_config)

            # 迁移优惠券数据
            self._migrate_coupon_data(legacy_conn, default_tenant_config)

    def _migrate_orders_data(self, legacy_conn, tenant_config):
        """迁移订单数据"""
        cursor = legacy_conn.cursor(pymysql.cursors.DictCursor)

        # 迁移order_orders表
        cursor.execute("""
            SELECT id, order_bid, shifu_bid, user_bid as user_id, payable_price,
                   paid_price, status, deleted, created_at, updated_at
            FROM order_orders
        """)
        orders = cursor.fetchall()

        with self._get_connection(tenant_config) as tenant_conn:
            tenant_cursor = tenant_conn.cursor()

            for order in orders:
                tenant_cursor.execute("""
                    INSERT INTO order_orders (
                        id, order_bid, shifu_bid, user_id, payable_price,
                        paid_price, status, deleted, created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    order['id'], order['order_bid'], order['shifu_bid'], order['user_id'],
                    order['payable_price'], order['paid_price'], order['status'],
                    order['deleted'], order['created_at'], order['updated_at']
                ))

            tenant_conn.commit()
            self.logger.info(f"迁移了 {len(orders)} 个订单")

        # 迁移order_pingxx_orders表
        cursor.execute("""
            SELECT id, pingxx_order_bid, user_bid as user_id, shifu_bid, order_bid,
                   transaction_no, app_id, channel, amount, currency, subject, body,
                   client_ip, extra, status, charge_id, paid_at, refunded_at, closed_at,
                   failed_at, refund_id, failure_code, failure_msg, charge_object,
                   deleted, created_at, updated_at
            FROM order_pingxx_orders
        """)
        pingxx_orders = cursor.fetchall()

        with self._get_connection(tenant_config) as tenant_conn:
            tenant_cursor = tenant_conn.cursor()

            for order in pingxx_orders:
                tenant_cursor.execute("""
                    INSERT INTO order_pingxx_orders (
                        id, pingxx_order_bid, user_id, shifu_bid, order_bid, transaction_no,
                        app_id, channel, amount, currency, subject, body, client_ip, extra,
                        status, charge_id, paid_at, refunded_at, closed_at, failed_at,
                        refund_id, failure_code, failure_msg, charge_object, deleted,
                        created_at, updated_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                """, (
                    order['id'], order['pingxx_order_bid'], order['user_id'],
                    order['shifu_bid'], order['order_bid'], order['transaction_no'],
                    order['app_id'], order['channel'], order['amount'], order['currency'],
                    order['subject'], order['body'], order['client_ip'], order['extra'],
                    order['status'], order['charge_id'], order['paid_at'],
                    order['refunded_at'], order['closed_at'], order['failed_at'],
                    order['refund_id'], order['failure_code'], order['failure_msg'],
                    order['charge_object'], order['deleted'], order['created_at'],
                    order['updated_at']
                ))

            tenant_conn.commit()
            self.logger.info(f"迁移了 {len(pingxx_orders)} 个Pingxx订单")

    def _migrate_shifu_data(self, legacy_conn, tenant_config):
        """迁移Shifu数据"""
        cursor = legacy_conn.cursor(pymysql.cursors.DictCursor)

        # 迁移所有Shifu相关表（这里简化处理，实际需要按照模型文件中的表结构）
        shifu_tables = [
            'shifu_draft_shifus', 'shifu_published_shifus', 'shifu_outline_items',
            'shifu_blocks', 'shifu_scenarios', 'shifu_block_groups', 'shifu_block_units',
            'shifu_block_subunits', 'shifu_ai_course_auth'
        ]

        with self._get_connection(tenant_config) as tenant_conn:
            tenant_cursor = tenant_conn.cursor()

            for table_name in shifu_tables:
                try:
                    # 查询现有数据
                    cursor.execute(f"SELECT * FROM {table_name}")
                    records = cursor.fetchall()

                    if records:
                        # 构建插入语句（简化处理）
                        columns = list(records[0].keys())
                        placeholders = ', '.join(['%s'] * len(columns))
                        columns_str = ', '.join(columns)

                        for record in records:
                            tenant_cursor.execute(f"""
                                INSERT INTO {table_name} ({columns_str})
                                VALUES ({placeholders})
                            """, tuple(record.values()))

                        tenant_conn.commit()
                        self.logger.info(f"迁移了 {len(records)} 条 {table_name} 记录")

                except Exception as e:
                    self.logger.warning(f"迁移表 {table_name} 失败: {str(e)}")

    def _migrate_study_records(self, legacy_conn, tenant_config):
        """迁移学习记录"""
        cursor = legacy_conn.cursor(pymysql.cursors.DictCursor)

        # 迁移学习进度记录
        cursor.execute("SELECT * FROM learn_progress_records")
        progress_records = cursor.fetchall()

        # 迁移生成的学习块
        cursor.execute("SELECT * FROM learn_generated_blocks")
        generated_blocks = cursor.fetchall()

        with self._get_connection(tenant_config) as tenant_conn:
            tenant_cursor = tenant_conn.cursor()

            # 迁移进度记录
            for record in progress_records:
                columns = list(record.keys())
                placeholders = ', '.join(['%s'] * len(columns))
                columns_str = ', '.join(columns)

                tenant_cursor.execute(f"""
                    INSERT INTO learn_progress_records ({columns_str})
                    VALUES ({placeholders})
                """, tuple(record.values()))

            # 迁移生成的块
            for block in generated_blocks:
                columns = list(block.keys())
                placeholders = ', '.join(['%s'] * len(columns))
                columns_str = ', '.join(columns)

                tenant_cursor.execute(f"""
                    INSERT INTO learn_generated_blocks ({columns_str})
                    VALUES ({placeholders})
                """, tuple(block.values()))

            tenant_conn.commit()
            self.logger.info(f"迁移了 {len(progress_records)} 条进度记录和 {len(generated_blocks)} 个生成块")

    def _migrate_active_data(self, legacy_conn, tenant_config):
        """迁移活动数据"""
        cursor = legacy_conn.cursor(pymysql.cursors.DictCursor)

        # 迁移活动表
        cursor.execute("SELECT * FROM active")
        activities = cursor.fetchall()

        # 迁移活动用户记录
        cursor.execute("SELECT * FROM active_user_record")
        user_records = cursor.fetchall()

        with self._get_connection(tenant_config) as tenant_conn:
            tenant_cursor = tenant_conn.cursor()

            # 迁移活动
            for activity in activities:
                columns = list(activity.keys())
                placeholders = ', '.join(['%s'] * len(columns))
                columns_str = ', '.join(columns)

                tenant_cursor.execute(f"""
                    INSERT INTO active ({columns_str})
                    VALUES ({placeholders})
                """, tuple(activity.values()))

            # 迁移用户记录
            for record in user_records:
                columns = list(record.keys())
                placeholders = ', '.join(['%s'] * len(columns))
                columns_str = ', '.join(columns)

                tenant_cursor.execute(f"""
                    INSERT INTO active_user_record ({columns_str})
                    VALUES ({placeholders})
                """, tuple(record.values()))

            tenant_conn.commit()
            self.logger.info(f"迁移了 {len(activities)} 个活动和 {len(user_records)} 条用户记录")

    def _migrate_coupon_data(self, legacy_conn, tenant_config):
        """迁移优惠券数据"""
        cursor = legacy_conn.cursor(pymysql.cursors.DictCursor)

        # 迁移优惠券表
        cursor.execute("SELECT * FROM promo_coupons")
        coupons = cursor.fetchall()

        # 迁移优惠券使用记录
        cursor.execute("SELECT * FROM promo_coupon_usages")
        usages = cursor.fetchall()

        with self._get_connection(tenant_config) as tenant_conn:
            tenant_cursor = tenant_conn.cursor()

            # 迁移优惠券
            for coupon in coupons:
                columns = list(coupon.keys())
                placeholders = ', '.join(['%s'] * len(columns))
                columns_str = ', '.join(columns)

                tenant_cursor.execute(f"""
                    INSERT INTO promo_coupons ({columns_str})
                    VALUES ({placeholders})
                """, tuple(coupon.values()))

            # 迁移使用记录
            for usage in usages:
                columns = list(usage.keys())
                placeholders = ', '.join(['%s'] * len(columns))
                columns_str = ', '.join(columns)

                tenant_cursor.execute(f"""
                    INSERT INTO promo_coupon_usages ({columns_str})
                    VALUES ({placeholders})
                """, tuple(usage.values()))

            tenant_conn.commit()
            self.logger.info(f"迁移了 {len(coupons)} 个优惠券和 {len(usages)} 条使用记录")

    def _create_user_tenant_associations(self):
        """建立用户-租户关联"""
        self.logger.info("建立用户-租户关联关系")

        with self._get_connection(self.system_db) as conn:
            cursor = conn.cursor()

            # 获取所有用户
            cursor.execute("SELECT user_id FROM user_info")
            users = cursor.fetchall()

            # 将所有现有用户关联到默认租户
            for user in users:
                cursor.execute("""
                    INSERT INTO saas_tenant_users (tenant_id, user_id, role, status, joined_at)
                    VALUES ('default', %s, 'user', 1, CURRENT_TIMESTAMP)
                """, (user[0],))

            conn.commit()
            self.logger.info(f"创建了 {len(users)} 个用户-租户关联")

    def _validate_migration(self) -> bool:
        """验证数据迁移结果"""
        self.logger.info("验证数据迁移结果")

        try:
            # 验证用户数据
            legacy_user_count = self._get_record_count(self.legacy_db, "user_info")
            system_user_count = self._get_record_count(self.system_db, "user_info")

            if legacy_user_count != system_user_count:
                self.logger.error(f"用户数量不匹配: 原始={legacy_user_count}, 系统库={system_user_count}")
                return False

            # 验证订单数据
            tenant_config = self.system_db.copy()
            tenant_config['database'] = 'ai_shifu_tenant_default'

            legacy_order_count = self._get_record_count(self.legacy_db, "order_orders")
            tenant_order_count = self._get_record_count(tenant_config, "order_orders")

            if legacy_order_count != tenant_order_count:
                self.logger.error(f"订单数量不匹配: 原始={legacy_order_count}, 租户库={tenant_order_count}")
                return False

            # 验证学习记录数据
            legacy_progress_count = self._get_record_count(self.legacy_db, "learn_progress_records")
            tenant_progress_count = self._get_record_count(tenant_config, "learn_progress_records")

            if legacy_progress_count != tenant_progress_count:
                self.logger.error(f"学习进度记录数量不匹配: 原始={legacy_progress_count}, 租户库={tenant_progress_count}")
                return False

            # 验证活动数据
            legacy_active_count = self._get_record_count(self.legacy_db, "active")
            tenant_active_count = self._get_record_count(tenant_config, "active")

            if legacy_active_count != tenant_active_count:
                self.logger.error(f"活动数量不匹配: 原始={legacy_active_count}, 租户库={tenant_active_count}")
                return False

            # 验证优惠券数据
            legacy_coupon_count = self._get_record_count(self.legacy_db, "promo_coupons")
            tenant_coupon_count = self._get_record_count(tenant_config, "promo_coupons")

            if legacy_coupon_count != tenant_coupon_count:
                self.logger.error(f"优惠券数量不匹配: 原始={legacy_coupon_count}, 租户库={tenant_coupon_count}")
                return False

            # 验证用户-租户关联
            with self._get_connection(self.system_db) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM saas_tenant_users WHERE tenant_id = 'default'")
                association_count = cursor.fetchone()[0]

                if association_count != system_user_count:
                    self.logger.error(f"用户-租户关联数量不匹配: 用户数={system_user_count}, 关联数={association_count}")
                    return False

            self.logger.info("数据迁移验证通过")
            return True

        except Exception as e:
            self.logger.error(f"数据验证失败: {str(e)}")
            return False

    def _get_record_count(self, db_config: Dict, table_name: str) -> int:
        """获取表记录数"""
        with self._get_connection(db_config) as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            return cursor.fetchone()[0]

    def _get_connection(self, db_config: Dict):
        """获取数据库连接"""
        return pymysql.connect(**db_config)

    def _read_sql_file(self, filename: str) -> str:
        """读取SQL文件内容"""
        # 实际实现中应该从文件读取
        return ""  # 简化实现
```

### 5.2 向后兼容性保证

```python
# 向后兼容性适配器
class BackwardCompatibilityAdapter:
    """向后兼容性适配器"""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    def adapt_legacy_api_calls(self, app: Flask):
        """适配原有API调用"""

        @app.route('/api/legacy/user/<user_id>/orders', methods=['GET'])
        def legacy_get_user_orders(user_id):
            """兼容原有的用户订单API"""

            # 使用默认租户处理原有请求
            g.tenant_id = 'default'
            g.tenant_session = self.db_manager.get_tenant_session('default')
            g.system_session = self.db_manager.get_system_session()

            try:
                # 查询订单（保持原有响应格式）
                orders = g.tenant_session.execute("""
                    SELECT order_bid as order_id, shifu_bid, payable_price,
                           paid_price, status, created_at
                    FROM order_orders
                    WHERE user_id = %s AND deleted = 0
                    ORDER BY created_at DESC
                """, (user_id,)).fetchall()

                # 转换为原有格式
                legacy_response = {
                    'code': 0,
                    'message': 'success',
                    'data': {
                        'user_id': user_id,
                        'orders': [
                            {
                                'order_id': order[0],
                                'shifu_id': order[1],
                                'price': float(order[2]),
                                'paid': float(order[3]),
                                'status': order[4],
                                'created': order[5].strftime('%Y-%m-%d %H:%M:%S')
                            }
                            for order in orders
                        ]
                    }
                }

                return jsonify(legacy_response)

            finally:
                if hasattr(g, 'tenant_session'):
                    g.tenant_session.close()
                if hasattr(g, 'system_session'):
                    g.system_session.close()

        @app.route('/api/legacy/orders', methods=['POST'])
        def legacy_create_order():
            """兼容原有的创建订单API"""

            # 使用默认租户
            g.tenant_id = 'default'
            g.tenant_session = self.db_manager.get_tenant_session('default')
            g.system_session = self.db_manager.get_system_session()

            try:
                data = request.json

                # 生成订单ID
                import uuid
                order_bid = str(uuid.uuid4())

                # 插入订单
                g.tenant_session.execute("""
                    INSERT INTO order_orders (
                        order_bid, shifu_bid, user_id, payable_price, status, created_at
                    ) VALUES (%s, %s, %s, %s, 501, CURRENT_TIMESTAMP)
                """, (
                    order_bid,
                    data.get('shifu_id'),
                    data.get('user_id'),
                    data.get('price', 0)
                ))

                g.tenant_session.commit()

                return jsonify({
                    'code': 0,
                    'message': 'success',
                    'data': {
                        'order_id': order_bid
                    }
                })

            except Exception as e:
                return jsonify({
                    'code': 1,
                    'message': str(e)
                }), 500

            finally:
                if hasattr(g, 'tenant_session'):
                    g.tenant_session.close()
                if hasattr(g, 'system_session'):
                    g.system_session.close()

        # 添加Shifu相关API适配
        @app.route('/api/legacy/shifu/<shifu_id>', methods=['GET'])
        def legacy_get_shifu(shifu_id):
            """兼容原有的获取Shifu API"""
            g.tenant_id = 'default'
            g.tenant_session = self.db_manager.get_tenant_session('default')

            try:
                # 从租户库查询Shifu数据
                shifu = g.tenant_session.execute("""
                    SELECT shifu_bid, title, description, avatar_res_bid, status
                    FROM shifu_published_shifus
                    WHERE shifu_bid = %s AND deleted = 0
                """, (shifu_id,)).fetchone()

                if not shifu:
                    return jsonify({'code': 404, 'message': 'Shifu not found'}), 404

                return jsonify({
                    'code': 0,
                    'message': 'success',
                    'data': dict(shifu)
                })

            finally:
                if hasattr(g, 'tenant_session'):
                    g.tenant_session.close()

        # 添加学习记录API适配
        @app.route('/api/legacy/user/<user_id>/study_progress', methods=['GET'])
        def legacy_get_study_progress(user_id):
            """兼容原有的学习进度API"""
            g.tenant_id = 'default'
            g.tenant_session = self.db_manager.get_tenant_session('default')

            try:
                # 从租户库查询学习进度
                progress = g.tenant_session.execute("""
                    SELECT progress_record_bid, shifu_bid, outline_item_bid,
                           status, block_position, created_at
                    FROM learn_progress_records
                    WHERE user_bid = %s AND deleted = 0
                    ORDER BY created_at DESC
                """, (user_id,)).fetchall()

                return jsonify({
                    'code': 0,
                    'message': 'success',
                    'data': {
                        'user_id': user_id,
                        'progress': [dict(p) for p in progress]
                    }
                })

            finally:
                if hasattr(g, 'tenant_session'):
                    g.tenant_session.close()

        # 添加优惠券API适配
        @app.route('/api/legacy/coupons/user/<user_id>', methods=['GET'])
        def legacy_get_user_coupons(user_id):
            """兼容原有的用户优惠券API"""
            g.tenant_id = 'default'
            g.tenant_session = self.db_manager.get_tenant_session('default')

            try:
                # 从租户库查询用户优惠券
                coupons = g.tenant_session.execute("""
                    SELECT cu.coupon_usage_bid, cu.coupon_bid, cu.name, cu.code,
                           cu.discount_type, cu.value, cu.status
                    FROM promo_coupon_usages cu
                    WHERE cu.user_bid = %s AND cu.deleted = 0
                    ORDER BY cu.created_at DESC
                """, (user_id,)).fetchall()

                return jsonify({
                    'code': 0,
                    'message': 'success',
                    'data': {
                        'user_id': user_id,
                        'coupons': [dict(c) for c in coupons]
                    }
                })

            finally:
                if hasattr(g, 'tenant_session'):
                    g.tenant_session.close()

# 数据库查询适配器
class DatabaseQueryAdapter:
    """数据库查询适配器 - 处理跨库关联查询"""

    @staticmethod
    def get_user_with_tenant_info(system_session, tenant_session, user_id: str, tenant_id: str):
        """获取用户信息和租户内角色"""

        # 从系统库获取用户基本信息
        user = system_session.execute("""
            SELECT u.user_id, u.username, u.name, u.email, u.mobile, u.user_language,
                   tu.role, tu.permissions, tu.joined_at
            FROM user_info u
            JOIN saas_tenant_users tu ON u.user_id = tu.user_id
            WHERE u.user_id = %s AND tu.tenant_id = %s AND tu.deleted = 0
        """, (user_id, tenant_id)).fetchone()

        return dict(user) if user else None

    @staticmethod
    def get_user_orders_with_stats(system_session, tenant_session, user_id: str):
        """获取用户订单及统计信息"""

        # 从租户库获取订单
        orders = tenant_session.execute("""
            SELECT order_bid, shifu_bid, payable_price, paid_price, status,
                   created_at, updated_at
            FROM order_orders
            WHERE user_id = %s AND deleted = 0
            ORDER BY created_at DESC
        """, (user_id,)).fetchall()

        # 计算统计信息
        stats = tenant_session.execute("""
            SELECT
                COUNT(*) as total_orders,
                COUNT(CASE WHEN status = 502 THEN 1 END) as paid_orders,
                SUM(CASE WHEN status = 502 THEN paid_price ELSE 0 END) as total_spent,
                MAX(created_at) as last_order_date
            FROM order_orders
            WHERE user_id = %s AND deleted = 0
        """, (user_id,)).fetchone()

        return {
            'orders': [dict(order) for order in orders],
            'stats': dict(stats) if stats else {}
        }

    @staticmethod
    def get_user_shifu_data(system_session, tenant_session, user_id: str):
        """获取用户相关的Shifu数据"""

        # 获取用户购买的Shifu
        purchased_shifus = tenant_session.execute("""
            SELECT DISTINCT s.shifu_bid, s.title, s.description, s.status, o.created_at as purchased_at
            FROM shifu_published_shifus s
            JOIN order_orders o ON s.shifu_bid = o.shifu_bid
            WHERE o.user_id = %s AND o.status = 502 AND o.deleted = 0 AND s.deleted = 0
            ORDER BY o.created_at DESC
        """, (user_id,)).fetchall()

        # 获取学习进度
        progress_data = tenant_session.execute("""
            SELECT pr.shifu_bid, COUNT(*) as total_progress,
                   COUNT(CASE WHEN pr.status = 603 THEN 1 END) as completed_progress
            FROM learn_progress_records pr
            WHERE pr.user_bid = %s AND pr.deleted = 0
            GROUP BY pr.shifu_bid
        """, (user_id,)).fetchall()

        progress_dict = {p[0]: {'total': p[1], 'completed': p[2]} for p in progress_data}

        # 组合数据
        shifu_data = []
        for shifu in purchased_shifus:
            shifu_dict = dict(shifu)
            shifu_dict['progress'] = progress_dict.get(shifu['shifu_bid'], {'total': 0, 'completed': 0})
            shifu_data.append(shifu_dict)

        return shifu_data

    @staticmethod
    def get_user_activity_data(system_session, tenant_session, user_id: str):
        """获取用户活动参与数据"""

        # 获取用户参与的活动
        activities = tenant_session.execute("""
            SELECT a.active_id, a.active_name, a.active_desc, a.active_type,
                   a.active_price, a.active_discount, aur.status, aur.created as joined_at
            FROM active a
            JOIN active_user_record aur ON a.active_id = aur.active_id
            WHERE aur.user_id = %s
            ORDER BY aur.created DESC
        """, (user_id,)).fetchall()

        return [dict(activity) for activity in activities]

    @staticmethod
    def get_user_coupon_summary(system_session, tenant_session, user_id: str):
        """获取用户优惠券使用汇总"""

        # 获取优惠券使用统计
        summary = tenant_session.execute("""
            SELECT
                COUNT(*) as total_coupons,
                COUNT(CASE WHEN status = 903 THEN 1 END) as used_coupons,
                COUNT(CASE WHEN status = 902 THEN 1 END) as active_coupons,
                COUNT(CASE WHEN status = 904 THEN 1 END) as expired_coupons,
                SUM(CASE WHEN status = 903 THEN value ELSE 0 END) as total_savings
            FROM promo_coupon_usages
            WHERE user_bid = %s AND deleted = 0
        """, (user_id,)).fetchone()

        # 获取最近使用的优惠券
        recent_coupons = tenant_session.execute("""
            SELECT coupon_bid, name, code, discount_type, value, status, created_at
            FROM promo_coupon_usages
            WHERE user_bid = %s AND deleted = 0
            ORDER BY created_at DESC
            LIMIT 10
        """, (user_id,)).fetchall()

        return {
            'summary': dict(summary) if summary else {},
            'recent_coupons': [dict(coupon) for coupon in recent_coupons]
        }
```

## 6. 运维和监控

### 6.1 数据库监控

```python
# 数据库监控服务
class DatabaseMonitor:
    """数据库监控服务"""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    def get_system_health(self) -> Dict:
        """获取系统健康状态"""

        health_status = {
            'system_database': self._check_system_db_health(),
            'tenant_databases': self._check_tenant_dbs_health(),
            'connection_pools': self._check_connection_pools(),
            'overall_status': 'healthy'
        }

        # 检查是否有故障
        if any(db['status'] != 'healthy' for db in health_status['tenant_databases']):
            health_status['overall_status'] = 'degraded'

        if health_status['system_database']['status'] != 'healthy':
            health_status['overall_status'] = 'critical'

        return health_status

    def _check_system_db_health(self) -> Dict:
        """检查系统库健康状态"""
        try:
            session = self.db_manager.get_system_session()

            # 检查连接
            session.execute("SELECT 1")

            # 获取基本统计
            stats = session.execute("""
                SELECT
                    (SELECT COUNT(*) FROM saas_tenants WHERE status = 1) as active_tenants,
                    (SELECT COUNT(*) FROM user_info) as total_users,
                    (SELECT COUNT(*) FROM saas_tenant_users WHERE status = 1) as active_tenant_users
            """).fetchone()

            session.close()

            return {
                'status': 'healthy',
                'active_tenants': stats[0],
                'total_users': stats[1],
                'active_tenant_users': stats[2],
                'checked_at': datetime.now().isoformat()
            }

        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'checked_at': datetime.now().isoformat()
            }

    def _check_tenant_dbs_health(self) -> List[Dict]:
        """检查租户库健康状态"""
        tenant_health = []

        # 获取所有活跃租户
        try:
            system_session = self.db_manager.get_system_session()
            tenants = system_session.execute("""
                SELECT tenant_id, tenant_name, database_name
                FROM saas_tenants
                WHERE status = 1 AND deleted = 0
            """).fetchall()
            system_session.close()

            for tenant_id, tenant_name, db_name in tenants:
                health_info = {
                    'tenant_id': tenant_id,
                    'tenant_name': tenant_name,
                    'database_name': db_name
                }

                try:
                    tenant_session = self.db_manager.get_tenant_session(tenant_id)

                    # 检查连接并获取统计
                    stats = tenant_session.execute("""
                        SELECT
                            (SELECT COUNT(*) FROM order_orders WHERE deleted = 0) as total_orders,
                            (SELECT COUNT(*) FROM study_records WHERE deleted = 0) as total_study_records
                    """).fetchone()

                    tenant_session.close()

                    health_info.update({
                        'status': 'healthy',
                        'total_orders': stats[0],
                        'total_study_records': stats[1],
                        'checked_at': datetime.now().isoformat()
                    })

                except Exception as e:
                    health_info.update({
                        'status': 'unhealthy',
                        'error': str(e),
                        'checked_at': datetime.now().isoformat()
                    })

                tenant_health.append(health_info)

        except Exception as e:
            tenant_health.append({
                'error': f"无法获取租户列表: {str(e)}",
                'status': 'critical'
            })

        return tenant_health

    def _check_connection_pools(self) -> Dict:
        """检查连接池状态"""

        pools_info = {
            'system_pool': {
                'size': self.db_manager.system_engine.pool.size(),
                'checked_out': self.db_manager.system_engine.pool.checkedout(),
                'checked_in': self.db_manager.system_engine.pool.checkedin(),
                'invalidated': self.db_manager.system_engine.pool.invalidated()
            },
            'tenant_pools': []
        }

        # 检查租户连接池
        for tenant_id, engine in self.db_manager.tenant_engines.items():
            pools_info['tenant_pools'].append({
                'tenant_id': tenant_id,
                'size': engine.pool.size(),
                'checked_out': engine.pool.checkedout(),
                'checked_in': engine.pool.checkedin(),
                'invalidated': engine.pool.invalidated()
            })

        return pools_info

# 性能统计服务
class PerformanceStatsCollector:
    """性能统计收集器"""

    def __init__(self, db_manager: DatabaseManager, redis_client):
        self.db_manager = db_manager
        self.redis_client = redis_client

    def collect_daily_stats(self):
        """收集每日统计数据"""
        today = datetime.now().date()

        # 收集系统级统计
        system_stats = self._collect_system_stats()

        # 收集各租户统计
        tenant_stats = self._collect_tenant_stats(today)

        # 存储统计数据
        self._store_daily_stats(today, system_stats, tenant_stats)

    def _collect_system_stats(self) -> Dict:
        """收集系统级统计"""
        system_session = self.db_manager.get_system_session()

        stats = system_session.execute("""
            SELECT
                COUNT(DISTINCT t.tenant_id) as active_tenants,
                COUNT(DISTINCT u.user_id) as total_users,
                COUNT(DISTINCT tu.user_id) as active_tenant_users,
                COUNT(DISTINCT CASE WHEN DATE(al.created_at) = CURDATE() THEN al.user_id END) as daily_active_users
            FROM saas_tenants t
            CROSS JOIN user_info u
            LEFT JOIN saas_tenant_users tu ON u.user_id = tu.user_id AND tu.status = 1
            LEFT JOIN saas_access_logs al ON u.user_id = al.user_id
            WHERE t.status = 1 AND t.deleted = 0
        """).fetchone()

        system_session.close()

        return {
            'active_tenants': stats[0],
            'total_users': stats[1],
            'active_tenant_users': stats[2],
            'daily_active_users': stats[3] or 0
        }

    def _collect_tenant_stats(self, stat_date) -> Dict:
        """收集租户统计"""
        system_session = self.db_manager.get_system_session()

        # 获取所有活跃租户
        tenants = system_session.execute("""
            SELECT tenant_id FROM saas_tenants
            WHERE status = 1 AND deleted = 0
        """).fetchall()

        system_session.close()

        tenant_stats = {}

        for tenant_id, in tenants:
            try:
                tenant_session = self.db_manager.get_tenant_session(tenant_id)

                # 收集租户统计数据
                stats = tenant_session.execute("""
                    SELECT
                        COUNT(DISTINCT user_id) as total_users,
                        COUNT(DISTINCT CASE WHEN DATE(created_at) = %s THEN user_id END) as daily_active_users,
                        COUNT(DISTINCT order_bid) as total_orders,
                        COUNT(DISTINCT CASE WHEN DATE(created_at) = %s THEN order_bid END) as daily_orders,
                        SUM(CASE WHEN status = 502 THEN paid_price ELSE 0 END) as total_revenue,
                        SUM(CASE WHEN status = 502 AND DATE(created_at) = %s THEN paid_price ELSE 0 END) as daily_revenue
                    FROM order_orders
                    WHERE deleted = 0
                """, (stat_date, stat_date, stat_date)).fetchone()

                tenant_stats[tenant_id] = {
                    'total_users': stats[0],
                    'daily_active_users': stats[1] or 0,
                    'total_orders': stats[2],
                    'daily_orders': stats[3] or 0,
                    'total_revenue': float(stats[4] or 0),
                    'daily_revenue': float(stats[5] or 0)
                }

                tenant_session.close()

            except Exception as e:
                tenant_stats[tenant_id] = {'error': str(e)}

        return tenant_stats

    def _store_daily_stats(self, stat_date, system_stats: Dict, tenant_stats: Dict):
        """存储每日统计数据"""

        # 存储到Redis（用于快速查询）
        redis_key = f"daily_stats:{stat_date.strftime('%Y-%m-%d')}"
        stats_data = {
            'date': stat_date.isoformat(),
            'system': system_stats,
            'tenants': tenant_stats,
            'collected_at': datetime.now().isoformat()
        }

        import json
        self.redis_client.setex(redis_key, 86400 * 7, json.dumps(stats_data))  # 保存7天

        # 存储租户级统计到各租户数据库
        for tenant_id, stats in tenant_stats.items():
            if 'error' in stats:
                continue

            try:
                tenant_session = self.db_manager.get_tenant_session(tenant_id)

                # 插入或更新统计记录
                tenant_session.execute("""
                    INSERT INTO tenant_statistics (
                        stat_date, total_users, active_users, total_orders, total_revenue,
                        total_study_records, created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    ON DUPLICATE KEY UPDATE
                        total_users = VALUES(total_users),
                        active_users = VALUES(active_users),
                        total_orders = VALUES(total_orders),
                        total_revenue = VALUES(total_revenue),
                        updated_at = CURRENT_TIMESTAMP
                """, (
                    stat_date,
                    stats['total_users'],
                    stats['daily_active_users'],
                    stats['total_orders'],
                    stats['total_revenue']
                ))

                tenant_session.commit()
                tenant_session.close()

            except Exception as e:
                print(f"存储租户 {tenant_id} 统计数据失败: {str(e)}")
```

## 7. 实施计划

### 7.1 迁移时间线

| 阶段 | 时间 | 主要任务 | 交付物 | 风险点 |
|------|------|----------|---------|--------|
| **阶段1: 准备阶段** | 第1-2周 | 环境准备、备份现有数据 | 迁移环境、备份方案 | 数据备份完整性 |
| **阶段2: 系统库构建** | 第3-4周 | 创建系统库、迁移用户数据 | 系统库、用户迁移 | 用户数据一致性 |
| **阶段3: 租户库构建** | 第5-6周 | 创建租户库、迁移业务数据 | 租户库、业务数据迁移 | 数据关联性 |
| **阶段4: 应用适配** | 第7-8周 | 修改应用连接、路由逻辑 | 多库连接、域名路由 | 应用稳定性 |
| **阶段5: 测试验证** | 第9-10周 | 功能测试、性能测试 | 测试报告、性能基准 | 性能下降 |
| **阶段6: 上线切换** | 第11-12周 | 生产环境部署、流量切换 | 生产系统、监控 | 服务中断 |

### 7.2 详细实施步骤

#### 阶段1: 准备阶段 (第1-2周)

**第1周：环境准备**
```bash
# 1. 备份现有数据库
mysqldump -u root -p --single-transaction --routines --triggers ai_shifu > ai_shifu_backup_$(date +%Y%m%d).sql

# 2. 创建测试环境
docker run -d --name mysql-test-system \
  -e MYSQL_ROOT_PASSWORD=password \
  -e MYSQL_DATABASE=ai_shifu_system \
  -p 3307:3306 \
  mysql:8.0

# 3. 创建Redis实例
docker run -d --name redis-saas-test \
  -p 6380:6379 \
  redis:alpine

# 4. 安装依赖包
pip install pymysql sqlalchemy cryptography redis
```

**第2周：数据分析和方案确认**
- 分析现有数据量和结构
- 确认租户划分规则
- 制定详细迁移计划
- 准备回滚方案

#### 阶段2: 系统库构建 (第3-4周)

**第3周：系统库创建**
```python
# 执行系统库创建脚本
from migration.system_db_creator import SystemDbCreator

creator = SystemDbCreator(
    system_db_config={
        'host': 'localhost',
        'port': 3307,
        'user': 'root',
        'password': 'password',
        'database': 'ai_shifu_system'
    }
)

creator.create_system_database()
creator.insert_default_data()
```

**第4周：用户数据迁移**
```python
# 执行用户数据迁移
migrator = SaaSV1DataMigrator(
    legacy_db_config={
        'host': 'localhost',
        'port': 3306,
        'user': 'root',
        'password': 'password',
        'database': 'ai_shifu'
    },
    system_db_config={
        'host': 'localhost',
        'port': 3307,
        'user': 'root',
        'password': 'password',
        'database': 'ai_shifu_system'
    }
)

# 只迁移用户相关数据
migrator._migrate_user_data()
migrator._create_user_tenant_associations()
```

#### 阶段3: 租户库构建 (第5-6周)

**第5周：租户库创建**
```python
# 创建默认租户数据库
migrator._create_default_tenant_database()

# 注册租户信息
tenant_manager = TenantManager(db_manager)
tenant_manager.register_tenant({
    'tenant_id': 'default',
    'tenant_name': '默认租户',
    'tenant_domain': 'app.ai-shifu.com',
    'database_config': {
        'host': 'localhost',
        'port': 3307,
        'database': 'ai_shifu_tenant_default'
    }
})
```

**第6周：业务数据迁移**
```python
# 迁移业务数据到租户库
migrator._migrate_business_data()

# 验证数据完整性
if not migrator._validate_migration():
    raise Exception("数据迁移验证失败，需要检查数据一致性")
```

#### 阶段4: 应用适配 (第7-8周)

**第7周：数据库连接改造**
```python
# 初始化数据库管理器
app = create_saas_app(
    system_db_url="mysql://root:password@localhost:3307/ai_shifu_system",
    redis_url="redis://localhost:6380/0",
    encryption_key="your-encryption-key-32-chars-long"
)

# 配置Flask应用
saas_app = SaaSFlaskApp(app, get_db_manager())
```

**第8周：路由和API改造**
```python
# 注册新的路由处理器
register_routes(app)

# 添加向后兼容接口
compatibility_adapter = BackwardCompatibilityAdapter(get_db_manager())
compatibility_adapter.adapt_legacy_api_calls(app)
```

#### 阶段5: 测试验证 (第9-10周)

**第9周：功能测试**
```python
# 自动化测试脚本
import pytest

class TestSaaSV1Migration:

    def test_user_data_integrity(self):
        """测试用户数据完整性"""
        # 验证用户数量
        # 验证用户信息正确性
        # 验证用户-租户关联

    def test_business_data_integrity(self):
        """测试业务数据完整性"""
        # 验证订单数据
        # 验证关联关系
        # 验证统计一致性

    def test_api_functionality(self):
        """测试API功能"""
        # 测试租户路由
        # 测试跨库查询
        # 测试向后兼容接口
```

**第10周：性能测试**
```python
# 性能测试脚本
from locust import HttpUser, task, between

class SaaSLoadTest(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def test_tenant_api(self):
        headers = {'Host': 'tenant1.ai-shifu.com'}
        self.client.get('/api/orders', headers=headers)

    @task(2)
    def test_user_orders(self):
        self.client.get('/api/users/test-user/orders')

    @task(1)
    def test_legacy_api(self):
        self.client.get('/api/legacy/user/test-user/orders')
```

#### 阶段6: 上线切换 (第11-12周)

**第11周：生产环境部署**
```yaml
# docker-compose.yml - 生产环境配置
version: '3.8'
services:
  mysql-system:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
      MYSQL_DATABASE: ai_shifu_system
    volumes:
      - system_db_data:/var/lib/mysql
      - ./config/mysql-system.cnf:/etc/mysql/conf.d/custom.cnf
    ports:
      - "3306:3306"

  mysql-tenant-default:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
      MYSQL_DATABASE: ai_shifu_tenant_default
    volumes:
      - tenant_db_data:/var/lib/mysql
      - ./config/mysql-tenant.cnf:/etc/mysql/conf.d/custom.cnf
    ports:
      - "3307:3306"

  redis:
    image: redis:alpine
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"

  ai-shifu-api:
    image: ai-shifu:saas-v1
    environment:
      - SYSTEM_DB_URL=mysql://root:${MYSQL_ROOT_PASSWORD}@mysql-system:3306/ai_shifu_system
      - REDIS_URL=redis://redis:6379/0
      - ENCRYPTION_KEY=${ENCRYPTION_KEY}
    depends_on:
      - mysql-system
      - mysql-tenant-default
      - redis
    ports:
      - "5000:5000"

volumes:
  system_db_data:
  tenant_db_data:
  redis_data:
```

**第12周：流量切换和监控**
```python
# 健康检查和监控
monitor = DatabaseMonitor(get_db_manager())
health_status = monitor.get_system_health()

if health_status['overall_status'] == 'healthy':
    # 切换DNS指向新系统
    # 或使用负载均衡器切换流量
    print("系统健康，可以切换流量")
else:
    print("系统不健康，需要检查问题")
    print(health_status)

# 性能监控
stats_collector = PerformanceStatsCollector(
    get_db_manager(),
    redis.Redis.from_url("redis://localhost:6379/0")
)
stats_collector.collect_daily_stats()
```

### 7.3 风险控制

#### 7.3.1 技术风险

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|----------|
| 数据迁移失败 | 高 | 中 | 充分测试、分批迁移、实时验证 |
| 性能下降 | 中 | 中 | 性能测试、连接池优化、索引优化 |
| 系统不稳定 | 高 | 低 | 灰度发布、监控告警、快速回滚 |
| 跨库关联复杂 | 中 | 高 | 查询优化、缓存策略、异步处理 |

#### 7.3.2 回滚方案

```python
# 紧急回滚脚本
class EmergencyRollback:

    def __init__(self, backup_config):
        self.backup_config = backup_config

    def rollback_to_legacy_system(self):
        """回滚到原有系统"""

        # 1. 停止新系统服务
        self._stop_saas_services()

        # 2. 恢复原始数据库
        self._restore_legacy_database()

        # 3. 启动原有系统
        self._start_legacy_services()

        # 4. 切换DNS/负载均衡
        self._switch_traffic_to_legacy()

        # 5. 验证系统正常
        self._verify_legacy_system()

    def incremental_rollback(self, failed_component):
        """增量回滚特定组件"""

        if failed_component == 'tenant_routing':
            # 禁用租户路由，使用默认租户
            self._disable_tenant_routing()

        elif failed_component == 'database_connection':
            # 回滚到单库连接
            self._rollback_to_single_db()
```

### 7.4 监控和告警

```python
# 监控配置
monitoring_config = {
    'system_db': {
        'connection_threshold': 80,  # 连接数阈值
        'response_time_threshold': 100,  # 响应时间阈值(ms)
        'error_rate_threshold': 1,  # 错误率阈值(%)
    },
    'tenant_db': {
        'connection_threshold': 50,
        'response_time_threshold': 200,
        'error_rate_threshold': 2,
    },
    'application': {
        'memory_threshold': 2048,  # 内存阈值(MB)
        'cpu_threshold': 80,  # CPU阈值(%)
        'request_rate_threshold': 1000,  # 请求率阈值(req/min)
    }
}

# 告警规则
alerting_rules = {
    'database_down': {
        'condition': 'system_db.status != "healthy"',
        'severity': 'critical',
        'notification': ['email', 'sms', 'slack']
    },
    'tenant_db_slow': {
        'condition': 'tenant_db.response_time > 200',
        'severity': 'warning',
        'notification': ['email']
    },
    'high_error_rate': {
        'condition': 'error_rate > 5',
        'severity': 'warning',
        'notification': ['slack']
    }
}
```

## 8. 成功标准和验收

### 8.1 技术验收标准

- ✅ **数据完整性**: 所有现有数据成功迁移，无数据丢失
- ✅ **功能完整性**: 所有现有功能正常工作，新增租户功能可用
- ✅ **性能标准**: 系统响应时间不超过现有系统的120%
- ✅ **稳定性**: 系统可用性达到99.9%
- ✅ **向后兼容**: 现有API调用方式继续有效

### 8.2 业务验收标准

- ✅ **用户体验**: 现有用户无感知升级，功能使用无变化
- ✅ **多租户功能**: 支持通过域名访问不同租户
- ✅ **数据隔离**: 租户间数据完全隔离，无交叉访问
- ✅ **管理功能**: 系统管理员可以管理租户和用户
- ✅ **监控告警**: 完善的系统监控和异常告警

### 8.3 运维验收标准

- ✅ **部署自动化**: 支持一键部署和回滚
- ✅ **监控完善**: 全面的系统和业务监控
- ✅ **日志完整**: 详细的操作和错误日志
- ✅ **文档齐全**: 完整的运维文档和操作手册
- ✅ **应急预案**: 明确的故障处理和恢复流程

## 9. 总结

AI-Shifu SaaS 1.0分库架构设计实现了以下目标：

### 9.1 架构优势

1. **渐进式改造** - 最小化对现有系统的影响，平滑过渡
2. **数据隔离** - 通过分库实现租户间完全隔离
3. **性能优化** - 分库减少数据量，提升查询性能
4. **扩展性强** - 支持独立扩展租户数据库
5. **向后兼容** - 保持现有API和功能完整性

### 9.2 关键创新

1. **统一用户系统** - 用户数据集中管理，跨租户共享
2. **灵活路由机制** - 支持域名、子域名、Header多种路由方式
3. **智能连接管理** - 动态创建和管理租户数据库连接
4. **跨库查询优化** - 高效处理用户-业务数据关联查询
5. **完善监控体系** - 全方位的系统健康监控

### 9.3 技术特色

- **分布式架构**: 系统库 + 多租户库的分布式设计
- **连接池优化**: 智能的数据库连接池管理
- **缓存策略**: Redis缓存提升性能
- **安全加固**: 数据库密码加密存储
- **容错机制**: 完善的异常处理和恢复能力

这个SaaS 1.0方案为AI-Shifu向完整SaaS平台演进奠定了坚实基础，同时保证了现有业务的连续性和稳定性。
