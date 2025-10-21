'use client';

import type React from 'react';

import { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Label } from '@/components/ui/Label';
import { Loader2 } from 'lucide-react';
import { useToast } from '@/hooks/useToast';
import { TermsCheckbox } from '@/components/TermsCheckbox';
import { isValidPhoneNumber } from '@/lib/validators';
import { useTranslation } from 'react-i18next';
import i18n from '@/i18n';
import { useAuth } from '@/hooks/useAuth';

import type { UserInfo } from '@/c-types';
interface PhoneLoginProps {
  onLoginSuccess: (userInfo: UserInfo) => void;
}

export function PhoneLogin({ onLoginSuccess }: PhoneLoginProps) {
  const { toast } = useToast();
  const [isLoading, setIsLoading] = useState(false);
  const [phoneNumber, setPhoneNumber] = useState('');
  const [phoneOtp, setPhoneOtp] = useState('');
  const [showOtpInput, setShowOtpInput] = useState(false);
  const [termsAccepted, setTermsAccepted] = useState(false);
  const [countdown, setCountdown] = useState(0);
  const [phoneError, setPhoneError] = useState('');
  const { t } = useTranslation();
  const { loginWithSmsCode, sendSmsCode } = useAuth({
    onSuccess: onLoginSuccess,
  });
  const validatePhone = (phone: string) => {
    if (!phone) {
      setPhoneError(t('module.auth.phoneEmpty'));
      return false;
    }

    if (!isValidPhoneNumber(phone)) {
      setPhoneError(t('module.auth.phoneError'));
      return false;
    }

    setPhoneError('');
    return true;
  };

  const handlePhoneChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setPhoneNumber(value);
    if (value) {
      validatePhone(value);
    } else {
      setPhoneError('');
    }
  };

  const handleSendOtp = async () => {
    if (!validatePhone(phoneNumber)) {
      return;
    }

    if (!termsAccepted) {
      toast({
        title: t('module.auth.termsError'),
        variant: 'destructive',
      });
      return;
    }

    try {
      setIsLoading(true);

      const response = await sendSmsCode(phoneNumber, i18n.language);

      if (response.code == 0) {
        setShowOtpInput(true);
        setCountdown(60);
        const timer = setInterval(() => {
          setCountdown(prevCountdown => {
            if (prevCountdown <= 1) {
              clearInterval(timer);
              return 0;
            }
            return prevCountdown - 1;
          });
        }, 1000);

        toast({
          title: t('module.auth.sendSuccess'),
          description: t('module.auth.checkYourSms'),
        });
      }
    } catch {
      // Error already handled in sendSmsCode
    } finally {
      setIsLoading(false);
    }
  };

  const handleVerifyOtp = async () => {
    if (!phoneOtp) {
      toast({
        title: t('module.auth.otpError'),
        variant: 'destructive',
      });
      return;
    }

    if (!termsAccepted) {
      toast({
        title: t('module.auth.termsError'),
        variant: 'destructive',
      });
      return;
    }

    try {
      setIsLoading(true);
      await loginWithSmsCode(phoneNumber, phoneOtp, i18n.language);
    } finally {
      setIsLoading(false);
    }
  };

  const handleOtpKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && showOtpInput && phoneOtp && !isLoading) {
      e.preventDefault();
      handleVerifyOtp();
    }
  };

  return (
    <div className='space-y-4'>
      <div className='space-y-2'>
        <Label
          htmlFor='phone'
          className={phoneError ? 'text-red-500' : ''}
        >
          {t('module.auth.phone')}
        </Label>
        <Input
          id='phone'
          placeholder={t('module.auth.phonePlaceholder')}
          value={phoneNumber}
          onChange={handlePhoneChange}
          disabled={isLoading}
          className={
            phoneError
              ? 'border-red-500 focus-visible:ring-red-500 placeholder:text-muted-foreground'
              : ''
          }
        />
        {phoneError && <p className='text-xs text-red-500'>{phoneError}</p>}
      </div>

      <div className='flex space-x-2'>
        <div className='flex-1'>
          <Input
            id='otp'
            placeholder={t('module.auth.otpPlaceholder')}
            value={phoneOtp}
            onChange={e => setPhoneOtp(e.target.value)}
            onKeyDown={handleOtpKeyDown}
            disabled={isLoading || !showOtpInput}
          />
        </div>
        <Button
          onClick={handleSendOtp}
          disabled={isLoading || countdown > 0 || !phoneNumber || !!phoneError}
          className='whitespace-nowrap h-8'
        >
          {isLoading && !showOtpInput ? (
            <Loader2 className='h-4 w-4 animate-spin mr-2' />
          ) : countdown > 0 ? (
            t('module.auth.secondsLater', { count: countdown })
          ) : (
            t('module.auth.getOtp')
          )}
        </Button>
      </div>

      <div className='mt-2'>
        <TermsCheckbox
          checked={termsAccepted}
          onCheckedChange={setTermsAccepted}
          disabled={isLoading}
        />
      </div>

      {showOtpInput && (
        <Button
          className='w-full h-8'
          onClick={handleVerifyOtp}
          disabled={isLoading || !phoneOtp}
        >
          {isLoading ? <Loader2 className='h-4 w-4 animate-spin mr-2' /> : null}
          {t('module.auth.login')}
        </Button>
      )}
    </div>
  );
}
