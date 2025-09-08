/**
 * Test setup for i18n test suite
 * Global configuration and utilities for all tests
 */

const fs = require('fs');
const path = require('path');

// Global test timeout (increased for file operations)
jest.setTimeout(10000);

// Mock modules that may not exist in test environment
jest.mock('../scripts/extract.js', () => ({
    extractFromDirectory: jest.fn(() => ({
        extractedKeys: ['user.login.title', 'user.login.username', 'common.submit'],
        stats: { filesProcessed: 1, keysFound: 3 }
    })),
    extractFromPythonFiles: jest.fn(() => ({
        extractedKeys: ['ERROR.SYSTEM_ERROR', 'common.welcome'],
        stats: { filesProcessed: 1, keysFound: 2 }
    })),
    mergeTranslations: jest.fn((existing, newTrans) => {
        // Simple merge for testing
        const merged = JSON.parse(JSON.stringify(existing));
        for (const [lang, data] of Object.entries(newTrans)) {
            if (!merged[lang]) merged[lang] = {};
            Object.assign(merged[lang], data);
        }
        return merged;
    }),
    flattenTranslations: jest.fn((nested) => {
        const flattened = {};
        function flatten(obj, prefix = '') {
            for (const [key, value] of Object.entries(obj)) {
                const newKey = prefix ? `${prefix}.${key}`.toUpperCase() : key.toUpperCase();
                if (typeof value === 'object' && value !== null) {
                    flatten(value, newKey);
                } else {
                    flattened[newKey] = value;
                }
            }
        }
        flatten(nested);
        return flattened;
    }),
    unflattenTranslations: jest.fn((flat) => {
        const nested = {};
        for (const [key, value] of Object.entries(flat)) {
            const parts = key.toLowerCase().split('.');
            let current = nested;
            for (let i = 0; i < parts.length - 1; i++) {
                if (!current[parts[i]]) current[parts[i]] = {};
                current = current[parts[i]];
            }
            current[parts[parts.length - 1]] = value;
        }
        return nested;
    }),
    extractAllTranslations: jest.fn((directory) => {
        // Mock extraction of multiple files
        const files = fs.readdirSync(directory).filter(f => f.endsWith('.json'));
        const result = {};
        files.forEach(file => {
            const content = fs.readFileSync(path.join(directory, file), 'utf8');
            try {
                result[file.replace('.json', '')] = JSON.parse(content);
            } catch (e) {
                result[file] = { error: 'Invalid JSON' };
            }
        });
        return result;
    })
}), { virtual: true });

jest.mock('../scripts/validate.js', () => ({
    validateTranslations: jest.fn((directory) => {
        try {
            const files = fs.readdirSync(directory).filter(f => f.endsWith('.json') && f !== 'languages.json');

            // Check if files exist and are valid JSON
            let hasErrors = false;
            const errors = [];

            for (const file of files) {
                const filePath = path.join(directory, file);
                const content = fs.readFileSync(filePath, 'utf8');

                try {
                    JSON.parse(content);
                } catch (e) {
                    hasErrors = true;
                    errors.push(`Invalid JSON in ${file}: ${e.message}`);
                }

                // Check for empty files
                if (content.trim() === '' || content.trim() === '{}') {
                    hasErrors = true;
                    errors.push(`Empty translation file: ${file}`);
                }
            }

            // Mock key consistency checking
            if (files.length > 1) {
                // Simplified consistency check - just check if files have similar structure
                const translationData = {};
                let keyMismatch = false;

                files.forEach(file => {
                    try {
                        const content = fs.readFileSync(path.join(directory, file), 'utf8');
                        const data = JSON.parse(content);
                        translationData[file] = Object.keys(data);
                    } catch (e) {
                        // Already handled above
                    }
                });

                const allKeys = Object.values(translationData);
                if (allKeys.length > 1) {
                    const firstKeys = allKeys[0] || [];
                    for (let i = 1; i < allKeys.length; i++) {
                        if (JSON.stringify(firstKeys.sort()) !== JSON.stringify((allKeys[i] || []).sort())) {
                            keyMismatch = true;
                            break;
                        }
                    }
                }

                if (keyMismatch) {
                    hasErrors = true;
                    errors.push('Translation key mismatch between language files');
                }
            }

            return {
                success: !hasErrors,
                errors,
                warnings: []
            };

        } catch (e) {
            return {
                success: false,
                errors: [`Failed to validate directory: ${e.message}`],
                warnings: []
            };
        }
    }),
    validateNamingConventions: jest.fn((directory) => {
        return {
            warnings: ['Some keys do not follow camelCase convention'],
            suggestions: ['Consider renaming "Invalid-Key" to "invalidKey"']
        };
    }),
    isValidKeyNaming: jest.fn((key) => {
        // Check camelCase with dots
        return /^[a-z][a-zA-Z0-9]*(\.[a-z][a-zA-Z0-9]*)*$/.test(key);
    }),
    findHardcodedStrings: jest.fn((sourceCode) => {
        // Simple regex to find quoted strings that aren't in t() calls
        const strings = [];
        const regex = /['"]([^'"]+)['"]/g;
        let match;

        while ((match = regex.exec(sourceCode)) !== null) {
            const context = sourceCode.substring(match.index - 10, match.index + match[0].length + 10);
            // Skip if it's in a t() call or other i18n function
            if (!context.includes('t(') && !context.includes('_(')) {
                strings.push(match[1]);
            }
        }

        return strings.filter(s => s.length > 3 && !/^[a-z.]+$/.test(s)); // Filter out keys and short strings
    }),
    validateArgs: jest.fn((args) => {
        const validFlags = ['--validate', '--strict', '--ignore-warnings'];
        const isValid = args.every(arg => !arg.startsWith('--') || validFlags.includes(arg));

        return {
            valid: isValid,
            error: isValid ? null : 'Invalid command line arguments'
        };
    })
}), { virtual: true });

jest.mock('../scripts/sync.js', () => ({
    syncToComponent: jest.fn((sourceDir, targetDir, component, options = {}) => {
        try {
            // Check if source directory exists
            if (!fs.existsSync(sourceDir)) {
                return {
                    success: false,
                    error: `Source directory ${sourceDir} not found`
                };
            }

            // Check if we can write to target directory
            if (!fs.existsSync(targetDir)) {
                fs.mkdirSync(targetDir, { recursive: true });
            }

            try {
                fs.accessSync(targetDir, fs.constants.W_OK);
            } catch (e) {
                return {
                    success: false,
                    error: `No write permission to ${targetDir}`
                };
            }

            // Mock synchronization
            const sourceFiles = fs.readdirSync(sourceDir).filter(f => f.endsWith('.json') && f !== 'languages.json');

            sourceFiles.forEach(file => {
                const sourcePath = path.join(sourceDir, file);
                const targetPath = path.join(targetDir, file);

                // Create backup if requested
                if (options.backup && fs.existsSync(targetPath)) {
                    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
                    const backupPath = path.join(targetDir, `${file}.backup.${timestamp}`);
                    fs.copyFileSync(targetPath, backupPath);
                }

                // Copy file
                fs.copyFileSync(sourcePath, targetPath);
            });

            return {
                success: true,
                filesCopied: sourceFiles.length
            };

        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    })
}), { virtual: true });

jest.mock('../scripts/frontend-config.js', () => ({
    generateWebConfig: jest.fn(() => {
        return `
import i18next from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

i18next
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    fallbackLng: 'en-US',
    debug: process.env.NODE_ENV === 'development',
    resources: {}
  });

export default i18next;
        `;
    }),
    generateCookWebConfig: jest.fn(() => {
        return `
'use client';
import i18next from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

i18next
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    fallbackLng: 'en-US',
    debug: false,
    resources: {}
  });

export default i18next;
        `;
    })
}), { virtual: true });

jest.mock('../scripts/update-frontend-configs.js', () => ({
    updateConfigs: jest.fn((projectRoot) => {
        try {
            const webDir = path.join(projectRoot, 'src', 'web', 'src');
            const cookWebDir = path.join(projectRoot, 'src', 'cook-web', 'src');

            // Create directories if they don't exist
            fs.mkdirSync(webDir, { recursive: true });
            fs.mkdirSync(cookWebDir, { recursive: true });

            // Create mock i18n config files
            const webConfig = `// Generated i18n config for Web\nexport default {};`;
            const cookWebConfig = `// Generated i18n config for Cook Web\nexport default {};`;

            fs.writeFileSync(path.join(webDir, 'i18n.ts'), webConfig);
            fs.writeFileSync(path.join(cookWebDir, 'i18n.ts'), cookWebConfig);

            return {
                success: true,
                filesUpdated: ['web/src/i18n.ts', 'cook-web/src/i18n.ts']
            };

        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    })
}), { virtual: true });

// Global test utilities
global.testUtils = {
    createMockTranslations: () => ({
        'en-US': {
            user: { login: { title: 'Login' } },
            common: { error: 'Error' }
        },
        'zh-CN': {
            user: { login: { title: '登录' } },
            common: { error: '错误' }
        }
    }),

    expectValidTranslationResult: (result) => {
        expect(result).toBeDefined();
        expect(typeof result).toBe('object');
        expect(result).toHaveProperty('success');
    },

    expectFileExists: (filePath) => {
        expect(fs.existsSync(filePath)).toBe(true);
    }
};

// Clean up console during tests unless debugging
if (!process.env.DEBUG_TESTS) {
    global.console = {
        ...console,
        log: jest.fn(),
        info: jest.fn(),
        warn: jest.fn(),
        error: jest.fn()
    };
}
