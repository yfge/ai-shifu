import styles from './NavBody.module.scss';

import { memo } from 'react';
import { useTranslation } from 'react-i18next';
import { cn } from '@/lib/utils';

import { Button } from '@/components/ui/Button';

import LogoWithText from '@/c-components/logo/LogoWithText';

export const NavBody = ({ onLoginClick = () => {} }) => {
  const { t } = useTranslation();
  return (
    <div className={styles.navBody}>
      <LogoWithText
        size={100}
        direction='col'
      />
      <div className={styles.btnWrapper}>
        <Button
          className={cn('w-48')}
          onClick={() => onLoginClick?.()}
        >
          {t('module.user.loginMainButton')}
        </Button>
      </div>
    </div>
  );
};

export default memo(NavBody);
