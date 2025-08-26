# OAuth 集成架构详细设计文档

## 1. 概述

### 1.1 系统目标

OAuth 集成系统为AI-Shifu SaaS平台提供统一的身份认证和授权服务，支持多种OAuth提供商，实现企业级单点登录(SSO)和用户身份联合。

### 1.2 核心功能

- 多OAuth提供商支持
- 租户级别的OAuth配置
- Just-In-Time (JIT) 用户创建
- 用户属性映射和角色分配
- SAML 2.0 支持
- SCIM 用户同步

### 1.3 支持的身份提供商

**企业级 SSO**
- Google Workspace / Google Cloud Identity
- Microsoft Azure AD / Office 365
- Okta
- Auth0
- Ping Identity
- OneLogin
- ADFS (Active Directory Federation Services)

**社交登录**
- 微信企业微信
- 钉钉
- GitHub (开发者)
- LinkedIn (专业网络)

**标准协议**
- OAuth 2.0 / OpenID Connect
- SAML 2.0
- LDAP (间接支持)

## 2. 系统架构

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend                               │
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │   Login Page    │  │ SSO Callback    │                  │
│  │                 │  │     Page        │                  │
│  └─────────────────┘  └─────────────────┘                  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   API Gateway                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │            OAuth Flow Controller                       │ │
│  │  • Provider Detection                                  │ │
│  │  • Flow Orchestration                                 │ │
│  │  • Error Handling                                     │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                OAuth Integration Service                    │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐ │
│  │   OAuth     │ │    User     │ │      Config           │ │
│  │ Providers   │ │ Provisioning│ │   Management          │ │
│  │  Service    │ │   Service   │ │     Service           │ │
│  └─────────────┘ └─────────────┘ └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                External OAuth Providers                     │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────────────────┐ │
│  │ Google  │ │Microsoft│ │  Okta   │ │      Others       │ │
│  │   SSO   │ │Azure AD │ │   SSO   │ │  (WeChat/DingTalk) │ │
│  └─────────┘ └─────────┘ └─────────┘ └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 核心服务组件

**OAuth Provider Service**: OAuth提供商管理
- 提供商配置和凭据管理
- OAuth流程标准化处理
- Token管理和刷新

**User Provisioning Service**: 用户自动创建
- JIT用户创建和更新
- 属性映射和角色分配
- 用户去重和合并

**Configuration Service**: 配置管理
- 租户级OAuth配置
- 提供商参数管理
- 映射规则配置

**Session Management Service**: 会话管理
- 跨域会话管理
- Token生命周期管理
- 登出和会话清理

## 3. 数据模型设计

### 3.1 OAuth 提供商配置 (OAuthProvider)

```sql
CREATE TABLE saas_oauth_providers (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    provider_bid VARCHAR(32) NOT NULL UNIQUE,
    tenant_bid VARCHAR(32) NOT NULL,

    -- Provider Information
    provider_type ENUM('google', 'microsoft', 'okta', 'auth0', 'saml', 'wechat', 'dingtalk', 'github') NOT NULL,
    provider_name VARCHAR(100) NOT NULL,
    display_name VARCHAR(100) NOT NULL,

    -- OAuth Configuration
    client_id VARCHAR(255) NOT NULL,
    client_secret TEXT NOT NULL, -- 加密存储
    authorization_url VARCHAR(500),
    token_url VARCHAR(500),
    user_info_url VARCHAR(500),
    jwks_url VARCHAR(500),

    -- SAML Configuration (如果是SAML)
    saml_entity_id VARCHAR(255),
    saml_sso_url VARCHAR(500),
    saml_certificate TEXT,

    -- Scopes and Claims
    default_scopes JSON, -- ["openid", "email", "profile"]
    required_claims JSON, -- ["email", "name"]
    optional_claims JSON, -- ["department", "title"]

    -- User Attribute Mapping
    attribute_mapping JSON, -- 用户属性映射规则
    role_mapping JSON, -- 角色映射规则

    -- Settings
    is_enabled BOOLEAN DEFAULT TRUE,
    is_default BOOLEAN DEFAULT FALSE,
    allow_registration BOOLEAN DEFAULT TRUE, -- 是否允许新用户注册
    auto_create_user BOOLEAN DEFAULT TRUE,

    -- Advanced Settings
    login_hint VARCHAR(255), -- 登录提示
    prompt_type ENUM('none', 'login', 'consent', 'select_account') DEFAULT 'select_account',
    max_age INT DEFAULT 3600,

    -- Standard Fields
    deleted SMALLINT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_user_bid VARCHAR(32) DEFAULT '',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    updated_user_bid VARCHAR(32) DEFAULT '',

    UNIQUE KEY uk_tenant_provider (tenant_bid, provider_type),
    INDEX idx_tenant_bid (tenant_bid),
    INDEX idx_provider_type (provider_type),
    INDEX idx_enabled (is_enabled),
    INDEX idx_default (tenant_bid, is_default)
);
```

### 3.2 OAuth 会话状态 (OAuthState)

```sql
CREATE TABLE saas_oauth_states (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    state_token VARCHAR(64) NOT NULL UNIQUE,
    tenant_bid VARCHAR(32) NOT NULL,
    provider_bid VARCHAR(32) NOT NULL,

    -- OAuth Flow Data
    redirect_uri VARCHAR(500) NOT NULL,
    code_verifier VARCHAR(128), -- PKCE
    nonce VARCHAR(64),

    -- Request Context
    user_ip VARCHAR(45),
    user_agent TEXT,
    referrer VARCHAR(500),

    -- Flow Status
    status ENUM('initiated', 'callback_received', 'completed', 'failed', 'expired') DEFAULT 'initiated',
    error_code VARCHAR(50),
    error_message TEXT,

    -- Timestamps
    initiated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME,
    expires_at DATETIME NOT NULL,

    INDEX idx_state_token (state_token),
    INDEX idx_tenant_provider (tenant_bid, provider_bid),
    INDEX idx_expires_at (expires_at),
    INDEX idx_status (status)
);
```

### 3.3 用户身份映射 (UserIdentityMapping)

```sql
CREATE TABLE saas_user_identity_mappings (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    mapping_bid VARCHAR(32) NOT NULL UNIQUE,

    -- User Reference
    user_bid VARCHAR(32) NOT NULL,
    tenant_bid VARCHAR(32) NOT NULL,

    -- Identity Provider Info
    provider_bid VARCHAR(32) NOT NULL,
    provider_type VARCHAR(50) NOT NULL,
    external_user_id VARCHAR(255) NOT NULL, -- OAuth提供商的用户ID

    -- Identity Details
    email VARCHAR(255) NOT NULL,
    email_verified BOOLEAN DEFAULT FALSE,
    name VARCHAR(255),
    avatar_url VARCHAR(500),
    locale VARCHAR(10),
    timezone VARCHAR(50),

    -- Provider-specific Data
    provider_data JSON, -- 原始用户数据
    last_login_data JSON, -- 最后登录时的数据

    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    is_primary BOOLEAN DEFAULT FALSE, -- 主要身份提供商

    -- Timestamps
    first_login_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE KEY uk_provider_external_id (provider_bid, external_user_id),
    UNIQUE KEY uk_user_provider (user_bid, provider_bid),
    INDEX idx_user_bid (user_bid),
    INDEX idx_tenant_bid (tenant_bid),
    INDEX idx_email (email),
    INDEX idx_external_user_id (external_user_id),
    INDEX idx_provider_type (provider_type)
);
```

### 3.4 OAuth Tokens 存储

```sql
CREATE TABLE saas_oauth_tokens (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    token_bid VARCHAR(32) NOT NULL UNIQUE,

    -- Token Context
    user_bid VARCHAR(32) NOT NULL,
    tenant_bid VARCHAR(32) NOT NULL,
    provider_bid VARCHAR(32) NOT NULL,

    -- Token Data (加密存储)
    access_token TEXT,
    refresh_token TEXT,
    id_token TEXT,

    -- Token Metadata
    token_type VARCHAR(50) DEFAULT 'Bearer',
    expires_at DATETIME,
    scope VARCHAR(500),

    -- Usage Tracking
    last_used_at DATETIME,
    refresh_count INT DEFAULT 0,

    -- Standard Fields
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE KEY uk_user_provider (user_bid, provider_bid),
    INDEX idx_user_bid (user_bid),
    INDEX idx_tenant_bid (tenant_bid),
    INDEX idx_expires_at (expires_at),
    INDEX idx_last_used (last_used_at)
);
```

## 4. OAuth 流程设计

### 4.1 标准 OAuth 2.0 流程

```
用户访问登录页面 → 选择身份提供商 → 跳转OAuth授权
         ↓
OAuth提供商用户认证 → 授权确认 → 回调携带授权码
         ↓
验证授权码 → 交换访问令牌 → 获取用户信息
         ↓
用户身份映射 → JIT用户创建 → 生成应用会话
         ↓
重定向到应用首页
```

### 4.2 租户识别策略

**基于域名识别**
```python
class TenantResolver:
    async def resolve_tenant_from_request(self, request):
        # 1. 从自定义域名识别
        host = request.headers.get('host')
        tenant = await self.get_tenant_by_domain(host)
        if tenant:
            return tenant

        # 2. 从子域名识别
        subdomain = self.extract_subdomain(host)
        if subdomain and subdomain != 'www':
            tenant = await self.get_tenant_by_subdomain(subdomain)
            if tenant:
                return tenant

        # 3. 从路径参数识别
        tenant_param = request.query_params.get('tenant')
        if tenant_param:
            tenant = await self.get_tenant_by_bid(tenant_param)
            if tenant:
                return tenant

        # 4. 从JWT token识别
        token = self.extract_token_from_request(request)
        if token:
            payload = self.decode_jwt(token)
            return await self.get_tenant_by_bid(payload.get('tenant_bid'))

        raise TenantNotFoundError("Unable to identify tenant from request")
```

### 4.3 OAuth 服务实现

```python
class OAuthProviderService:
    def __init__(self):
        self.providers = {
            'google': GoogleOAuthProvider(),
            'microsoft': MicrosoftOAuthProvider(),
            'okta': OktaOAuthProvider(),
            'auth0': Auth0OAuthProvider(),
            'wechat': WeChatOAuthProvider(),
            'dingtalk': DingTalkOAuthProvider(),
        }

    async def initiate_oauth_flow(self, tenant_bid: str, provider_type: str, redirect_uri: str):
        # 1. 获取OAuth配置
        provider_config = await self.get_provider_config(tenant_bid, provider_type)
        if not provider_config or not provider_config.is_enabled:
            raise ProviderNotConfiguredError(f"OAuth provider {provider_type} not configured for tenant")

        # 2. 生成状态参数
        state_token = secrets.token_urlsafe(32)
        code_verifier = secrets.token_urlsafe(43) if provider_config.supports_pkce else None
        nonce = secrets.token_urlsafe(16)

        # 3. 保存OAuth状态
        oauth_state = OAuthState(
            state_token=state_token,
            tenant_bid=tenant_bid,
            provider_bid=provider_config.provider_bid,
            redirect_uri=redirect_uri,
            code_verifier=code_verifier,
            nonce=nonce,
            expires_at=datetime.utcnow() + timedelta(minutes=10)
        )
        await self.oauth_state_repository.create(oauth_state)

        # 4. 构建授权URL
        provider = self.providers[provider_type]
        auth_url = await provider.build_authorization_url(
            client_id=provider_config.client_id,
            redirect_uri=redirect_uri,
            state=state_token,
            code_challenge=self.generate_code_challenge(code_verifier) if code_verifier else None,
            nonce=nonce,
            scopes=provider_config.default_scopes
        )

        return {
            'authorization_url': auth_url,
            'state': state_token
        }

    async def handle_oauth_callback(self, state: str, code: str, error: str = None):
        # 1. 验证状态参数
        oauth_state = await self.oauth_state_repository.get_by_state(state)
        if not oauth_state or oauth_state.expires_at < datetime.utcnow():
            raise InvalidOAuthStateError("Invalid or expired OAuth state")

        if error:
            await self.oauth_state_repository.update_status(oauth_state.id, 'failed', error)
            raise OAuthCallbackError(f"OAuth callback error: {error}")

        # 2. 获取提供商配置
        provider_config = await self.get_provider_config_by_bid(oauth_state.provider_bid)
        provider = self.providers[provider_config.provider_type]

        # 3. 交换访问令牌
        token_response = await provider.exchange_code_for_tokens(
            client_id=provider_config.client_id,
            client_secret=provider_config.client_secret,
            code=code,
            redirect_uri=oauth_state.redirect_uri,
            code_verifier=oauth_state.code_verifier
        )

        # 4. 获取用户信息
        user_info = await provider.get_user_info(token_response.access_token)

        # 5. 用户身份映射和创建
        user = await self.user_provisioning_service.provision_user(
            tenant_bid=oauth_state.tenant_bid,
            provider_config=provider_config,
            user_info=user_info,
            tokens=token_response
        )

        # 6. 更新OAuth状态
        await self.oauth_state_repository.update_status(oauth_state.id, 'completed')

        return user

class UserProvisioningService:
    async def provision_user(self, tenant_bid: str, provider_config: OAuthProvider,
                           user_info: dict, tokens: TokenResponse):
        # 1. 查找现有用户身份映射
        identity_mapping = await self.identity_repository.get_by_external_id(
            provider_config.provider_bid, user_info.get('id')
        )

        if identity_mapping:
            # 更新现有用户
            user = await self.update_existing_user(identity_mapping, user_info, tokens)
        else:
            # 创建新用户或关联现有用户
            user = await self.create_or_link_user(tenant_bid, provider_config, user_info, tokens)

        return user

    async def create_or_link_user(self, tenant_bid: str, provider_config: OAuthProvider,
                                user_info: dict, tokens: TokenResponse):
        email = user_info.get('email')

        # 1. 尝试通过邮箱查找现有用户
        existing_user = await self.user_repository.get_by_email(email) if email else None

        if existing_user:
            # 关联到现有用户
            user = existing_user
        else:
            # 创建新用户
            if not provider_config.auto_create_user:
                raise UserProvisioningError("User auto-creation is disabled")

            user_data = self.map_user_attributes(provider_config.attribute_mapping, user_info)
            user = await self.user_repository.create(User(
                user_id=generate_uuid(),
                email=user_data.get('email', ''),
                username=user_data.get('username', email),
                name=user_data.get('name', ''),
                user_avatar=user_data.get('avatar_url', ''),
                user_language=user_data.get('locale', 'en-US')
            ))

        # 2. 创建身份映射
        identity_mapping = UserIdentityMapping(
            mapping_bid=generate_uuid(),
            user_bid=user.user_id,
            tenant_bid=tenant_bid,
            provider_bid=provider_config.provider_bid,
            provider_type=provider_config.provider_type,
            external_user_id=user_info.get('id'),
            email=user_info.get('email', ''),
            email_verified=user_info.get('email_verified', False),
            name=user_info.get('name', ''),
            avatar_url=user_info.get('picture', ''),
            provider_data=user_info
        )
        await self.identity_repository.create(identity_mapping)

        # 3. 分配租户角色
        await self.assign_tenant_role(tenant_bid, user.user_id, provider_config)

        # 4. 保存OAuth令牌
        await self.save_oauth_tokens(user.user_id, tenant_bid, provider_config.provider_bid, tokens)

        return user

    def map_user_attributes(self, mapping_rules: dict, user_info: dict) -> dict:
        """根据映射规则转换用户属性"""
        result = {}

        for target_attr, source_path in mapping_rules.items():
            # 支持嵌套路径，如 "profile.name"
            value = self.get_nested_value(user_info, source_path)
            if value is not None:
                result[target_attr] = value

        return result

    async def assign_tenant_role(self, tenant_bid: str, user_bid: str, provider_config: OAuthProvider):
        # 1. 检查是否已有租户关系
        tenant_user = await self.tenant_user_repository.get_by_user_tenant(user_bid, tenant_bid)

        if not tenant_user:
            # 2. 根据映射规则确定角色
            default_role = 'member'
            role_mapping = provider_config.role_mapping or {}

            # 基于用户信息映射角色（如部门、职位等）
            mapped_role = self.determine_role_from_mapping(role_mapping, user_info)
            role = mapped_role or default_role

            # 3. 创建租户用户关系
            tenant_user = TenantUser(
                tenant_user_bid=generate_uuid(),
                tenant_bid=tenant_bid,
                user_bid=user_bid,
                role=role,
                permissions=self.get_default_permissions(role),
                status='active',
                joined_at=datetime.utcnow()
            )
            await self.tenant_user_repository.create(tenant_user)
```

### 4.4 SAML 2.0 支持

```python
class SAMLProvider(BaseOAuthProvider):
    async def build_authorization_url(self, **kwargs):
        # 构建SAML AuthnRequest
        saml_request = self.create_authn_request(
            entity_id=kwargs['entity_id'],
            acs_url=kwargs['acs_url'],
            destination=kwargs['sso_url']
        )

        # Base64编码
        encoded_request = base64.b64encode(saml_request.encode()).decode()

        # 构建重定向URL
        auth_url = f"{kwargs['sso_url']}?SAMLRequest={encoded_request}&RelayState={kwargs['state']}"

        return auth_url

    async def handle_saml_response(self, saml_response: str, relay_state: str):
        # 1. 解码SAML Response
        decoded_response = base64.b64decode(saml_response)

        # 2. 验证签名
        if not self.verify_saml_signature(decoded_response):
            raise SAMLSignatureError("Invalid SAML signature")

        # 3. 解析用户信息
        user_info = self.extract_user_info_from_saml(decoded_response)

        return user_info

    def create_authn_request(self, entity_id: str, acs_url: str, destination: str):
        # 创建SAML AuthnRequest XML
        request_id = f"id_{uuid.uuid4()}"
        timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

        authn_request = f"""
        <samlp:AuthnRequest
            xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
            xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
            ID="{request_id}"
            Version="2.0"
            IssueInstant="{timestamp}"
            Destination="{destination}"
            AssertionConsumerServiceURL="{acs_url}"
            ProtocolBinding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST">
            <saml:Issuer>{entity_id}</saml:Issuer>
        </samlp:AuthnRequest>
        """

        return authn_request
```

## 5. 提供商具体实现

### 5.1 Google OAuth 实现

```python
class GoogleOAuthProvider(BaseOAuthProvider):
    def __init__(self):
        self.authorization_endpoint = "https://accounts.google.com/o/oauth2/v2/auth"
        self.token_endpoint = "https://oauth2.googleapis.com/token"
        self.userinfo_endpoint = "https://www.googleapis.com/oauth2/v2/userinfo"
        self.jwks_endpoint = "https://www.googleapis.com/oauth2/v3/certs"
        self.default_scopes = ["openid", "email", "profile"]

    async def build_authorization_url(self, client_id: str, redirect_uri: str,
                                    state: str, scopes: list = None, **kwargs):
        params = {
            'client_id': client_id,
            'response_type': 'code',
            'scope': ' '.join(scopes or self.default_scopes),
            'redirect_uri': redirect_uri,
            'state': state,
            'access_type': 'offline',  # 获取refresh_token
            'prompt': kwargs.get('prompt', 'select_account'),
            'include_granted_scopes': 'true'
        }

        if kwargs.get('code_challenge'):
            params['code_challenge'] = kwargs['code_challenge']
            params['code_challenge_method'] = 'S256'

        if kwargs.get('nonce'):
            params['nonce'] = kwargs['nonce']

        query_string = urlencode(params)
        return f"{self.authorization_endpoint}?{query_string}"

    async def exchange_code_for_tokens(self, client_id: str, client_secret: str,
                                     code: str, redirect_uri: str, **kwargs):
        data = {
            'client_id': client_id,
            'client_secret': client_secret,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': redirect_uri,
        }

        if kwargs.get('code_verifier'):
            data['code_verifier'] = kwargs['code_verifier']

        async with httpx.AsyncClient() as client:
            response = await client.post(self.token_endpoint, data=data)

        if response.status_code != 200:
            raise TokenExchangeError(f"Token exchange failed: {response.text}")

        token_data = response.json()

        return TokenResponse(
            access_token=token_data['access_token'],
            token_type=token_data.get('token_type', 'Bearer'),
            expires_in=token_data.get('expires_in'),
            refresh_token=token_data.get('refresh_token'),
            id_token=token_data.get('id_token'),
            scope=token_data.get('scope')
        )

    async def get_user_info(self, access_token: str):
        headers = {'Authorization': f'Bearer {access_token}'}

        async with httpx.AsyncClient() as client:
            response = await client.get(self.userinfo_endpoint, headers=headers)

        if response.status_code != 200:
            raise UserInfoError(f"Failed to get user info: {response.text}")

        user_data = response.json()

        return {
            'id': user_data['id'],
            'email': user_data['email'],
            'email_verified': user_data.get('verified_email', False),
            'name': user_data.get('name'),
            'given_name': user_data.get('given_name'),
            'family_name': user_data.get('family_name'),
            'picture': user_data.get('picture'),
            'locale': user_data.get('locale'),
            'provider': 'google'
        }
```

### 5.2 Microsoft Azure AD 实现

```python
class MicrosoftOAuthProvider(BaseOAuthProvider):
    def __init__(self):
        self.base_url = "https://login.microsoftonline.com"
        self.default_scopes = ["openid", "email", "profile", "User.Read"]

    def get_tenant_endpoints(self, tenant_id: str = "common"):
        return {
            'authorization': f"{self.base_url}/{tenant_id}/oauth2/v2.0/authorize",
            'token': f"{self.base_url}/{tenant_id}/oauth2/v2.0/token",
            'userinfo': "https://graph.microsoft.com/v1.0/me"
        }

    async def build_authorization_url(self, client_id: str, redirect_uri: str,
                                    state: str, scopes: list = None, tenant_id: str = "common", **kwargs):
        endpoints = self.get_tenant_endpoints(tenant_id)

        params = {
            'client_id': client_id,
            'response_type': 'code',
            'redirect_uri': redirect_uri,
            'response_mode': 'query',
            'scope': ' '.join(scopes or self.default_scopes),
            'state': state,
            'prompt': kwargs.get('prompt', 'select_account')
        }

        if kwargs.get('code_challenge'):
            params['code_challenge'] = kwargs['code_challenge']
            params['code_challenge_method'] = 'S256'

        query_string = urlencode(params)
        return f"{endpoints['authorization']}?{query_string}"

    async def get_user_info(self, access_token: str):
        headers = {'Authorization': f'Bearer {access_token}'}

        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://graph.microsoft.com/v1.0/me",
                headers=headers
            )

        if response.status_code != 200:
            raise UserInfoError(f"Failed to get user info: {response.text}")

        user_data = response.json()

        return {
            'id': user_data['id'],
            'email': user_data.get('mail') or user_data.get('userPrincipalName'),
            'name': user_data.get('displayName'),
            'given_name': user_data.get('givenName'),
            'family_name': user_data.get('surname'),
            'job_title': user_data.get('jobTitle'),
            'department': user_data.get('department'),
            'office_location': user_data.get('officeLocation'),
            'business_phones': user_data.get('businessPhones', []),
            'provider': 'microsoft'
        }
```

### 5.3 企业微信实现

```python
class WeChatOAuthProvider(BaseOAuthProvider):
    def __init__(self):
        self.authorization_endpoint = "https://open.weixin.qq.com/connect/oauth2/authorize"
        self.token_endpoint = "https://qyapi.weixin.qq.com/cgi-bin/gettoken"
        self.userinfo_endpoint = "https://qyapi.weixin.qq.com/cgi-bin/user/getuserinfo"
        self.user_detail_endpoint = "https://qyapi.weixin.qq.com/cgi-bin/user/get"

    async def build_authorization_url(self, corp_id: str, redirect_uri: str,
                                    state: str, agent_id: str, **kwargs):
        params = {
            'appid': corp_id,
            'redirect_uri': redirect_uri,
            'response_type': 'code',
            'scope': 'snsapi_base',  # 或 snsapi_userinfo
            'agentid': agent_id,
            'state': state
        }

        query_string = urlencode(params)
        return f"{self.authorization_endpoint}?{query_string}#wechat_redirect"

    async def exchange_code_for_tokens(self, corp_id: str, corp_secret: str, **kwargs):
        # 企业微信先获取access_token
        token_params = {
            'corpid': corp_id,
            'corpsecret': corp_secret
        }

        async with httpx.AsyncClient() as client:
            token_response = await client.get(self.token_endpoint, params=token_params)

        if token_response.status_code != 200:
            raise TokenExchangeError(f"Failed to get access token: {token_response.text}")

        token_data = token_response.json()
        if token_data.get('errcode') != 0:
            raise TokenExchangeError(f"WeChat error: {token_data.get('errmsg')}")

        return TokenResponse(
            access_token=token_data['access_token'],
            token_type='Bearer',
            expires_in=token_data.get('expires_in', 7200)
        )

    async def get_user_info(self, access_token: str, code: str):
        # 1. 通过code获取用户ID
        userinfo_params = {
            'access_token': access_token,
            'code': code
        }

        async with httpx.AsyncClient() as client:
            userinfo_response = await client.get(self.userinfo_endpoint, params=userinfo_params)

        userinfo_data = userinfo_response.json()
        if userinfo_data.get('errcode') != 0:
            raise UserInfoError(f"WeChat userinfo error: {userinfo_data.get('errmsg')}")

        userid = userinfo_data.get('UserId')
        if not userid:
            raise UserInfoError("No UserId in WeChat response")

        # 2. 获取用户详细信息
        user_detail_params = {
            'access_token': access_token,
            'userid': userid
        }

        detail_response = await client.get(self.user_detail_endpoint, params=user_detail_params)
        detail_data = detail_response.json()

        if detail_data.get('errcode') != 0:
            raise UserInfoError(f"WeChat user detail error: {detail_data.get('errmsg')}")

        return {
            'id': userid,
            'name': detail_data.get('name'),
            'email': detail_data.get('email'),
            'mobile': detail_data.get('mobile'),
            'department': detail_data.get('department', []),
            'position': detail_data.get('position'),
            'avatar': detail_data.get('avatar'),
            'status': detail_data.get('status'),
            'provider': 'wechat'
        }
```

## 6. 配置管理界面

### 6.1 OAuth 提供商配置API

```python
@router.post("/tenants/{tenant_bid}/oauth/providers")
async def create_oauth_provider(tenant_bid: str, request: CreateOAuthProviderRequest):
    """创建OAuth提供商配置"""
    # 验证租户权限
    await permission_service.check_permission(
        current_user.user_bid, tenant_bid, 'settings', 'write'
    )

    # 验证配置参数
    await oauth_service.validate_provider_config(request)

    provider = await oauth_service.create_provider(tenant_bid, request)
    return {"data": provider}

@router.put("/tenants/{tenant_bid}/oauth/providers/{provider_bid}")
async def update_oauth_provider(tenant_bid: str, provider_bid: str, request: UpdateOAuthProviderRequest):
    """更新OAuth提供商配置"""
    provider = await oauth_service.update_provider(provider_bid, request)
    return {"data": provider}

@router.post("/tenants/{tenant_bid}/oauth/providers/{provider_bid}/test")
async def test_oauth_provider(tenant_bid: str, provider_bid: str):
    """测试OAuth提供商配置"""
    test_result = await oauth_service.test_provider_configuration(provider_bid)
    return {"data": test_result}

class CreateOAuthProviderRequest(BaseModel):
    provider_type: str
    provider_name: str
    display_name: str
    client_id: str
    client_secret: str
    tenant_id: Optional[str] = None  # 用于Microsoft Azure AD
    default_scopes: List[str] = []
    attribute_mapping: Dict[str, str] = {}
    role_mapping: Dict[str, List[str]] = {}
    is_enabled: bool = True
    is_default: bool = False
    auto_create_user: bool = True
```

### 6.2 用户属性映射配置

```python
class AttributeMappingService:
    """用户属性映射服务"""

    def get_default_mapping(self, provider_type: str) -> dict:
        """获取默认属性映射"""
        mappings = {
            'google': {
                'email': 'email',
                'name': 'name',
                'first_name': 'given_name',
                'last_name': 'family_name',
                'avatar_url': 'picture',
                'locale': 'locale'
            },
            'microsoft': {
                'email': 'mail',
                'name': 'displayName',
                'first_name': 'givenName',
                'last_name': 'surname',
                'job_title': 'jobTitle',
                'department': 'department',
                'office_location': 'officeLocation'
            },
            'wechat': {
                'email': 'email',
                'name': 'name',
                'mobile': 'mobile',
                'department': 'department.0', # 取第一个部门
                'position': 'position',
                'avatar_url': 'avatar'
            }
        }

        return mappings.get(provider_type, {})

    def get_suggested_role_mapping(self, provider_type: str) -> dict:
        """获取建议的角色映射"""
        role_mappings = {
            'microsoft': {
                'admin': ['IT Administrator', 'System Administrator'],
                'editor': ['Content Creator', 'Manager'],
                'member': ['Employee', 'User']
            },
            'wechat': {
                'admin': ['管理员', '系统管理员'],
                'editor': ['内容创建者', '经理'],
                'member': ['员工', '用户']
            }
        }

        return role_mappings.get(provider_type, {})
```

## 7. 安全考虑

### 7.1 OAuth 安全最佳实践

**PKCE (Proof Key for Code Exchange)**
```python
def generate_code_verifier():
    """生成PKCE code verifier"""
    return base64url_encode(os.urandom(32))

def generate_code_challenge(code_verifier: str):
    """生成PKCE code challenge"""
    digest = hashlib.sha256(code_verifier.encode('utf-8')).digest()
    return base64url_encode(digest)
```

**状态参数验证**
- 使用加密安全的随机数生成状态参数
- 状态参数有效期限制（10分钟）
- 防止CSRF攻击

**令牌安全存储**
- 访问令牌和刷新令牌加密存储
- 定期轮换加密密钥
- 令牌最小权限原则

### 7.2 会话管理安全

```python
class SecureSessionManager:
    async def create_session(self, user_bid: str, tenant_bid: str, provider_type: str):
        session_data = {
            'user_bid': user_bid,
            'tenant_bid': tenant_bid,
            'provider_type': provider_type,
            'created_at': datetime.utcnow().isoformat(),
            'last_activity': datetime.utcnow().isoformat()
        }

        # 生成JWT token
        token = jwt.encode(
            payload=session_data,
            key=self.get_signing_key(),
            algorithm='HS256',
            headers={'tenant_bid': tenant_bid}
        )

        # 设置安全Cookie
        response.set_cookie(
            'auth_token',
            token,
            max_age=86400,  # 24小时
            httponly=True,
            secure=True,
            samesite='strict'
        )

        return token
```

## 8. 监控和分析

### 8.1 OAuth 流程监控

**关键指标**
- OAuth流程成功率
- 提供商响应时间
- 用户创建成功率
- 令牌刷新失败率

**告警配置**
```python
class OAuthMonitoringService:
    async def track_oauth_flow(self, tenant_bid: str, provider_type: str,
                              step: str, status: str, duration: float = None):
        metrics = {
            'tenant_bid': tenant_bid,
            'provider_type': provider_type,
            'step': step,  # initiate, callback, token_exchange, user_info
            'status': status,  # success, failure, error
            'duration_ms': duration,
            'timestamp': datetime.utcnow()
        }

        # 发送到监控系统
        await self.metrics_client.send('oauth_flow', metrics)

        # 检查错误率阈值
        if status == 'failure':
            error_rate = await self.calculate_error_rate(provider_type)
            if error_rate > 0.1:  # 10%错误率
                await self.send_alert(f"High OAuth error rate for {provider_type}: {error_rate:.2%}")
```

### 8.2 用户登录分析

```python
class LoginAnalyticsService:
    async def track_login_event(self, user_bid: str, tenant_bid: str, provider_type: str,
                               source: str, user_agent: str, ip_address: str):
        login_event = {
            'user_bid': user_bid,
            'tenant_bid': tenant_bid,
            'provider_type': provider_type,
            'source': source,  # web, mobile_app
            'user_agent': user_agent,
            'ip_address': ip_address,
            'timestamp': datetime.utcnow(),
            'location': await self.get_location_from_ip(ip_address)
        }

        await self.analytics_client.track('user_login', login_event)

        # 异常登录检测
        await self.detect_anomalous_login(user_bid, login_event)
```

这个OAuth集成架构设计提供了完整的企业级身份认证解决方案，支持主流的OAuth提供商，具备良好的安全性和扩展性，能够满足不同规模企业的SSO需求。
