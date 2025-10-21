import styles from './NavFooter.module.scss';

import clsx from 'clsx';
import { memo, forwardRef, useImperativeHandle, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { useUserStore } from '@/store';

import { Avatar, AvatarImage } from '@/components/ui/Avatar';

import imgUser from '@/c-assets/newchat/light/user.png';

// @ts-expect-error EXPECT
export const NavFooter = forwardRef(({ onClick, isCollapse = false }, ref) => {
  const { t } = useTranslation();

  const userInfo = useUserStore(state => state.userInfo);
  const isLoggedIn = useUserStore(state => state.isLoggedIn);
  const avatar = userInfo?.avatar || imgUser.src;
  const htmlRef = useRef(null);

  const containElement = elem => {
    // @ts-expect-error EXPECT
    return htmlRef.current && htmlRef.current.contains(elem);
  };
  useImperativeHandle(ref, () => ({
    containElement,
  }));

  return (
    <div
      className={clsx(styles.navFooter, isCollapse ? styles.collapse : '')}
      onClick={onClick}
      ref={htmlRef}
    >
      <div className={styles.userSection}>
        <Avatar className='w-9 h-9'>
          <AvatarImage src={avatar} />
        </Avatar>
        <div className={styles.userName}>
          {isLoggedIn
            ? userInfo?.name || t('module.user.defaultUserName')
            : t('module.user.notLogin')}
        </div>
      </div>
    </div>
  );
});

NavFooter.displayName = 'NavFooter';
export default memo(NavFooter);
