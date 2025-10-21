import styles from './ChatInputText.module.scss';
import { useEffect, useRef, useState, memo } from 'react';
import { useTranslation } from 'react-i18next';

import { toast } from '@/hooks/useToast';
import {
  INTERACTION_OUTPUT_TYPE,
  INTERACTION_TYPE,
} from '@/c-constants/courseConstants';

import { registerInteractionType } from '../interactionRegistry';
import iconSend from '@/c-assets/newchat/light/icon-send.png';
import Image from 'next/image';

const OUTPUT_TYPE_MAP = {
  [INTERACTION_TYPE.INPUT]: INTERACTION_OUTPUT_TYPE.TEXT,
  [INTERACTION_TYPE.PHONE]: INTERACTION_OUTPUT_TYPE.PHONE,
  [INTERACTION_TYPE.CHECKCODE]: INTERACTION_OUTPUT_TYPE.CHECKCODE,
};

interface ChatInputProps {
  onClick?: (outputType: string, isValid: boolean, value: string) => void;
  type?: string;
  disabled?: boolean;
  initialValue?: string;
  onInputChange?: (value: string) => void;
  props?: {
    content?: {
      content?: string;
    };
  };
}

export const ChatInputText = ({
  onClick,
  initialValue,
  onInputChange,
  type,
  disabled = false,
  props = {},
}: ChatInputProps) => {
  const { t } = useTranslation();
  const [input, setInput] = useState(initialValue || '');

  useEffect(() => {
    setInput(initialValue || '');
  }, [initialValue]);
  const [isComposing, setIsComposing] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const placeholder =
    props?.content?.content || t('module.chat.chatInputPlaceholder');
  // @ts-expect-error EXPECT
  const outputType = OUTPUT_TYPE_MAP[type];

  const onSendClick = async () => {
    if (disabled) {
      return;
    }
    if (input.trim() === '') {
      toast({
        title: t('module.chat.chatInputWarn'),
        variant: 'destructive',
      });
      return;
    }

    onClick?.(outputType, true, input.trim());
    setInput('');

    if (textareaRef.current) {
      textareaRef.current.style.height = '24px';
    }
  };

  const adjustHeight = () => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    const currentValue = textarea.value;
    const currentPlaceholder = textarea.placeholder;

    const wasDisabled = textarea.disabled;
    if (wasDisabled) {
      textarea.disabled = false;
    }

    if (!currentValue) {
      textarea.value = currentPlaceholder;
    }

    textarea.style.height = 'auto';
    const computed = window.getComputedStyle(textarea);
    const padding =
      parseFloat(computed.paddingTop) + parseFloat(computed.paddingBottom);
    const newHeight = Math.min(textarea.scrollHeight - padding, 120);
    textarea.style.height = `${newHeight}px`;

    if (!currentValue) {
      textarea.value = '';
      textarea.placeholder = currentPlaceholder;
    }

    if (wasDisabled) {
      textarea.disabled = true;
    }
  };

  useEffect(() => {
    if (textareaRef.current) {
      if (!disabled) {
        textareaRef.current.focus();
      }
      adjustHeight();
    }
  }, [disabled]);

  useEffect(() => {
    adjustHeight();
  }, [placeholder]);

  useEffect(() => {
    adjustHeight();
  }, [input]);

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value;
    setInput(value);
    onInputChange?.(value);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (isComposing) {
      return;
    }

    if (e.key === 'Enter') {
      if (e.shiftKey) {
        return;
      } else {
        e.preventDefault();
        onSendClick();
      }
    }
  };

  return (
    <div className={styles.inputTextWrapper}>
      <div className={styles.inputForm}>
        <div className={styles.inputWrapper}>
          <textarea
            ref={textareaRef}
            rows={1}
            value={input}
            onChange={handleInput}
            placeholder={placeholder}
            className={styles.inputField}
            disabled={disabled}
            onKeyDown={handleKeyDown}
            onCompositionStart={() => setIsComposing(true)}
            onCompositionEnd={() => setIsComposing(false)}
            enterKeyHint='send'
            autoComplete='off'
            spellCheck={false}
            autoCapitalize='off'
            autoCorrect='off'
            data-gramm='false'
            suppressContentEditableWarning={true}
          />
          <Image
            src={iconSend.src}
            width={24}
            height={24}
            alt=''
            className={styles.sendIcon}
            onClick={onSendClick}
          />
        </div>
      </div>
    </div>
  );
};

const ChatInputTextMemo = memo(ChatInputText);
registerInteractionType(INTERACTION_TYPE.INPUT, ChatInputTextMemo);
registerInteractionType(INTERACTION_TYPE.PHONE, ChatInputTextMemo);
registerInteractionType(INTERACTION_TYPE.CHECKCODE, ChatInputTextMemo);
export default ChatInputTextMemo;
