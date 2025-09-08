# AI-Shifu 统一国际化系统

这个目录包含了AI-Shifu项目的统一国际化(i18n)系统，为所有组件提供一致的多语言支持。

## 目录结构

```
i18n/
├── README.md              # 本文档
├── locales/               # 语言文件目录
│   ├── en-US.json        # 英文翻译（主要语言）
│   ├── zh-CN.json        # 中文翻译
│   └── languages.json    # 支持的语言配置
├── schemas/               # 验证规则
│   └── translation-schema.json  # 翻译JSON结构验证
├── scripts/               # 工具脚本
│   ├── validate.js       # 翻译完整性检查
│   ├── sync.js           # 多组件同步
│   └── extract.js        # 从现有系统提取翻译
└── docs/                  # 文档
    ├── naming-convention.md  # 命名规范
    └── integration-guide.md  # 集成指南
```

## 设计原则

### 1. 统一数据格式
- 所有翻译使用嵌套的JSON结构
- 支持变量插值：`{{variable}}`
- 一致的命名规范：`模块.功能.具体项`

### 2. 中心化管理
- 单一数据源：所有翻译内容集中管理
- 自动同步：变更自动同步到各组件
- 版本控制：翻译更改可追踪

### 3. 质量保证
- JSON Schema验证
- 翻译完整性检查
- CI/CD集成检查

## 命名规范

### 模块分类
- `common` - 通用组件（按钮、对话框等）
- `auth` - 认证相关
- `chat` - 聊天功能
- `user` - 用户管理
- `settings` - 设置页面
- `navigation` - 导航菜单
- `error` - 错误信息
- `api` - API错误消息

### 命名格式
```json
{
  "模块": {
    "功能": {
      "具体项": "翻译内容"
    }
  }
}
```

例如：
```json
{
  "auth": {
    "login": {
      "title": "登录",
      "submit": "登录",
      "placeholder": {
        "email": "请输入邮箱",
        "password": "请输入密码"
      }
    }
  }
}
```

## 使用方法

### 前端组件 (React)
```typescript
import { useTranslation } from 'react-i18next';

function LoginComponent() {
  const { t } = useTranslation();

  return (
    <div>
      <h1>{t('auth.login.title')}</h1>
      <button>{t('auth.login.submit')}</button>
    </div>
  );
}
```

### 后端 (Python Flask)
```python
from flaskr.i18n import _

def get_user_message():
    return {
        'message': _('auth.login.success'),
        'error': _('auth.login.failed')
    }
```

## 工具脚本

### 验证翻译完整性
```bash
node i18n/scripts/validate.js
```

### 同步到各组件
```bash
node i18n/scripts/sync.js
```

### 从现有系统提取
```bash
node i18n/scripts/extract.js
```

## 维护指南

1. **添加新翻译**：直接编辑对应的语言JSON文件
2. **修改现有翻译**：更新JSON文件后运行同步脚本
3. **添加新语言**：创建新的语言文件并更新languages.json
4. **验证变更**：使用验证脚本确保翻译完整性

## 注意事项

- 所有翻译键必须在所有语言文件中都有对应的值
- 使用统一的变量插值格式：`{{variable}}`
- 遵循项目的命名规范和代码风格
- 提交前必须通过验证脚本检查
