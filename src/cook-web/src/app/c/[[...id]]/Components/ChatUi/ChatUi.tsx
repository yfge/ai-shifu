import styles from './ChatUi.module.scss';

import { useContext, memo } from 'react';
import { cn } from '@/lib/utils';
import { useShallow } from 'zustand/react/shallow';
import { useTranslation } from 'react-i18next';

import ChatComponents from './NewChatComp';
import UserSettings from '../Settings/UserSettings';
import { FRAME_LAYOUT_MOBILE } from '@/c-constants/uiConstants';
import GlobalInfoButton from './GlobalInfoButton';
import { useSystemStore } from '@/c-store/useSystemStore';
import { useUiLayoutStore } from '@/c-store';

/**
 * 聊天区的整体画布
 */
export const ChatUi = ({
  chapterId,
  lessonId,
  lessonUpdate,
  onGoChapter,
  onPurchased,
  showUserSettings = true,
  userSettingBasicInfo = false,
  onUserSettingsClose = () => {},
  onMobileSettingClick = () => {},
  chapterUpdate,
  updateSelectedLesson,
  getNextLessonId,
}) => {
  const { frameLayout } = useUiLayoutStore(state => state);
  const { skip, updateSkip, previewMode } = useSystemStore(
    useShallow(state => ({
      skip: state.skip,
      updateSkip: state.updateSkip,
      previewMode: state.previewMode,
    })),
  );
  const { t } = useTranslation();

  const handlePreviewModeClick = () => {
    updateSkip(!skip);
  };

  return (
    <div
      className={cn(
        styles.ChatUi,
        frameLayout === FRAME_LAYOUT_MOBILE ? styles.mobile : '',
      )}
    >
      {
        <ChatComponents
          chapterId={chapterId}
          lessonId={lessonId}
          lessonUpdate={lessonUpdate}
          onGoChapter={onGoChapter}
          className={cn(
            styles.chatComponents,
            showUserSettings ? styles.chatComponentsHidden : '',
          )}
          onPurchased={onPurchased}
          chapterUpdate={chapterUpdate}
          updateSelectedLesson={updateSelectedLesson}
          getNextLessonId={getNextLessonId}
        />
      }
      {showUserSettings && (
        <UserSettings
          className={styles.UserSettings}
          onHomeClick={onUserSettingsClose}
          onClose={onUserSettingsClose}
          isBasicInfo={userSettingBasicInfo}
        />
      )}

      <GlobalInfoButton className={styles.globalInfoButton} />
      {previewMode && (
        <div className={styles.previewMode}>
          <button
            className={cn(styles.previewModeButton, { [styles.active]: skip })}
            onClick={handlePreviewModeClick}
          >
            {skip
              ? t('module.chat.stopAutoSkip')
              : t('module.chat.startAutoSkip')}
          </button>
        </div>
      )}
    </div>
  );
};

export default memo(ChatUi);
