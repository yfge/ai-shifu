'use client';

import styles from './page.module.scss';

import { useEffect, useState, useCallback } from 'react';
import clsx from 'clsx';
import { useShallow } from 'zustand/react/shallow';
import { useTranslation } from 'react-i18next';

import { useParams } from 'next/navigation';

import {
  calcFrameLayout,
  FRAME_LAYOUT_MOBILE,
  inWechat,
} from '@/c-constants/uiConstants';
import { EVENT_NAMES, events } from './events';

import {
  useEnvStore,
  useCourseStore,
  useUiLayoutStore,
  useSystemStore,
} from '@/c-store';
import { useUserStore } from '@/store';
import { useDisclosure } from '@/c-common/hooks/useDisclosure';
import { useLessonTree } from './hooks/useLessonTree';
import { updateWxcode } from '@/c-api/user';
import { shifu } from '@/c-service/Shifu';

import { Skeleton } from '@/components/ui/Skeleton';
import { AppContext } from './Components/AppContext';
import NavDrawer from './Components/NavDrawer/NavDrawer';
import FeedbackModal from './Components/FeedbackModal/FeedbackModal';
import TrackingVisit from '@/c-components/TrackingVisit';
import ChatUi from './Components/ChatUi/ChatUi';

import ChatMobileHeader from './Components/ChatMobileHeader';
import PayModalM from './Components/Pay/PayModalM';
import PayModal from './Components/Pay/PayModal';

// import LoginModal from './Components/Login/LoginModal';

// the main page of course learning
export default function ChatPage() {
  const { i18n } = useTranslation();

  /**
   * User info and init part
   */
  const userInfo = useUserStore(state => state.userInfo);
  const { isLoggedIn, initUser } = useUserStore(state => state);
  const [initialized, setInitialized] = useState(false);

  const { wechatCode } = useSystemStore(
    useShallow(state => ({ wechatCode: state.wechatCode })),
  );

  const initAndCheckLogin = useCallback(async () => {
    // Initialize user state (automatically handles guest or auth)
    await initUser();

    if (inWechat() && wechatCode && isLoggedIn) {
      await updateWxcode({ wxcode: wechatCode });
    }
    setInitialized(true);
  }, [wechatCode, isLoggedIn, initUser]);

  useEffect(() => {
    initAndCheckLogin();
  }, [initAndCheckLogin]);

  // NOTE: User-related features should be organized into one module
  function gotoLogin() {
    window.location.href = `/login?redirect=${encodeURIComponent(location.pathname)}`;
  }
  // NOTE: Probably don't need this.
  // const [loginModalOpen, setLoginModalOpen] = useState(false);

  /**
   * UI layout part
   */
  const { frameLayout, updateFrameLayout } = useUiLayoutStore(state => state);
  const mobileStyle = frameLayout === FRAME_LAYOUT_MOBILE;

  // check the frame layout
  useEffect(() => {
    const onResize = () => {
      const frameLayout = calcFrameLayout('#root');
      updateFrameLayout(frameLayout);
    };
    window.addEventListener('resize', onResize);
    onResize();
    return () => {
      window.removeEventListener('resize', onResize);
    };
  }, [updateFrameLayout]);

  const {
    open: navOpen,
    onClose: onNavClose,
    onToggle: onNavToggle,
  } = useDisclosure({
    initOpen: mobileStyle ? false : true,
  });

  const { open: feedbackModalOpen, onClose: onFeedbackModalClose } =
    useDisclosure();

  /**
   * Lesson part
   */
  let courseId = '';
  const params = useParams();
  if (params?.id?.[0]) {
    courseId = params.id[0];
  }

  const { updateCourseId } = useEnvStore.getState();

  useEffect(() => {
    const updateCourse = async () => {
      if (courseId) {
        await updateCourseId(courseId);
      }
    };
    updateCourse();
  }, [courseId]);

  const {
    tree,
    selectedLessonId,
    loadTree,
    reloadTree,
    updateSelectedLesson,
    toggleCollapse,
    getCurrElement,
    updateLesson,
    updateChapterStatus,
    getChapterByLesson,
    onTryLessonSelect,
    getNextLessonId,
  } = useLessonTree();

  const [currentLanguage, setCurrentLanguage] = useState(i18n.language);

  useEffect(() => {
    if (tree && i18n.language !== currentLanguage) {
      setCurrentLanguage(i18n.language);
      reloadTree();
    }
  }, [i18n.language, tree, currentLanguage, reloadTree]);

  const { lessonId, updateLessonId, chapterId, updateChapterId, courseName } =
    useCourseStore(
      useShallow(state => ({
        courseName: state.courseName,
        lessonId: state.lessonId,
        updateLessonId: state.updateLessonId,
        chapterId: state.chapterId,
        updateChapterId: state.updateChapterId,
      })),
    );

  useEffect(() => {
    if (selectedLessonId) {
      updateLessonId(selectedLessonId);
    }
  }, [selectedLessonId, updateLessonId]);

  const loadData = useCallback(async () => {
    await loadTree(chapterId, lessonId);
  }, [chapterId, lessonId, loadTree]);

  const [loadedChapterId, setLoadedChapterId] = useState<string | null>(null);
  useEffect(() => {
    if (initialized && loadedChapterId !== chapterId) {
      loadData();
      setLoadedChapterId(chapterId);
    }
  }, [chapterId, initialized, loadData, loadedChapterId]);

  // TODO: REMOVE
  // console.log(
  //   'chapterId: ',
  //   chapterId,
  //   'lessonId: ',
  //   lessonId,
  //   'initialized: ',
  //   initialized,
  //   'loadedChapterId: ',
  //   loadedChapterId,
  // );

  const onLessonSelect = ({ id }) => {
    const chapter = getChapterByLesson(id);
    if (!chapter) {
      return;
    }
    updateLessonId(id);
    if (chapter.id !== chapterId) {
      updateChapterId(chapter.id);
    }
    if (lessonId === id) {
      return;
    }
    events.dispatchEvent(
      new CustomEvent(EVENT_NAMES.GO_TO_NAVIGATION_NODE, {
        detail: {
          chapterId: chapter.id,
          lessonId: id,
        },
      }),
    );

    if (mobileStyle) {
      onNavClose();
    }
  };

  const onLessonUpdate = useCallback(
    val => {
      updateLesson(val.id, val);
    },
    [updateLesson],
  );

  const onGoChapter = async id => {
    // updateChapterId(id);
    updateLessonId(id);
  };

  const onChapterUpdate = useCallback(
    ({ id, status, status_value }) => {
      updateChapterStatus(id, { status, status_value });
    },
    [updateChapterStatus],
  );

  const fetchData = useCallback(async () => {
    if (tree) {
      const data = await getCurrElement();
      if (data && data.lesson) {
        updateLessonId(data.lesson.id);
        if (data.catalog) {
          updateChapterId(data.catalog.id);
        }
      }
    }
  }, [tree, getCurrElement, updateLessonId, updateChapterId]);

  useEffect(() => {
    if (initialized) {
      fetchData();
    }
  }, [fetchData, initialized]);

  /**
   * Pay part
   */

  const {
    payModalOpen,
    payModalState,
    openPayModal,
    closePayModal,
    setPayModalResult,
  } = useCourseStore(
    useShallow(state => ({
      payModalOpen: state.payModalOpen,
      payModalState: state.payModalState,
      openPayModal: state.openPayModal,
      closePayModal: state.closePayModal,
      setPayModalResult: state.setPayModalResult,
    })),
  );

  const onPurchased = useCallback(() => {
    reloadTree();
  }, [reloadTree]);

  const _onPayModalCancel = useCallback(
    (_?: unknown) => {
      closePayModal();
      setPayModalResult('cancel');
    },
    [closePayModal, setPayModalResult],
  );

  const _onPayModalOk = useCallback(
    (_?: unknown) => {
      closePayModal();
      setPayModalResult('ok');
      onPurchased();
    },
    [closePayModal, onPurchased, setPayModalResult],
  );

  /**
   * Misc part
   */

  const [userSettingBasicInfo, setUserSettingBasicInfo] = useState(false);
  const [showUserSettings, setShowUserSettings] = useState(false);
  // const [loginOkHandlerData, setLoginOkHandlerData] = useState(null);

  const onGoToSettingBasic = useCallback(() => {
    setUserSettingBasicInfo(true);
    setShowUserSettings(true);
    if (mobileStyle) {
      onNavClose();
    }
  }, [mobileStyle, onNavClose]);

  const onGoToSettingPersonal = useCallback(() => {
    setUserSettingBasicInfo(false);
    setShowUserSettings(true);
    if (mobileStyle) {
      onNavClose();
    }
  }, [mobileStyle, onNavClose]);

  // const onLoginModalClose = useCallback(async () => {
  //   setLoginModalOpen(false);
  //   setLoginOkHandlerData(null);
  //   await loadData();
  //   shifu.loginTools.emitLoginModalCancel();
  // }, [loadData]);

  // const onLoginModalOk = useCallback(async () => {
  //   reloadTree();
  //   shifu.loginTools.emitLoginModalOk();
  //   if (loginOkHandlerData) {
  //     if (loginOkHandlerData.type === 'pay') {
  //       shifu.payTools.openPay({
  //         ...loginOkHandlerData.payload,
  //       });
  //     }

  //     setLoginOkHandlerData(null);
  //   }
  // }, [loginOkHandlerData, reloadTree]);

  // const onFeedbackClick = useCallback(() => {
  //   onFeedbackModalOpen();
  // }, [onFeedbackModalOpen]);

  // listen global event
  useEffect(() => {
    const resetChapterEventHandler = async e => {
      await reloadTree(e.detail.chapter_id);
      onGoChapter(e.detail.chapter_id);
    };
    const eventHandler = () => {
      // setLoginModalOpen(true);
      gotoLogin();
    };

    shifu.events.addEventListener(
      shifu.EventTypes.OPEN_LOGIN_MODAL,
      eventHandler,
    );

    shifu.events.addEventListener(
      shifu.EventTypes.RESET_CHAPTER,
      resetChapterEventHandler,
    );

    return () => {
      shifu.events.removeEventListener(
        shifu.EventTypes.OPEN_LOGIN_MODAL,
        eventHandler,
      );

      shifu.events.removeEventListener(
        shifu.EventTypes.RESET_CHAPTER,
        resetChapterEventHandler,
      );
    };
  }, [gotoLogin, onGoChapter, reloadTree]);
  return (
    <div className={clsx(styles.newChatPage)}>
      <AppContext.Provider
        value={{ frameLayout, mobileStyle, isLoggedIn, userInfo, theme: '' }}
      >
        {!initialized ? (
          <div className='flex flex-col space-y-6 p-6 container mx-auto'>
            <Skeleton className='h-[125px] rounded-xl' />
            <div className='space-y-4'>
              <Skeleton className='h-6' />
              <Skeleton className='h-6' />
              <Skeleton className='h-6' />
              <Skeleton className='h-6 w-1/3' />
              <Skeleton className='h-6' />
              <Skeleton className='h-6' />
              <Skeleton className='h-6 w-3/4' />
            </div>
          </div>
        ) : null}

        {initialized && navOpen ? (
          <NavDrawer
            courseName={courseName}
            onLoginClick={() => {
              // setLoginModalOpen(true)
              gotoLogin();
            }}
            lessonTree={tree}
            selectedLessonId={selectedLessonId || ''}
            onChapterCollapse={id => toggleCollapse({ id })}
            onLessonSelect={onLessonSelect}
            onTryLessonSelect={onTryLessonSelect}
            onBasicInfoClick={onGoToSettingBasic}
            onPersonalInfoClick={onGoToSettingPersonal}
          />
        ) : null}

        {initialized ? (
          <ChatUi
            lessonId={lessonId}
            chapterId={chapterId}
            lessonUpdate={onLessonUpdate}
            onGoChapter={onGoChapter}
            onPurchased={onPurchased}
            showUserSettings={showUserSettings}
            onUserSettingsClose={() => setShowUserSettings(false)}
            chapterUpdate={onChapterUpdate}
            userSettingBasicInfo={userSettingBasicInfo}
            updateSelectedLesson={updateSelectedLesson}
            getNextLessonId={getNextLessonId}
          />
        ) : null}

        {/* It looks like it's no longer needed. */}
        {/* {loginModalOpen ? (
          <LoginModal
            onLogin={onLoginModalOk}
            open={loginModalOpen}
            onClose={onLoginModalClose}
            destroyOnClose={true}
            onFeedbackClick={onFeedbackClick}
          />
        ) : null} */}

        {payModalOpen && mobileStyle ? (
          <PayModalM
            open={payModalOpen}
            onCancel={_onPayModalCancel}
            onOk={_onPayModalOk}
            type={payModalState.type}
            payload={payModalState.payload}
          />
        ) : null}

        {payModalOpen && !mobileStyle ? (
          <PayModal
            open={payModalOpen}
            onCancel={_onPayModalCancel}
            onOk={_onPayModalOk}
            type={payModalState.type}
            payload={payModalState.payload}
          />
        ) : null}

        {initialized ? <TrackingVisit /> : null}

        {mobileStyle ? (
          <ChatMobileHeader
            navOpen={navOpen}
            className={styles.chatMobileHeader}
            iconPopoverPayload={tree?.bannerInfo}
            onSettingClick={onNavToggle}
          />
        ) : null}

        <FeedbackModal
          open={feedbackModalOpen}
          onClose={onFeedbackModalClose}
        />
      </AppContext.Provider>
    </div>
  );
}
