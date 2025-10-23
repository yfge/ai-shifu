import './ForkChatUI/styles/index.scss';
import styles from './ChatComponents.module.scss';

import {
  useEffect,
  forwardRef,
  useImperativeHandle,
  useState,
  useContext,
  useRef,
  memo,
  useCallback,
} from 'react';
import { cn } from '@/lib/utils';

import useMessages from './ForkChatUI/hooks/useMessages';
import { Chat } from './ForkChatUI/components/Chat';
import { useChatComponentsScroll } from './ChatComponents/useChatComponentsScroll';

import { ThumbsUp, ThumbsDown } from 'lucide-react';

import {
  runScript,
  getLessonStudyRecord,
  scriptContentOperation,
} from '@/c-api/study';
import { genUuid } from '@/c-utils/common';
import ChatInteractionArea from './ChatInput/ChatInteractionArea';
import { AppContext } from '@/c-components/AppContext';

import { useCourseStore } from '@/c-store/useCourseStore';
import {
  LESSON_STATUS_VALUE,
  INTERACTION_TYPE,
  INTERACTION_OUTPUT_TYPE,
  RESP_EVENT_TYPE,
  CHAT_MESSAGE_TYPE,
} from '@/c-constants/courseConstants';

import { useUserStore } from '@/store';
import { fixMarkdown, fixMarkdownStream } from '@/c-utils/markdownUtils';
// TODO: FIXME
// import LoginModal from '../Login/LoginModal';
import { useDisclosure } from '@/c-common/hooks/useDisclosure';

import { tokenTool } from '@/c-service/storeUtil';
import MarkdownBubble from './ChatMessage/MarkdownBubble';
import { useTracking, EVENT_NAMES } from '@/c-common/hooks/useTracking';
// import { useTranslation } from 'react-i18next';
import { useEnvStore } from '@/c-store/envStore';
import { shifu } from '@/c-service/Shifu';
import {
  events,
  EVENT_NAMES as BZ_EVENT_NAMES,
} from '@/app/c/[[...id]]/events';
import ActiveMessageControl from './ChatMessage/ActiveMessageControl';
import { convertKeysToCamelCase } from '@/c-utils/objUtils';
import { useShallow } from 'zustand/react/shallow';

import logoColor120 from '@/c-assets/logos/logo-color-120.png';

const USER_ROLE = {
  TEACHER: '老师',
  STUDENT: '学生',
};

const createMessage = ({
  id = '',
  role,
  content,
  interaction_type,
  logid,
  type = CHAT_MESSAGE_TYPE.TEXT,
  teach_avator,
}) => {
  const mid = id || genUuid();
  if (type === CHAT_MESSAGE_TYPE.LESSON_SEPARATOR) {
    return {
      _id: mid,
      id: mid,
      type: CHAT_MESSAGE_TYPE.LESSON_SEPARATOR,
      content: content,
    };
  }
  const position = role === USER_ROLE.STUDENT ? 'right' : 'left';

  let avatar = teach_avator || logoColor120.src;

  if (role === USER_ROLE.STUDENT) {
    avatar = null;
  }
  return {
    _id: mid,
    id: mid,
    role,
    content,
    interaction_type,
    isComplete: false,
    logid,
    type,
    position,
    user: { avatar },
  };
};

const convertMessage = (serverMessage, userInfo, teach_avator) => {
  if (serverMessage.script_type === CHAT_MESSAGE_TYPE.TEXT) {
    return createMessage({
      id: serverMessage.id,
      role: serverMessage.script_role,
      content: fixMarkdown(serverMessage.script_content),
      interaction_type: serverMessage.interaction_type,
      logid: serverMessage.logid,
      type: serverMessage.script_type,
      // userInfo,
      teach_avator,
      // isComplete: true,
    });
  } else if (serverMessage.script_type === CHAT_MESSAGE_TYPE.LESSON_SEPARATOR) {
    return createMessage({
      id: serverMessage.id,
      role: serverMessage.script_role,
      content: { lessonId: serverMessage.lesson_id },
      type: serverMessage.script_type,
      interaction_type: serverMessage.interaction_type,
      logid: serverMessage.logid,
      // userInfo,
      teach_avator,
      // isComplete: true,
    });
  }

  return {};
};

const convertEventInputModal = ({ type, content, script_id }) => {
  const scriptId = script_id;

  if (type === RESP_EVENT_TYPE.PHONE || type === RESP_EVENT_TYPE.CHECKCODE) {
    return {
      type,
      props: { content, scriptId },
    };
  } else if (type === RESP_EVENT_TYPE.INPUT) {
    return {
      type,
      props: { content, scriptId },
    };
  } else if (
    type === RESP_EVENT_TYPE.BUTTONS ||
    type === RESP_EVENT_TYPE.ORDER ||
    type === RESP_EVENT_TYPE.NONBLOCK_ORDER ||
    type === RESP_EVENT_TYPE.REQUIRE_LOGIN
  ) {
    const getBtnType = type => {
      if (type === INTERACTION_TYPE.ORDER) {
        return INTERACTION_TYPE.ORDER;
      }
      if (type === INTERACTION_TYPE.NONBLOCK_ORDER) {
        return INTERACTION_TYPE.NONBLOCK_ORDER;
      }
      if (type === RESP_EVENT_TYPE.REQUIRE_LOGIN) {
        return INTERACTION_TYPE.REQUIRE_LOGIN;
      }

      return INTERACTION_TYPE.CONTINUE;
    };
    const btnType = getBtnType(type);
    const buttons = content.buttons;
    if (buttons.length === 1) {
      return {
        type: btnType,
        props: {
          ...buttons[0],
          scriptId,
        },
      };
    } else {
      return {
        type,
        props: { ...content, scriptId },
      };
    }
  }
};
// TODO: FIXME
export const ChatComponents = forwardRef<any, any>(
  (
    {
      className,
      lessonUpdate,
      onGoChapter = () => {},
      chapterId,
      lessonId,
      onPurchased,
      chapterUpdate,
      updateSelectedLesson,
    },
    ref,
  ) => {
    // const { t } = useTranslation();
    const { trackEvent, trackTrailProgress } = useTracking();
    const { courseId } = useEnvStore.getState();
    const chatId = courseId;

    const [inputDisabled, setInputDisabled] = useState(false);
    const [inputModal, setInputModal] = useState(null);
    const [loadedChapterId, setLoadedChapterId] = useState('');
    const [loadedData, setLoadedData] = useState(false);
    const [isStreaming, setIsStreaming] = useState(false);
    const [initRecords, setInitRecords] = useState([]);
    // lesson id the current message is belong to
    const [messageLessonId, setMessageLessonId] = useState('');

    // action control is register in plugin
    const [showActionControl, setShowActionControl] = useState(false);
    const [actionControlType, setActionControlType] = useState('');
    const [actionControlPayload, setActionControlPayload] = useState({
      type: '',
      val: '',
      scriptId: '',
    });
    const [askButtonState, setAskButtonState] = useState({
      total: 1,
      used: 1,
      askMode: false,
      visible: false,
    });

    const { userInfo, mobileStyle } = useContext(AppContext);
    const chatRef = useRef(null);

    const { updateResetedChapterId } = useCourseStore(
      useShallow(state => ({
        updateResetedChapterId: state.updateResetedChapterId,
      })),
    );

    const { messages, appendMsg, setTyping, updateMsg, resetList, deleteMsg } =
      useMessages([]);

    const {
      // autoScroll,
      onMessageListScroll,
      scrollToLesson,
      scrollToBottom,
    } = useChatComponentsScroll({
      chatRef,
      containerStyle: styles.chatComponents,
      messages,
      appendMsg,
      deleteMsg,
    });

    const lastMsgRef = useRef(null);
    const { initUser, updateUserInfo, refreshUserInfo } = useUserStore(
      useShallow(state => ({
        initUser: state.initUser,
        updateUserInfo: state.updateUserInfo,
        refreshUserInfo: state.refreshUserInfo,
      })),
    );

    const { openPayModal, payModalResult } = useCourseStore(
      useShallow(state => ({
        openPayModal: state.openPayModal,
        payModalResult: state.payModalResult,
      })),
    );

    const onPayModalOpen = useCallback(() => {
      openPayModal();
    }, [openPayModal]);

    const {
      // open: loginModalOpen,
      onOpen: onLoginModalOpen,
      // onClose: onLoginModalClose,
    } = useDisclosure();

    // const _onLoginModalClose = useCallback(() => {
    //   onLoginModalClose();
    //   setInputDisabled(false);
    // }, [onLoginModalClose]);

    const closeActionControl = useCallback(() => {
      setShowActionControl(false);
    }, []);

    const onActionControlComplete = (type, display, val, scriptId) => {
      closeActionControl();
      handleSend(type, display, val, scriptId);
    };

    const getActionControl = () => {
      const Control = shifu.getChatInputActionControls(actionControlType);
      return (
        <Control
          onClose={closeActionControl}
          payload={actionControlPayload}
          onComplete={onActionControlComplete}
        ></Control>
      );
    };

    const initLoadedInteraction = useCallback(ui => {
      const nextInputModal = convertEventInputModal(ui);
      setInputDisabled(false);
      // @ts-expect-error EXPECT
      setInputModal(nextInputModal);
    }, []);

    const lessonUpdateResp = useCallback(
      (response, isEnd, nextStepFunc) => {
        const content = response.content;
        lessonUpdate?.({
          id: content.lesson_id,
          name: content.lesson_name,
          status: content.status,
          status_value: content.status_value,
        });

        if (
          content.status_value === LESSON_STATUS_VALUE.PREPARE_LEARNING &&
          !isEnd
        ) {
          nextStepFunc({
            chatId,
            lessonId: content.lesson_id,
            type: INTERACTION_OUTPUT_TYPE.START,
            val: '',
          });
        }

        if (content.status_value === LESSON_STATUS_VALUE.LEARNING && !isEnd) {
          updateSelectedLesson(content.lesson_id);
        }
      },
      [chatId, lessonUpdate, updateSelectedLesson],
    );

    const nextStep = useCallback(
      ({ chatId, lessonId, val, type, scriptId }) => {
        setAskButtonState(v => ({
          ...v,
          askMode: false,
        }));
        let lastMsg = null;
        let isEnd = false;
        let teach_avator = null;
        let lastLessonId = messageLessonId;
        let lastActiveMsg = null;

        runScript(chatId, lessonId, val, type, scriptId, async response => {
          if (response.type === RESP_EVENT_TYPE.TEACHER_AVATOR) {
            teach_avator = response.content;
          }

          const scriptId = response.script_id;
          if (
            [
              RESP_EVENT_TYPE.TEXT_END,
              RESP_EVENT_TYPE.PHONE,
              RESP_EVENT_TYPE.CHECKCODE,
              RESP_EVENT_TYPE.ORDER,
              RESP_EVENT_TYPE.NONBLOCK_ORDER,
              RESP_EVENT_TYPE.USER_LOGIN,
              RESP_EVENT_TYPE.REQUIRE_LOGIN,
            ].includes(response.type)
          ) {
            trackTrailProgress(scriptId);
          }

          try {
            if (response.type === RESP_EVENT_TYPE.TEXT) {
              if (isEnd) {
                return;
              }
              setIsStreaming(true);
              // @ts-expect-error EXPECT
              if (lastMsg !== null && lastMsg.type === 'text') {
                const currText = fixMarkdownStream(
                  // @ts-expect-error EXPECT
                  lastMsg.content,
                  response.content,
                );
                // @ts-expect-error EXPECT
                lastMsg.content = lastMsg.content + currText;
                // @ts-expect-error EXPECT
                updateMsg(lastMsg.id, lastMsg);
                lastMsgRef.current = lastMsg;
              } else {
                const id = genUuid();
                // @ts-expect-error EXPECT
                lastMsg = createMessage({
                  id: id,
                  type: response.type,
                  role: USER_ROLE.TEACHER,
                  content: response.content,
                  // @ts-expect-error EXPECT
                  userInfo,
                  teach_avator: teach_avator,
                });
                // @ts-expect-error EXPECT
                appendMsg(lastMsg);
                lastMsgRef.current = lastMsg;
              }
            } else if (response.type === RESP_EVENT_TYPE.TEXT_END) {
              setIsStreaming(false);
              setTyping(false);
              if (lastMsg) {
                // @ts-expect-error EXPECT
                lastMsg.isComplete = true;
                if (response.log_id) {
                  // @ts-expect-error EXPECT
                  lastMsg.logid = response.log_id;
                }
                // @ts-expect-error EXPECT
                updateMsg(lastMsg.id, lastMsg);
                // lastMsg = null;
                lastActiveMsg = lastMsg;
                lastMsg = null;
                lastMsgRef.current = null;
              }
              lastMsgRef.current = null;
              if (isEnd) {
                lastMsg = null;
                return;
              }
            } else if (response.type === RESP_EVENT_TYPE.ACTIVE) {
              if (lastActiveMsg) {
                // @ts-expect-error EXPECT
                lastActiveMsg.ext = {
                  // @ts-expect-error EXPECT
                  ...lastActiveMsg.ext,
                  active: convertKeysToCamelCase(response.content),
                };
                // @ts-expect-error EXPECT
                updateMsg(lastActiveMsg.id, lastActiveMsg);
                lastActiveMsg = null;
              }
            } else if (
              response.type === RESP_EVENT_TYPE.INPUT ||
              response.type === RESP_EVENT_TYPE.PHONE ||
              response.type === RESP_EVENT_TYPE.CHECKCODE
            ) {
              if (isEnd) {
                return;
              }
              // @ts-expect-error EXPECT
              setInputModal({ type: response.type, props: response });
              setInputDisabled(false);
            } else if (
              response.type === RESP_EVENT_TYPE.BUTTONS ||
              response.type === RESP_EVENT_TYPE.ORDER ||
              response.type === RESP_EVENT_TYPE.NONBLOCK_ORDER ||
              response.type === RESP_EVENT_TYPE.REQUIRE_LOGIN
            ) {
              if (isEnd) {
                return;
              }
              const model = convertEventInputModal(response);
              // @ts-expect-error EXPECT
              setInputModal(model);
              setInputDisabled(false);
            } else if (response.type === RESP_EVENT_TYPE.LESSON_UPDATE) {
              lessonUpdateResp(response, isEnd, nextStep);

              const content = response.content;

              if (
                content.status_value === LESSON_STATUS_VALUE.PREPARE_LEARNING
              ) {
                const newLessonId = content.lesson_id;
                if (!newLessonId) {
                  return;
                }
                if (newLessonId !== lastLessonId) {
                  // @ts-expect-error EXPECT
                  const msg = createMessage({
                    id: `lesson-${newLessonId}`,
                    type: CHAT_MESSAGE_TYPE.LESSON_SEPARATOR,
                    content: { lessonId: newLessonId },
                  });
                  // @ts-expect-error EXPECT
                  appendMsg(msg);
                  lastLessonId = newLessonId;
                  setMessageLessonId(newLessonId);
                }
              }
            } else if (response.type === RESP_EVENT_TYPE.CHAPTER_UPDATE) {
              const {
                status,
                status_value,
                lesson_id: chapterId,
              } = response.content;
              chapterUpdate?.({ id: chapterId, status, status_value });
              if (status_value === LESSON_STATUS_VALUE.COMPLETED) {
                isEnd = true;
                setTyping(false);
              }
              if (status_value === LESSON_STATUS_VALUE.PREPARE_LEARNING) {
                setInputModal({
                  // @ts-expect-error EXPECT
                  type: INTERACTION_TYPE.NEXT_CHAPTER,
                  props: {
                    label: '下一章',
                    lessonId: chapterId,
                  },
                });
                setInputDisabled(false);
              }
            } else if (response.type === RESP_EVENT_TYPE.USER_LOGIN) {
              await tokenTool.set({
                token: response.content.token,
                faked: true,
              });
              initUser();
            } else if (response.type === RESP_EVENT_TYPE.PROFILE_UPDATE) {
              const content = response.content;
              updateUserInfo({ [content.key]: content.value });
            } else if (response.type === RESP_EVENT_TYPE.ASK_MODE) {
              const content = response.content;
              setAskButtonState({
                used: content.ask_count,
                total: content.ask_limit_count,
                askMode: content.ask_mode,
                visible: content.visible,
              });
            }
          } catch (e) {
            console.log(e);
          }
        });
      },
      [
        appendMsg,
        chapterUpdate,
        initUser,
        lessonUpdateResp,
        messageLessonId,
        setTyping,
        trackTrailProgress,
        updateMsg,
        updateUserInfo,
        userInfo,
      ],
    );

    useEffect(() => {
      if (!loadedData) {
        return;
      }

      scrollToBottom();

      if (!initRecords || initRecords.length === 0) {
        // @ts-expect-error EXPECT
        nextStep({
          chatId,
          lessonId: lessonId,
          type: INTERACTION_OUTPUT_TYPE.START,
          val: '',
        });
      }
      setLoadedData(false);
    }, [chatId, initRecords, lessonId, loadedData, nextStep, scrollToBottom]);

    const resetAndLoadData = useCallback(async () => {
      if (!chapterId) {
        return;
      }
      setIsStreaming(false);
      setTyping(false);
      setInputDisabled(true);
      resetList();
      // @ts-expect-error EXPECT
      setInitRecords(null);

      const resp = await getLessonStudyRecord(chapterId);
      const records = resp?.records || [];
      const teach_avator = resp?.teach_avator || null;
      setInitRecords(records);
      const ui = resp?.ui || null;

      if (records && records.length > 0) {
        let lessonId = '';
        let lastMsg = null;

        records.forEach((v, i) => {
          const newLessonId = v.lesson_id;
          if (newLessonId !== lessonId && !!newLessonId) {
            lessonId = newLessonId;
            appendMsg(
              // @ts-expect-error EXPECT
              convertMessage({
                ...v,
                id: `lesson-${newLessonId}`,
                script_type: CHAT_MESSAGE_TYPE.LESSON_SEPARATOR,
                logid: v.id,
              }),
            );
          }

          if (v.script_type === CHAT_MESSAGE_TYPE.ACTIVE) {
            if (!lastMsg) {
              return;
            }
            // @ts-expect-error EXPECT
            lastMsg.ext = {
              // @ts-expect-error EXPECT
              ...lastMsg.ext,
              active: convertKeysToCamelCase({
                msg: v.script_content,
                ...v.data,
              }),
            };
            // @ts-expect-error EXPECT
            updateMsg(lastMsg.id, lastMsg);
            lastMsg = null;
            return;
          }

          const newMessage = convertMessage(
            {
              ...v,
              id: i,
              script_type: CHAT_MESSAGE_TYPE.TEXT,
              logid: v.id,
            },
            userInfo,
            teach_avator,
          );
          // @ts-expect-error EXPECT
          appendMsg(newMessage);
          // @ts-expect-error EXPECT
          lastMsg = newMessage;
        });

        setMessageLessonId(lessonId);
      }

      if (ui) {
        initLoadedInteraction(ui);
      }
      const askUiContent = resp?.ask_ui?.content;

      if (askUiContent) {
        setAskButtonState({
          used: askUiContent.ask_count,
          total: askUiContent.ask_limit_count,
          askMode: askUiContent.ask_mode,
          visible: askUiContent.visible,
        });
      }

      setLoadedData(true);
      setLoadedChapterId(chapterId);
    }, [
      appendMsg,
      chapterId,
      initLoadedInteraction,
      resetList,
      setTyping,
      updateMsg,
      userInfo,
    ]);

    useEffect(() => {
      if (loadedChapterId !== chapterId) {
        setLoadedChapterId(chapterId);
        resetAndLoadData();
      }
    }, [chapterId, loadedChapterId, resetAndLoadData]);

    useEffect(() => {
      return useCourseStore.subscribe(
        state => state.resetedChapterId,
        curr => {
          if (!curr) {
            return;
          }

          if (curr === loadedChapterId) {
            resetAndLoadData();
            // reset to null
            // @ts-expect-error EXPECT
            updateResetedChapterId(null);
          } else {
            return;
          }
        },
      );
    });

    useEffect(() => {
      return useUserStore.subscribe(
        state => state.isLoggedIn,
        () => {
          setLoadedChapterId(chapterId);
          resetAndLoadData();
        },
      );
    }, [chapterId, resetAndLoadData]);

    useEffect(() => {
      if (window.ztDebug) {
        window.ztDebug.resend = () => {};

        window.ztDebug.resendX = (
          chatId,
          lessonId,
          val,
          type,
          scriptId = null,
        ) => {
          nextStep({
            chatId,
            lessonId,
            val,
            type,
            scriptId,
          });
        };

        window.ztDebug.openPayModal = () => {
          onPayModalOpen();
        };
      }

      return () => {
        if (window.ztDebug) {
          delete window.ztDebug.resend;
        }
      };
    }, [nextStep, onPayModalOpen]);

    const handleSend = useCallback(
      async (type, display, val, scriptId) => {
        if (
          type === INTERACTION_OUTPUT_TYPE.TEXT ||
          type === INTERACTION_OUTPUT_TYPE.SELECT ||
          type === INTERACTION_OUTPUT_TYPE.CONTINUE ||
          type === INTERACTION_OUTPUT_TYPE.PHONE ||
          type === INTERACTION_OUTPUT_TYPE.CHECKCODE ||
          type === INTERACTION_OUTPUT_TYPE.LOGIN ||
          type === INTERACTION_OUTPUT_TYPE.ASK
        ) {
          if (val && typeof val === 'string' && val.trim() && display) {
            const message = createMessage({
              role: USER_ROLE.STUDENT,
              content: val,
              type: CHAT_MESSAGE_TYPE.TEXT,
              // @ts-expect-error EXPECT
              userInfo,
            });
            // @ts-expect-error EXPECT
            await appendMsg(message);
          }
        }

        setTyping(true);
        setInputDisabled(true);
        scrollToBottom();
        nextStep({ chatId, lessonId, type, val, scriptId });
      },
      [
        appendMsg,
        chatId,
        lessonId,
        nextStep,
        scrollToBottom,
        setTyping,
        userInfo,
      ],
    );

    const onPayModalOk = useCallback(() => {
      // @ts-expect-error EXPECT
      handleSend(INTERACTION_OUTPUT_TYPE.ORDER);
      onPurchased?.();
      refreshUserInfo();
    }, [handleSend, onPurchased, refreshUserInfo]);

    useEffect(() => {
      if (payModalResult === 'ok') {
        onPayModalOk();
        setInputDisabled(false);
      }
      if (payModalResult === 'cancel') {
        setInputDisabled(false);
      }
    }, [onPayModalOk, payModalResult]);

    const [interactionTypes, setInteractionTypes] = useState({});

    const renderMessageContentOperation = useCallback(
      msg => {
        const likeClick = async () => {
          setInteractionTypes(prevTypes => {
            const currentType = prevTypes[msg.id] ?? msg.interaction_type;
            const updatedTypes = {
              ...prevTypes,
              [msg.id]: currentType === 1 ? 0 : 1,
            };

            scriptContentOperation(msg.logid, updatedTypes[msg.id]).then(
              () => {},
            );
            return updatedTypes;
          });
        };

        const disClick = async () => {
          setInteractionTypes(prevTypes => {
            const currentType = prevTypes[msg.id] ?? msg.interaction_type;
            const updatedTypes = {
              ...prevTypes,
              [msg.id]: currentType === 2 ? 0 : 2,
            };

            scriptContentOperation(msg.logid, updatedTypes[msg.id]).then(
              () => {},
            );
            return updatedTypes;
          });
        };

        const currentInteractionType =
          interactionTypes[msg.id] ?? msg.interaction_type;

        return (
          <div className={styles.messageContentOperation}>
            {currentInteractionType === 1 ? (
              <ThumbsUp
                className={cn('text-blue-500', 'w-5', 'h-5')}
                onClick={likeClick}
              />
            ) : (
              <ThumbsUp
                className={cn('text-gray-400', 'w-5', 'h-5')}
                onClick={likeClick}
              />
            )}
            {currentInteractionType === 2 ? (
              <ThumbsDown
                className={cn('text-blue-500', 'w-5', 'h-5', 'cursor-pointer')}
                onClick={disClick}
              />
            ) : (
              <ThumbsDown
                className={cn('text-gray-400', 'w-5', 'h-5')}
                onClick={disClick}
              />
            )}
          </div>
        );
      },
      [interactionTypes, setInteractionTypes],
    );

    const renderMessageContent = useCallback(
      msg => {
        const { content, type, ext } = msg;
        if (type === CHAT_MESSAGE_TYPE.LESSON_SEPARATOR) {
          return <></>;
        }

        if (content === undefined) {
          return <></>;
        }
        if (type === CHAT_MESSAGE_TYPE.TEXT) {
          return (
            <div>
              <MarkdownBubble
                content={content}
                isStreaming={isStreaming}
                mobileStyle={mobileStyle}
              />
              {ext?.active && <ActiveMessageControl {...ext.active} />}
              {(msg.isComplete || msg.logid) &&
                msg.position == 'left' &&
                renderMessageContentOperation(msg)}
            </div>
          );
        }
        return <></>;
      },
      [isStreaming, mobileStyle, renderMessageContentOperation],
    );

    const onChatInputSend = useCallback(
      async (type, display, val, scriptId) => {
        if (type === INTERACTION_OUTPUT_TYPE.NEXT_CHAPTER) {
          onGoChapter?.(val.lessonId);
          return;
        }

        if (type === INTERACTION_OUTPUT_TYPE.ORDER) {
          setInputDisabled(true);
          trackEvent(EVENT_NAMES.POP_PAY, { from: 'show-btn' });
          onPayModalOpen();
          return;
        }

        if (type === INTERACTION_OUTPUT_TYPE.REQUIRE_LOGIN) {
          setInputDisabled(true);
          trackEvent(EVENT_NAMES.POP_LOGIN, { from: 'script' });
          onLoginModalOpen();
          return;
        }

        if (
          !(
            type === INTERACTION_OUTPUT_TYPE.TEXT ||
            type === INTERACTION_OUTPUT_TYPE.SELECT ||
            type === INTERACTION_OUTPUT_TYPE.CONTINUE ||
            type === INTERACTION_OUTPUT_TYPE.PHONE ||
            type === INTERACTION_OUTPUT_TYPE.CHECKCODE ||
            type === INTERACTION_OUTPUT_TYPE.LOGIN ||
            type === INTERACTION_OUTPUT_TYPE.ASK
          )
        ) {
          setShowActionControl(true);
          setActionControlType(type);
          setActionControlPayload({
            type,
            val,
            scriptId,
          });

          if (type === INTERACTION_OUTPUT_TYPE.NONBLOCK_ORDER) {
            trackEvent(EVENT_NAMES.POP_PAY, { from: 'show-nb-btn' });
          }
          return;
        }

        handleSend(type, display, val, scriptId);
      },
      [handleSend, onGoChapter, onLoginModalOpen, onPayModalOpen, trackEvent],
    );

    useImperativeHandle(ref, () => ({}));

    const onChatInteractionAreaSizeChange = useCallback(({ height }) => {
      if (!chatRef || !chatRef.current) {
        return;
      }
      // @ts-expect-error EXPECT
      const messageListElem = chatRef.current.querySelector('.MessageList');
      if (!messageListElem) {
        return;
      }

      messageListElem.style.paddingBottom = `${height}px`;
    }, []);

    // const onLogin = useCallback(async () => {
    //   await refreshUserInfo();
    //   handleSend(INTERACTION_OUTPUT_TYPE.LOGIN, false, t('module.chat.loginSuccess'));
    // }, [handleSend, refreshUserInfo, t]);

    useEffect(() => {
      const onGoToNavigationNode = e => {
        const { chapterId, lessonId } = e.detail;

        if (chapterId !== loadedChapterId) {
          return;
        }

        scrollToLesson(lessonId);
        updateSelectedLesson(lessonId);
      };

      events.addEventListener(
        BZ_EVENT_NAMES.GO_TO_NAVIGATION_NODE,
        onGoToNavigationNode,
      );

      return () => {
        events.removeEventListener(
          BZ_EVENT_NAMES.GO_TO_NAVIGATION_NODE,
          onGoToNavigationNode,
        );
      };
    }, [loadedChapterId, scrollToLesson, updateSelectedLesson]);
    useEffect(() => {
      if (lastMsgRef.current) {
        const messageIndex = messages.findIndex(
          // @ts-expect-error EXPECT
          msg => msg.id === lastMsgRef.current.id,
        );
        if (messageIndex === -1) {
          appendMsg(lastMsgRef.current);
        } else if (messageIndex !== messages.length - 1) {
          // @ts-expect-error EXPECT
          deleteMsg(lastMsgRef.current.id);
          appendMsg(lastMsgRef.current);
        }
      }
    }, [messages, appendMsg, deleteMsg]);

    return (
      <div
        className={cn(
          styles.chatComponents,
          className,
          mobileStyle ? styles.mobile : '',
        )}
        ref={chatRef}
      >
        <Chat
          // @ts-expect-error EXPECT
          navbar={null}
          messages={messages}
          renderMessageContent={renderMessageContent}
          recorder={{ canRecord: true }}
          inputOptions={{ disabled: inputDisabled }}
          Composer={() => {
            return <></>;
          }}
          onScroll={onMessageListScroll}
        />

        {inputModal && (
          <ChatInteractionArea
            askButtonState={askButtonState}
            // @ts-expect-error EXPECT
            type={inputModal.type}
            // @ts-expect-error EXPECT
            props={inputModal.props}
            disabled={inputDisabled}
            // @ts-expect-error EXPECT
            onSend={onChatInputSend}
            // @ts-expect-error EXPECT
            onSizeChange={onChatInteractionAreaSizeChange}
          />
        )}
        {/* TODO: FIXME */}
        {/* {loginModalOpen && (
          <LoginModal
            open={loginModalOpen}
            onClose={_onLoginModalClose}
            onLogin={onLogin}
          />
        )} */}
        {showActionControl && getActionControl()}
      </div>
    );
  },
);

ChatComponents.displayName = 'ChatComponents';

export default memo(ChatComponents);
