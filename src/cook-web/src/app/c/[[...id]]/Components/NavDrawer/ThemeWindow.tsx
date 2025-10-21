import PopupModal from '@/c-components/PopupModal';
import { memo } from 'react';
import { useTranslation } from 'react-i18next';

export const ThemeWindow = ({ open, onClose, style, className }) => {
  const { t } = useTranslation();
  return (
    // @ts-expect-error EXPECT
    <PopupModal
      open={open}
      onClose={onClose}
      wrapStyle={{ ...style }}
      className={className}
    >
      <div
        style={{
          display: 'flex',
          height: '100px',
          verticalAlign: 'middle',
          justifyContent: 'center',
          alignItems: 'center',
        }}
      >
        {t('common.core.waitingForCompletion')}
      </div>
    </PopupModal>
  );
};

export default memo(ThemeWindow);
