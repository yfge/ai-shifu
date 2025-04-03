import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

interface Variable {
  name: string;
  description: string;
  color: string;
  text: string;
}

interface SolideContnetProps {
    content: string;
    profiles: string[];
}

const mockVariables: Variable[] = [
  { name: 'user.name', description: '用户姓名', color: 'bg-red-100 text-red-800', text: 'red' },
  { name: 'user.age', description: '用户年龄', color: 'bg-blue-100 text-blue-800', text: 'blue' },
  { name: 'date', description: '当前日期', color: 'bg-green-100 text-green-800', text: 'green' },
];

// 将文本中的变量部分转换为 Markdown 代码块
const processContent = (content: string) => {
  // 匹配 {variable} 格式的变量
  const variableRegex = /\{([^}]+)\}/g;
  return content.replace(variableRegex, '`$1`');
};

export default function TextEditor(props: SolideContnetProps) {
  const [content, setContent] = useState('');
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [suggestions, setSuggestions] = useState<Variable[]>([]);
  const [cursorPosition, setCursorPosition] = useState(0);
  const [isEditing, setIsEditing] = useState(false);
  const [suggestionPosition, setSuggestionPosition] = useState({ top: 0, left: 0 });
  const [selectedIndex, setSelectedIndex] = useState(0);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const updateCursorPosition = () => {
    if (textareaRef.current) {
      const position = textareaRef.current.selectionStart;
      setCursorPosition(position);

      // 计算光标在文本区域中的位置
      const text = textareaRef.current.value.substring(0, position);
      const lines = text.split('\n');
      const currentLine = lines[lines.length - 1];
      const lineNumber = lines.length;

      // 创建一个临时的 span 元素来计算文本宽度
      const span = document.createElement('span');
      span.style.visibility = 'hidden';
      span.style.position = 'absolute';
      span.style.whiteSpace = 'pre';
      span.style.font = window.getComputedStyle(textareaRef.current).font;
      span.textContent = currentLine;
      document.body.appendChild(span);

      const rect = textareaRef.current.getBoundingClientRect();
      const lineHeight = parseInt(window.getComputedStyle(textareaRef.current).lineHeight);
      const paddingTop = parseInt(window.getComputedStyle(textareaRef.current).paddingTop);
      const paddingLeft = parseInt(window.getComputedStyle(textareaRef.current).paddingLeft);

      setSuggestionPosition({
        top: rect.top + paddingTop + (lineNumber * lineHeight),
        left: rect.left + paddingLeft + span.offsetWidth
      });

      document.body.removeChild(span);
    }
  };

  const insertVariable = (variable: Variable) => {
    const textBeforeCursor = content.substring(0, cursorPosition);
    const textAfterCursor = content.substring(cursorPosition);
    const newContent = textBeforeCursor + variable.name + '}' + textAfterCursor;
    setContent(newContent);
    setShowSuggestions(false);

    // 更新光标位置到变量名之后
    setTimeout(() => {
      if (textareaRef.current) {
        const newCursorPos = cursorPosition + variable.name.length + 1;
        textareaRef.current.setSelectionRange(newCursorPos, newCursorPos);
        setCursorPosition(newCursorPos);
      }
    }, 0);
  };

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value;
    setContent(value);
    updateCursorPosition();

    // 检查是否输入了 {
    const textBeforeCursor = value.substring(0, cursorPosition);
    const lastChar = textBeforeCursor[textBeforeCursor.length - 1];

    if (lastChar === '{') {
      setShowSuggestions(true);
      setSuggestions(mockVariables);
      setSelectedIndex(0);
    } else {
      setShowSuggestions(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (showSuggestions) {
      switch (e.key) {
        case 'ArrowUp':
          e.preventDefault();
          setSelectedIndex(prev => (prev > 0 ? prev - 1 : suggestions.length - 1));
          break;
        case 'ArrowDown':
          e.preventDefault();
          setSelectedIndex(prev => (prev < suggestions.length - 1 ? prev + 1 : 0));
          break;
        case 'Enter':
        case 'Tab':
          e.preventDefault();
          if (suggestions[selectedIndex]) {
            insertVariable(suggestions[selectedIndex]);
          }
          break;
        case 'Escape':
          e.preventDefault();
          setShowSuggestions(false);
          break;
      }
    }
  };

  const handleClick = () => {
    setIsEditing(true);
    updateCursorPosition();
  };

  const handleBlur = () => {
    // 延迟关闭下拉菜单，以便能够点击选择
    setTimeout(() => {
      setIsEditing(false);
      setShowSuggestions(false);
    }, 200);
  };

  const renderContent = () => {
    if (isEditing) {
      return (
        <div className="relative">
          <textarea
            ref={textareaRef}
            value={content}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            onBlur={handleBlur}
            onClick={handleClick}
            onKeyUp={updateCursorPosition}
            className="w-full h-64 p-4 border rounded font-mono"
          />
          {showSuggestions && (
            <div
              className="fixed z-10 bg-white border rounded shadow-lg w-64"
              style={{
                top: `${suggestionPosition.top}px`,
                left: `${suggestionPosition.left}px`
              }}
            >
              {suggestions.map((suggestion, index) => (
                <div
                  key={suggestion.name}
                  className={`p-2 hover:bg-gray-100 cursor-pointer ${
                    index === selectedIndex ? 'bg-blue-50' : ''
                  }`}
                  onClick={() => insertVariable(suggestion)}
                >
                  <div className="flex items-center">
                    <div className={`w-3 h-3 rounded-full mr-2 ${suggestion.color}`}></div>
                    <div className="font-bold">{suggestion.name}</div>
                  </div>
                  <div className="text-sm text-gray-500 ml-5">{suggestion.description}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      );
    }

    return (
      <div
        className="w-full h-64 p-4 border rounded cursor-pointer font-mono"
        onClick={handleClick}
      >
        <ReactMarkdown
          components={{
            code({node, className, children, ...props}) {
              // 检查是否是变量（没有语言标记的代码块）
              if (!className) {
                const variable = mockVariables.find(v => v.name === String(children));
                return (
                  <span className={`${variable?.color || 'bg-blue-100 text-blue-800'} px-1 py-0.5 rounded`}>
                    {children}
                  </span>
                );
              }

              const match = /language-(\w+)/.exec(className || '');
              return match ? (
                <SyntaxHighlighter
                  style={vscDarkPlus as any}
                  language={match[1]}
                  PreTag="div"
                  {...props}
                >
                  {String(children).replace(/\n$/, '')}
                </SyntaxHighlighter>
              ) : (
                <code className={className} {...props}>
                  {children}
                </code>
              );
            }
          }}
        >
          {processContent(content)}
        </ReactMarkdown>
      </div>
    );
  };

  return (
    <div className="container mx-auto p-4">
      {renderContent()}
    </div>
  );
}
