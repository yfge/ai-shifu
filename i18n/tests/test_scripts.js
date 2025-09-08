/**
 * Unit tests for i18n scripts and utilities
 * Tests validation, extraction, synchronization, and other utility functions
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');
const { createWriteStream } = require('fs');
const os = require('os');

// Mock console methods for testing
const originalConsole = { ...console };
let mockConsoleOutput = [];

function mockConsole() {
    mockConsoleOutput = [];
    console.log = (...args) => mockConsoleOutput.push(['log', ...args]);
    console.info = (...args) => mockConsoleOutput.push(['info', ...args]);
    console.warn = (...args) => mockConsoleOutput.push(['warn', ...args]);
    console.error = (...args) => mockConsoleOutput.push(['error', ...args]);
}

function restoreConsole() {
    Object.assign(console, originalConsole);
}

function getConsoleOutput(type = null) {
    if (type) {
        return mockConsoleOutput.filter(entry => entry[0] === type);
    }
    return mockConsoleOutput;
}

// Test utilities
function createTempDir() {
    const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'i18n-test-'));
    return tempDir;
}

function createTestTranslationFiles(tempDir) {
    const testTranslations = {
        'en-US': {
            user: {
                login: {
                    title: 'Login',
                    username: 'Username',
                    password: 'Password'
                },
                profile: {
                    title: 'Profile',
                    name: 'Name'
                }
            },
            common: {
                error: 'An error occurred',
                success: 'Success',
                loading: 'Loading...'
            }
        },
        'zh-CN': {
            user: {
                login: {
                    title: '登录',
                    username: '用户名',
                    password: '密码'
                },
                profile: {
                    title: '个人资料',
                    name: '姓名'
                }
            },
            common: {
                error: '发生错误',
                success: '成功',
                loading: '加载中...'
            }
        }
    };

    const filePaths = {};
    for (const [lang, data] of Object.entries(testTranslations)) {
        const filePath = path.join(tempDir, `${lang}.json`);
        fs.writeFileSync(filePath, JSON.stringify(data, null, 2));
        filePaths[lang] = filePath;
    }

    // Create languages.json
    const languagesConfig = {
        supportedLanguages: [
            { code: 'en-US', name: 'English (US)' },
            { code: 'zh-CN', name: '中文 (简体)' }
        ]
    };
    const languagesPath = path.join(tempDir, 'languages.json');
    fs.writeFileSync(languagesPath, JSON.stringify(languagesConfig, null, 2));
    filePaths.languages = languagesPath;

    return { filePaths, testTranslations };
}

function cleanupTempDir(tempDir) {
    try {
        fs.rmSync(tempDir, { recursive: true, force: true });
    } catch (error) {
        // Ignore cleanup errors
    }
}

// Test suite for validation script
describe('Translation Validation Script', () => {
    let tempDir;
    let originalCwd;

    beforeEach(() => {
        tempDir = createTempDir();
        originalCwd = process.cwd();
        mockConsole();
    });

    afterEach(() => {
        cleanupTempDir(tempDir);
        process.chdir(originalCwd);
        restoreConsole();
    });

    test('should validate correct translation files', () => {
        const { filePaths } = createTestTranslationFiles(tempDir);

        // Load and run validation logic
        const validateFunction = require('../scripts/validate.js');

        const result = validateFunction.validateTranslations(tempDir);
        expect(result.success).toBe(true);
        expect(result.errors).toHaveLength(0);
    });

    test('should detect missing translation keys', () => {
        const tempDir = createTempDir();

        // Create files with missing keys
        fs.writeFileSync(path.join(tempDir, 'en-US.json'), JSON.stringify({
            user: { login: { title: 'Login', username: 'Username' } },
            common: { error: 'Error' }
        }, null, 2));

        fs.writeFileSync(path.join(tempDir, 'zh-CN.json'), JSON.stringify({
            user: { login: { title: '登录' } }, // Missing username
            common: { error: '错误', success: '成功' } // Extra success key
        }, null, 2));

        const validateFunction = require('../scripts/validate.js');
        const result = validateFunction.validateTranslations(tempDir);

        expect(result.success).toBe(false);
        expect(result.errors.some(error => error.includes('missing'))).toBe(true);
    });

    test('should detect invalid JSON format', () => {
        const tempDir = createTempDir();

        // Create invalid JSON file
        fs.writeFileSync(path.join(tempDir, 'en-US.json'), '{"invalid": json}');

        const validateFunction = require('../scripts/validate.js');
        const result = validateFunction.validateTranslations(tempDir);

        expect(result.success).toBe(false);
        expect(result.errors.some(error => error.includes('JSON'))).toBe(true);
    });

    test('should validate naming conventions', () => {
        const tempDir = createTempDir();

        // Create file with invalid naming
        fs.writeFileSync(path.join(tempDir, 'en-US.json'), JSON.stringify({
            'Invalid-Key': 'value', // Should use camelCase
            'user': {
                'Login_Title': 'Login' // Should use camelCase
            }
        }, null, 2));

        const validateFunction = require('../scripts/validate.js');
        const result = validateFunction.validateNamingConventions(tempDir);

        expect(result.warnings.length).toBeGreaterThan(0);
    });
});

// Test suite for extraction script
describe('Translation Extraction Script', () => {
    let tempDir;
    let originalCwd;

    beforeEach(() => {
        tempDir = createTempDir();
        originalCwd = process.cwd();
        mockConsole();
    });

    afterEach(() => {
        cleanupTempDir(tempDir);
        process.chdir(originalCwd);
        restoreConsole();
    });

    test('should extract translations from source files', () => {
        // Create mock source files with i18n calls
        const webSrcDir = path.join(tempDir, 'src', 'web', 'src');
        fs.mkdirSync(webSrcDir, { recursive: true });

        const componentCode = `
            import { useTranslation } from 'react-i18next';

            function LoginComponent() {
                const { t } = useTranslation();
                return (
                    <div>
                        <h1>{t('user.login.title')}</h1>
                        <input placeholder={t('user.login.username')} />
                        <button>{t('common.submit')}</button>
                    </div>
                );
            }
        `;
        fs.writeFileSync(path.join(webSrcDir, 'LoginComponent.js'), componentCode);

        const extractFunction = require('../scripts/extract.js');
        const result = extractFunction.extractFromDirectory(webSrcDir);

        expect(result.extractedKeys).toContain('user.login.title');
        expect(result.extractedKeys).toContain('user.login.username');
        expect(result.extractedKeys).toContain('common.submit');
    });

    test('should merge existing translations', () => {
        const { testTranslations } = createTestTranslationFiles(tempDir);

        const newTranslations = {
            'en-US': {
                newSection: {
                    key1: 'New Value 1',
                    key2: 'New Value 2'
                }
            }
        };

        const extractFunction = require('../scripts/extract.js');
        const merged = extractFunction.mergeTranslations(testTranslations, newTranslations);

        expect(merged['en-US'].user.login.title).toBe('Login'); // Original preserved
        expect(merged['en-US'].newSection.key1).toBe('New Value 1'); // New added
    });

    test('should handle extraction from Python backend files', () => {
        const backendDir = path.join(tempDir, 'backend');
        fs.mkdirSync(backendDir, { recursive: true });

        const pythonCode = `
            from flaskr.i18n import _

            def handle_error():
                return _('ERROR.SYSTEM_ERROR')

            def welcome_user(name):
                return t('common.welcome', name=name)
        `;
        fs.writeFileSync(path.join(backendDir, 'handlers.py'), pythonCode);

        const extractFunction = require('../scripts/extract.js');
        const result = extractFunction.extractFromPythonFiles(backendDir);

        expect(result.extractedKeys).toContain('ERROR.SYSTEM_ERROR');
        expect(result.extractedKeys).toContain('common.welcome');
    });
});

// Test suite for synchronization script
describe('Translation Synchronization Script', () => {
    let tempDir;
    let originalCwd;

    beforeEach(() => {
        tempDir = createTempDir();
        originalCwd = process.cwd();
        mockConsole();
    });

    afterEach(() => {
        cleanupTempDir(tempDir);
        process.chdir(originalCwd);
        restoreConsole();
    });

    test('should sync translations to web frontend', () => {
        const { testTranslations } = createTestTranslationFiles(tempDir);

        // Create target directory structure
        const webLocalesDir = path.join(tempDir, 'target', 'web', 'public', 'locales');
        fs.mkdirSync(webLocalesDir, { recursive: true });

        const syncFunction = require('../scripts/sync.js');
        const result = syncFunction.syncToComponent(tempDir, webLocalesDir, 'web');

        expect(result.success).toBe(true);
        expect(fs.existsSync(path.join(webLocalesDir, 'en-US.json'))).toBe(true);
        expect(fs.existsSync(path.join(webLocalesDir, 'zh-CN.json'))).toBe(true);

        // Verify content
        const syncedContent = JSON.parse(fs.readFileSync(path.join(webLocalesDir, 'en-US.json'), 'utf8'));
        expect(syncedContent.user.login.title).toBe('Login');
    });

    test('should sync translations to cook-web', () => {
        const { testTranslations } = createTestTranslationFiles(tempDir);

        const cookWebDir = path.join(tempDir, 'target', 'cook-web', 'public', 'locales');
        fs.mkdirSync(cookWebDir, { recursive: true });

        const syncFunction = require('../scripts/sync.js');
        const result = syncFunction.syncToComponent(tempDir, cookWebDir, 'cook-web');

        expect(result.success).toBe(true);
        expect(fs.existsSync(path.join(cookWebDir, 'en-US.json'))).toBe(true);
    });

    test('should sync translations to backend API', () => {
        const { testTranslations } = createTestTranslationFiles(tempDir);

        const backendDir = path.join(tempDir, 'target', 'api', 'flaskr', 'i18n', 'locales');
        fs.mkdirSync(backendDir, { recursive: true });

        const syncFunction = require('../scripts/sync.js');
        const result = syncFunction.syncToComponent(tempDir, backendDir, 'backend');

        expect(result.success).toBe(true);
        expect(fs.existsSync(path.join(backendDir, 'en-US.json'))).toBe(true);
    });

    test('should handle sync with force option', () => {
        const { testTranslations } = createTestTranslationFiles(tempDir);

        const targetDir = path.join(tempDir, 'target', 'locales');
        fs.mkdirSync(targetDir, { recursive: true });

        // Create existing file with different content
        fs.writeFileSync(path.join(targetDir, 'en-US.json'), JSON.stringify({
            old: { content: 'should be replaced' }
        }, null, 2));

        const syncFunction = require('../scripts/sync.js');
        const result = syncFunction.syncToComponent(tempDir, targetDir, 'test', { force: true });

        expect(result.success).toBe(true);

        const syncedContent = JSON.parse(fs.readFileSync(path.join(targetDir, 'en-US.json'), 'utf8'));
        expect(syncedContent.user).toBeDefined(); // New content should be there
        expect(syncedContent.old).toBeUndefined(); // Old content should be gone
    });

    test('should create backup files when requested', () => {
        const { testTranslations } = createTestTranslationFiles(tempDir);

        const targetDir = path.join(tempDir, 'target', 'locales');
        fs.mkdirSync(targetDir, { recursive: true });

        // Create existing file
        fs.writeFileSync(path.join(targetDir, 'en-US.json'), JSON.stringify({
            existing: { content: 'backup me' }
        }, null, 2));

        const syncFunction = require('../scripts/sync.js');
        const result = syncFunction.syncToComponent(tempDir, targetDir, 'test', { backup: true });

        expect(result.success).toBe(true);

        // Check backup was created
        const backupFiles = fs.readdirSync(targetDir).filter(f => f.includes('.backup.'));
        expect(backupFiles.length).toBeGreaterThan(0);
    });
});

// Test suite for frontend config generation
describe('Frontend Config Generation', () => {
    let tempDir;
    let originalCwd;

    beforeEach(() => {
        tempDir = createTempDir();
        originalCwd = process.cwd();
        mockConsole();
    });

    afterEach(() => {
        cleanupTempDir(tempDir);
        process.chdir(originalCwd);
        restoreConsole();
    });

    test('should generate web frontend i18n config', () => {
        const configGenerator = require('../scripts/frontend-config.js');

        const webConfig = configGenerator.generateWebConfig();

        expect(webConfig).toContain('i18next');
        expect(webConfig).toContain('react-i18next');
        expect(webConfig).toContain('i18next-browser-languagedetector');
        expect(webConfig).toContain('fallbackLng');
    });

    test('should generate cook-web i18n config', () => {
        const configGenerator = require('../scripts/frontend-config.js');

        const cookWebConfig = configGenerator.generateCookWebConfig();

        expect(cookWebConfig).toContain('i18next');
        expect(cookWebConfig).toContain('use client');
        expect(cookWebConfig).toContain('fallbackLng');
    });

    test('should update frontend configs in place', () => {
        // Create mock frontend directories
        const webSrcDir = path.join(tempDir, 'src', 'web', 'src');
        const cookWebSrcDir = path.join(tempDir, 'src', 'cook-web', 'src');
        fs.mkdirSync(webSrcDir, { recursive: true });
        fs.mkdirSync(cookWebSrcDir, { recursive: true });

        const configUpdater = require('../scripts/update-frontend-configs.js');
        const result = configUpdater.updateConfigs(tempDir);

        expect(result.success).toBe(true);
        expect(fs.existsSync(path.join(webSrcDir, 'i18n.ts'))).toBe(true);
        expect(fs.existsSync(path.join(cookWebSrcDir, 'i18n.ts'))).toBe(true);
    });
});

// Test suite for utility functions
describe('I18n Utility Functions', () => {
    let tempDir;

    beforeEach(() => {
        tempDir = createTempDir();
        mockConsole();
    });

    afterEach(() => {
        cleanupTempDir(tempDir);
        restoreConsole();
    });

    test('should flatten nested JSON structure', () => {
        const nestedData = {
            user: {
                login: {
                    title: 'Login',
                    fields: {
                        username: 'Username',
                        password: 'Password'
                    }
                }
            },
            common: {
                buttons: {
                    save: 'Save',
                    cancel: 'Cancel'
                }
            }
        };

        const utilities = require('../scripts/extract.js');
        const flattened = utilities.flattenTranslations(nestedData);

        expect(flattened['USER.LOGIN.TITLE']).toBe('Login');
        expect(flattened['USER.LOGIN.FIELDS.USERNAME']).toBe('Username');
        expect(flattened['COMMON.BUTTONS.SAVE']).toBe('Save');
    });

    test('should unflatten dot-notation keys', () => {
        const flatData = {
            'USER.LOGIN.TITLE': 'Login',
            'USER.LOGIN.USERNAME': 'Username',
            'COMMON.ERROR': 'Error'
        };

        const utilities = require('../scripts/extract.js');
        const nested = utilities.unflattenTranslations(flatData);

        expect(nested.user.login.title).toBe('Login');
        expect(nested.user.login.username).toBe('Username');
        expect(nested.common.error).toBe('Error');
    });

    test('should validate translation key naming conventions', () => {
        const validKeys = ['user.login.title', 'common.error', 'navigation.home'];
        const invalidKeys = ['user-login-title', 'COMMON_ERROR', 'navigation.Home'];

        const utilities = require('../scripts/validate.js');

        validKeys.forEach(key => {
            expect(utilities.isValidKeyNaming(key)).toBe(true);
        });

        invalidKeys.forEach(key => {
            expect(utilities.isValidKeyNaming(key)).toBe(false);
        });
    });

    test('should detect hardcoded strings in source code', () => {
        const sourceCode = `
            function Component() {
                return (
                    <div>
                        <h1>Hardcoded Title</h1>
                        <p>{t('translated.content')}</p>
                        <button>Click me</button>
                        <span>{"Another hardcoded string"}</span>
                    </div>
                );
            }
        `;

        const utilities = require('../scripts/validate.js');
        const hardcoded = utilities.findHardcodedStrings(sourceCode);

        expect(hardcoded).toContain('Hardcoded Title');
        expect(hardcoded).toContain('Click me');
        expect(hardcoded).toContain('Another hardcoded string');
        expect(hardcoded).not.toContain('translated.content');
    });
});

// Test suite for error handling
describe('Script Error Handling', () => {
    let tempDir;

    beforeEach(() => {
        tempDir = createTempDir();
        mockConsole();
    });

    afterEach(() => {
        cleanupTempDir(tempDir);
        restoreConsole();
    });

    test('should handle missing source directories gracefully', () => {
        const nonExistentDir = path.join(tempDir, 'nonexistent');

        const syncFunction = require('../scripts/sync.js');
        const result = syncFunction.syncToComponent(nonExistentDir, tempDir, 'test');

        expect(result.success).toBe(false);
        expect(result.error).toContain('not found');
    });

    test('should handle permission errors gracefully', () => {
        // Create a directory without write permissions
        const restrictedDir = path.join(tempDir, 'restricted');
        fs.mkdirSync(restrictedDir);
        fs.chmodSync(restrictedDir, '444'); // Read-only

        const syncFunction = require('../scripts/sync.js');
        const result = syncFunction.syncToComponent(tempDir, restrictedDir, 'test');

        // Restore permissions for cleanup
        fs.chmodSync(restrictedDir, '755');

        expect(result.success).toBe(false);
        expect(result.error).toContain('permission');
    });

    test('should validate CLI arguments', () => {
        const validateFunction = require('../scripts/validate.js');

        // Test with invalid arguments
        const result = validateFunction.validateArgs(['--invalid-flag']);
        expect(result.valid).toBe(false);
        expect(result.error).toContain('invalid');

        // Test with valid arguments
        const validResult = validateFunction.validateArgs(['--validate']);
        expect(validResult.valid).toBe(true);
    });
});

// Test suite for performance
describe('Script Performance', () => {
    let tempDir;

    beforeEach(() => {
        tempDir = createTempDir();
        mockConsole();
    });

    afterEach(() => {
        cleanupTempDir(tempDir);
        restoreConsole();
    });

    test('should handle large translation files efficiently', () => {
        // Create large translation file
        const largeTranslations = {};
        for (let i = 0; i < 1000; i++) {
            largeTranslations[`section${i}`] = {};
            for (let j = 0; j < 100; j++) {
                largeTranslations[`section${i}`][`key${j}`] = `Value ${i}-${j}`;
            }
        }

        const filePath = path.join(tempDir, 'large-translations.json');
        fs.writeFileSync(filePath, JSON.stringify(largeTranslations, null, 2));

        const startTime = Date.now();

        const validateFunction = require('../scripts/validate.js');
        const result = validateFunction.validateTranslations(tempDir);

        const endTime = Date.now();
        const duration = endTime - startTime;

        expect(result.success).toBe(true);
        expect(duration).toBeLessThan(5000); // Should complete within 5 seconds
    });

    test('should process multiple files concurrently', () => {
        // Create multiple translation files
        for (let i = 0; i < 10; i++) {
            const translations = {
                [`section${i}`]: {
                    key1: `Value ${i}-1`,
                    key2: `Value ${i}-2`
                }
            };
            fs.writeFileSync(path.join(tempDir, `lang${i}.json`), JSON.stringify(translations, null, 2));
        }

        const startTime = Date.now();

        const extractFunction = require('../scripts/extract.js');
        const result = extractFunction.extractAllTranslations(tempDir);

        const endTime = Date.now();
        const duration = endTime - startTime;

        expect(Object.keys(result).length).toBe(10);
        expect(duration).toBeLessThan(3000); // Should be reasonably fast
    });
});

module.exports = {
    mockConsole,
    restoreConsole,
    getConsoleOutput,
    createTempDir,
    createTestTranslationFiles,
    cleanupTempDir
};
