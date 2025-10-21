import { memo, useCallback, useState } from 'react';
import { cn } from '@/lib/utils';
import { useTranslation } from 'react-i18next';

import { useShallow } from 'zustand/react/shallow';
import { useCourseStore } from '@/c-store/useCourseStore';

import { useTracking, EVENT_NAMES } from '@/c-common/hooks/useTracking';
import { shifu } from '@/c-service/Shifu';

import { Button } from '@/components/ui/Button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/Dialog';

export const ResetChapterButton = ({
  className,
  chapterId,
  chapterName,
  lessonId,
  onClick,
  onConfirm,
}) => {
  const { t } = useTranslation();
  const { trackEvent } = useTracking();

  const [showConfirm, setShowConfirm] = useState(false);

  const { resetChapter, updateLessonId } = useCourseStore(
    useShallow(state => ({
      resetChapter: state.resetChapter,
      updateLessonId: state.updateLessonId,
    })),
  );

  const onButtonClick = useCallback(
    async e => {
      setShowConfirm(true);
      // Modal.confirm({
      //   title: t('module.lesson.reset.confirmTitle'),
      //   content: t('module.lesson.reset.confirmContent'),
      //   onOk: async () => {
      //     await resetChapter(chapterId);
      //     updateLessonId(lessonId);
      //     shifu.resetTools.resetChapter({
      //       chapter_id: chapterId,
      //       chapter_name: chapterName,
      //     });
      //     trackEvent(EVENT_NAMES.RESET_CHAPTER_CONFIRM, {
      //       chapter_id: chapterId,
      //       chapter_name: chapterName,
      //     });
      //     onConfirm?.();
      //   },
      // });
      trackEvent(EVENT_NAMES.RESET_CHAPTER, {
        chapter_id: chapterId,
        chapter_name: chapterName,
      });
      e.detail = { chapterId };
      onClick?.(e);
    },
    [chapterId, chapterName, onClick, trackEvent],
    // [chapterId, chapterName, onClick, onConfirm, resetChapter, t, trackEvent, lessonId, updateLessonId]
  );

  async function handleConfirm() {
    await resetChapter(chapterId);
    updateLessonId(lessonId);

    shifu.resetTools.resetChapter({
      chapter_id: chapterId,
      chapter_name: chapterName,
    });

    trackEvent(EVENT_NAMES.RESET_CHAPTER_CONFIRM, {
      chapter_id: chapterId,
      chapter_name: chapterName,
    });

    onConfirm?.();

    setShowConfirm(false);
  }

  return (
    <>
      <Button
        size='sm'
        className={cn(className, 'size-max', 'px-2', 'rounded-full')}
        onClick={onButtonClick}
      >
        {t('module.lesson.reset.title')}
      </Button>
      <Dialog
        open={showConfirm}
        onOpenChange={open => setShowConfirm(open)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('module.lesson.reset.confirmTitle')}</DialogTitle>
            <DialogDescription>
              {t('module.lesson.reset.confirmContent')}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button onClick={handleConfirm}>{t('common.core.ok')}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
};

export default memo(ResetChapterButton);
