import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ComponentType,
  useContext,
} from 'react';
import { useLatest, useMountedState } from 'react-use';
import { fixMarkdownStream } from '@/c-utils/markdownUtils';
import { useCourseStore } from '@/c-store/useCourseStore';
import { useUserStore } from '@/store';
import { useShallow } from 'zustand/react/shallow';
import {
  StudyRecordItem,
  LikeStatus,
  getRunMessage,
  SSE_INPUT_TYPE,
  getLessonStudyRecord,
  PREVIEW_MODE,
  SSE_OUTPUT_TYPE,
  SYS_INTERACTION_TYPE,
  LIKE_STATUS,
  BLOCK_TYPE,
  BlockType,
} from '@/c-api/studyV2';
import { LESSON_STATUS_VALUE } from '@/c-constants/courseConstants';
import {
  events,
  EVENT_NAMES as BZ_EVENT_NAMES,
} from '@/app/c/[[...id]]/events';
import { EVENT_NAMES } from '@/c-common/hooks/useTracking';
import { OnSendContentParams } from 'markdown-flow-ui';
import LoadingBar from './LoadingBar';
import { useTranslation } from 'react-i18next';
import AskIcon from '@/c-assets/newchat/light/icon_ask.svg';
import { AppContext } from '../AppContext';
import { flushSync } from 'react-dom';

export enum ChatContentItemType {
  CONTENT = 'content',
  INTERACTION = 'interaction',
  ASK = 'ask',
  LIKE_STATUS = 'likeStatus',
}

export interface ChatContentItem {
  content?: string;
  customRenderBar?: (() => JSX.Element | null) | ComponentType<any>;
  defaultButtonText?: string;
  defaultInputText?: string;
  readonly?: boolean;
  isHistory?: boolean;
  generated_block_bid: string;
  ask_generated_block_bid?: string; // use for ask block, because an interaction block gid isn't ask gid
  parent_block_bid?: string; // when like_status is not none, the parent_block_bid is the generated_block_bid of the interaction block
  like_status?: LikeStatus;
  type: ChatContentItemType | BlockType;
  ask_list?: ChatContentItem[]; // list of ask records for this content block
  isAskExpanded?: boolean; // whether the ask panel is expanded
}

interface SSEParams {
  input: string | Record<string, any>;
  input_type: SSE_INPUT_TYPE;
  reload_generated_block_bid?: string;
}

export interface UseChatSessionParams {
  shifuBid: string;
  outlineBid: string;
  lessonId: string;
  chapterId?: string;
  previewMode?: (typeof PREVIEW_MODE)[keyof typeof PREVIEW_MODE];
  trackEvent: (name: string, payload?: Record<string, any>) => void;
  trackTrailProgress: (generatedBlockBid: string) => void;
  lessonUpdate?: (params: Record<string, any>) => void;
  chapterUpdate?: (params: Record<string, any>) => void;
  updateSelectedLesson: (lessonId: string, forceExpand?: boolean) => void;
  getNextLessonId: (lessonId?: string | null) => string | null;
  scrollToLesson: (lessonId: string) => void;
  scrollToBottom: (behavior?: ScrollBehavior) => void;
  showOutputInProgressToast: () => void;
  onPayModalOpen: () => void;
  chatBoxBottomRef: React.RefObject<HTMLDivElement | null>;
  onGoChapter: (lessonId: string) => void;
}

export interface UseChatSessionResult {
  items: ChatContentItem[];
  isLoading: boolean;
  onSend: (content: OnSendContentParams) => void;
  onRefresh: (generatedBlockBid: string) => void;
  onTypeFinished: () => void;
  toggleAskExpanded: (parentBlockBid: string) => void;
}

/**
 * useChatLogicHook orchestrates the streaming chat lifecycle for lesson content.
 */
function useChatLogicHook({
  shifuBid,
  onGoChapter,
  outlineBid,
  lessonId,
  chapterId,
  previewMode,
  trackEvent,
  chatBoxBottomRef,
  trackTrailProgress,
  lessonUpdate,
  chapterUpdate,
  updateSelectedLesson,
  getNextLessonId,
  scrollToLesson,
  scrollToBottom,
  showOutputInProgressToast,
  onPayModalOpen,
}: UseChatSessionParams): UseChatSessionResult {
  const { t, i18n, ready } = useTranslation();
  const { mobileStyle } = useContext(AppContext);

  const { updateUserInfo } = useUserStore(
    useShallow(state => ({
      updateUserInfo: state.updateUserInfo,
    })),
  );
  const { updateResetedChapterId, updateResetedLessonId, resetedLessonId } =
    useCourseStore(
      useShallow(state => ({
        resetedLessonId: state.resetedLessonId,
        updateResetedChapterId: state.updateResetedChapterId,
        updateResetedLessonId: state.updateResetedLessonId,
      })),
    );

  const [contentList, setContentList] = useState<ChatContentItem[]>([]);
  const [isTypeFinished, setIsTypeFinished] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  // const [lastInteractionBlock, setLastInteractionBlock] =
  //   useState<ChatContentItem | null>(null);
  const [loadedChapterId, setLoadedChapterId] = useState('');

  const contentListRef = useRef<ChatContentItem[]>([]);
  const currentContentRef = useRef<string>('');
  const currentBlockIdRef = useRef<string | null>(null);
  const runRef = useRef<((params: SSEParams) => void) | null>(null);
  const sseRef = useRef<any>(null);
  const lastInteractionBlockRef = useRef<ChatContentItem | null>(null);
  const hasScrolledToBottomRef = useRef<boolean>(false);

  const effectivePreviewMode = previewMode ?? PREVIEW_MODE.NORMAL;

  // Use react-use hooks for safer state management
  const isMounted = useMountedState();
  const chatBoxBottomRefLatest = useLatest(chatBoxBottomRef);

  /**
   * Auto scroll to bottom when history records are loaded and rendered
   * Only scroll once, don't interfere with user scrolling
   */
  useEffect(() => {
    // Only scroll once after initial load
    if (hasScrolledToBottomRef.current) {
      return;
    }

    // Wait for: 1) loading complete, 2) has content, 3) chapter loaded
    if (!isLoading && contentList.length > 0 && loadedChapterId) {
      // Simple one-time scroll after a reasonable delay
      const timer = setTimeout(() => {
        if (!isMounted()) return;

        const bottomEl = chatBoxBottomRefLatest.current?.current;
        if (bottomEl) {
          // Use instant scroll to avoid blocking user interaction
          bottomEl.scrollIntoView({
            behavior: 'auto',
            block: 'end',
          });
          hasScrolledToBottomRef.current = true;
        }
      }, 300);

      return () => clearTimeout(timer);
    }
  }, [
    isLoading,
    contentList.length,
    loadedChapterId,
    isMounted,
    chatBoxBottomRefLatest,
  ]);

  /**
   * Keeps the React state and mutable ref of the content list in sync.
   */
  const setTrackedContentList = useCallback(
    (
      updater:
        | ChatContentItem[]
        | ((prev: ChatContentItem[]) => ChatContentItem[]),
    ) => {
      setContentList(prev => {
        const next =
          typeof updater === 'function'
            ? (updater as (prev: ChatContentItem[]) => ChatContentItem[])(prev)
            : updater;
        contentListRef.current = next;
        return next;
      });
    },
    [],
  );

  /**
   * Applies stream-driven lesson status updates and triggers follow-up actions.
   */
  const lessonUpdateResp = useCallback(
    (response, isEnd: boolean) => {
      const {
        outline_bid: currentOutlineBid,
        status,
        title,
      } = response.content;
      lessonUpdate?.({
        id: currentOutlineBid,
        name: title,
        status,
        status_value: status,
      });
      if (status === LESSON_STATUS_VALUE.PREPARE_LEARNING && !isEnd) {
        runRef.current?.({
          input: '',
          input_type: SSE_INPUT_TYPE.NORMAL,
        });
      }

      if (status === LESSON_STATUS_VALUE.LEARNING && !isEnd) {
        updateSelectedLesson(currentOutlineBid);
      }
    },
    [lessonUpdate, updateSelectedLesson],
  );

  /**
   * Starts the SSE request and streams content into the chat list.
   */
  const run = useCallback(
    (sseParams: SSEParams) => {
      sseRef.current?.close();
      setIsTypeFinished(false);

      currentBlockIdRef.current = 'loading';
      currentContentRef.current = '';
      // setLastInteractionBlock(null);
      lastInteractionBlockRef.current = null;
      setTrackedContentList(prev => {
        const placeholderItem: ChatContentItem = {
          generated_block_bid: currentBlockIdRef.current || '',
          content: '',
          customRenderBar: () => <LoadingBar />,
          type: ChatContentItemType.CONTENT,
        };
        return [...prev, placeholderItem];
      });

      let isEnd = false;

      const source = getRunMessage(
        shifuBid,
        outlineBid,
        effectivePreviewMode,
        sseParams,
        async response => {
          try {
            const nid = response.generated_block_bid;
            if (
              currentBlockIdRef.current === 'loading' &&
              response.type !== SSE_OUTPUT_TYPE.VARIABLE_UPDATE
            ) {
              // close loading
              setTrackedContentList(pre => {
                const newList = pre.filter(
                  item => item.generated_block_bid !== 'loading',
                );
                return newList;
              });
              currentBlockIdRef.current = nid;
            }

            const blockId = currentBlockIdRef.current;

            if (nid && [SSE_OUTPUT_TYPE.BREAK].includes(response.type)) {
              trackTrailProgress(nid);
            }

            if (response.type === SSE_OUTPUT_TYPE.INTERACTION) {
              // console.log('🔵 Received INTERACTION type:', response);
              const interactionBlock = {
                generated_block_bid: nid,
                content: response.content,
                customRenderBar: () => null,
                defaultButtonText: '',
                defaultInputText: '',
                readonly: false,
                type: ChatContentItemType.INTERACTION,
              };
              // setLastInteractionBlock(interactionBlock);
              lastInteractionBlockRef.current = interactionBlock;
              // console.log('🔵 Set lastInteractionBlockRef.current:', interactionBlock);
            } else if (response.type === SSE_OUTPUT_TYPE.CONTENT) {
              if (isEnd) {
                return;
              }

              const prevText = currentContentRef.current || '';
              const delta = fixMarkdownStream(prevText, response.content || '');
              const nextText = prevText + delta;
              currentContentRef.current = nextText;
              if (blockId) {
                setTrackedContentList(prevState => {
                  let hasItem = false;
                  const updatedList = prevState.map(item => {
                    if (item.generated_block_bid === blockId) {
                      hasItem = true;
                      return {
                        ...item,
                        content: nextText,
                        customRenderBar: () => null,
                      };
                    }
                    return item;
                  });
                  if (!hasItem) {
                    updatedList.push({
                      generated_block_bid: blockId,
                      content: nextText,
                      defaultButtonText: '',
                      defaultInputText: '',
                      readonly: false,
                      customRenderBar: () => null,
                      type: ChatContentItemType.CONTENT,
                    });
                  }
                  return updatedList;
                });
              }
            } else if (response.type === SSE_OUTPUT_TYPE.OUTLINE_ITEM_UPDATE) {
              if (response.content.has_children) {
                const { status, outline_bid: chapterBid } = response.content;
                chapterUpdate?.({
                  id: chapterBid,
                  status,
                  status_value: status,
                });
                if (status === LESSON_STATUS_VALUE.COMPLETED) {
                  isEnd = true;
                }
              } else {
                // current lesson loading
                if (lessonId === response.content.outline_bid) {
                  currentBlockIdRef.current = 'loading';
                  currentContentRef.current = '';
                  // setLastInteractionBlock(null);
                  lastInteractionBlockRef.current = null;
                  setTrackedContentList(prev => {
                    const placeholderItem: ChatContentItem = {
                      generated_block_bid: currentBlockIdRef.current || '',
                      content: '',
                      customRenderBar: () => <LoadingBar />,
                      type: ChatContentItemType.CONTENT,
                    };
                    return [...prev, placeholderItem];
                  });
                }
                lessonUpdateResp(response, isEnd);
              }
            } else if (
              response.type === SSE_OUTPUT_TYPE.BREAK ||
              response.type === SSE_OUTPUT_TYPE.TEXT_END
            ) {
              // console.log('🟢 Received TEXT_END/BREAK, type:', response.type);
              // console.log('🟢 lastInteractionBlockRef.current:', lastInteractionBlockRef.current);
              if (blockId) {
                setTrackedContentList(prevState => {
                  const updatedList = prevState.map(item =>
                    item.generated_block_bid === blockId
                      ? {
                          ...item,
                          readonly: true,
                          customRenderBar: () => null,
                          isHistory: false,
                        }
                      : item,
                  );
                  return updatedList;
                });

                // Set finished state if no interaction block pending
                if (!lastInteractionBlockRef.current) {
                  setIsTypeFinished(true);
                }
              }
              currentBlockIdRef.current = null;
              currentContentRef.current = '';
            } else if (response.type === SSE_OUTPUT_TYPE.PROFILE_UPDATE) {
              updateUserInfo({
                [response.content.key]: response.content.value,
              });
            }
          } catch (error) {
            console.warn('SSE handling error:', error);
          }
        },
      );
      sseRef.current = source;
    },
    [
      chapterUpdate,
      effectivePreviewMode,
      lessonUpdateResp,
      outlineBid,
      setTrackedContentList,
      shifuBid,
      trackTrailProgress,
      updateUserInfo,
    ],
  );

  useEffect(() => {
    return () => {
      sseRef.current?.close();
    };
  }, []);

  useEffect(() => {
    runRef.current = run;
  }, [run]);

  /**
   * Transforms persisted study records into chat-friendly content items.
   */
  const mapRecordsToContent = useCallback(
    (records: StudyRecordItem[]) => {
      const result: ChatContentItem[] = [];
      let buffer: StudyRecordItem[] = []; // 缓存连续 ask
      let lastContentId: string | null = null;

      const flushBuffer = () => {
        if (buffer.length > 0) {
          const parentId = lastContentId || '';
          result.push({
            generated_block_bid: '',
            type: BLOCK_TYPE.ASK,
            isAskExpanded: false,
            parent_block_bid: parentId,
            ask_list: buffer.map(item => ({
              ...item,
              type: item.block_type,
            })), // 保留原始 ask 列表
            readonly: false,
            isHistory: true,
            customRenderBar: () => null,
            defaultButtonText: '',
            defaultInputText: '',
          });
          buffer = [];
        }
      };

      records.forEach((item: StudyRecordItem) => {
        if (item.block_type === BLOCK_TYPE.CONTENT) {
          // flush 之前缓存的 ask
          flushBuffer();
          result.push({
            generated_block_bid: item.generated_block_bid,
            content:
              item.content +
              (!mobileStyle
                ? ``
                : `<custom-button-after-content><img src="${AskIcon.src}" alt="ask" width="14" height="14" /><span>${t('module.chat.ask')}</span></custom-button-after-content>`),
            customRenderBar: () => null,
            defaultButtonText: item.user_input || '',
            defaultInputText: item.user_input || '',
            readonly: false,
            isHistory: true,
            type: item.block_type,
          });
          lastContentId = item.generated_block_bid;

          if (item.like_status) {
            result.push({
              generated_block_bid: '',
              parent_block_bid: item.generated_block_bid,
              like_status: item.like_status,
              type: ChatContentItemType.LIKE_STATUS,
            });
          }
        } else if (
          item.block_type === BLOCK_TYPE.ASK ||
          item.block_type === BLOCK_TYPE.ANSWER
        ) {
          // 累积 ask
          buffer.push(item);
        } else {
          // flush 并处理其他类型
          flushBuffer();
          result.push({
            generated_block_bid: item.generated_block_bid,
            content: item.content,
            customRenderBar: () => null,
            defaultButtonText: item.user_input || '',
            defaultInputText: item.user_input || '',
            readonly: false,
            isHistory: true,
            type: item.block_type,
          });
        }
      });

      // 最后 flush
      flushBuffer();
      console.log('result:', result);
      return result;
    },
    [mobileStyle],
  );

  /**
   * Loads the persisted lesson records and primes the chat stream.
   */
  const refreshData = useCallback(async () => {
    setTrackedContentList(() => []);

    setIsTypeFinished(true);
    lastInteractionBlockRef.current = null;
    setIsLoading(true);
    hasScrolledToBottomRef.current = false;

    try {
      const recordResp = await getLessonStudyRecord({
        shifu_bid: shifuBid,
        outline_bid: outlineBid,
        preview_mode: effectivePreviewMode,
      });

      if (recordResp?.records?.length > 0) {
        const contentRecords = mapRecordsToContent(recordResp.records);
        setTrackedContentList(contentRecords);
        setIsTypeFinished(true);
        if (chapterId) {
          setLoadedChapterId(chapterId);
        }
        if (
          recordResp.records[recordResp.records.length - 1].block_type ===
            BLOCK_TYPE.CONTENT ||
          recordResp.records[recordResp.records.length - 1].block_type ===
            BLOCK_TYPE.ERROR
        ) {
          runRef.current?.({
            input: '',
            input_type: SSE_INPUT_TYPE.NORMAL,
          });
        }
      } else {
        runRef.current?.({
          input: '',
          input_type: SSE_INPUT_TYPE.NORMAL,
        });
      }
    } catch (error) {
      console.warn('refreshData error:', error);
    } finally {
      setIsLoading(false);
    }
  }, [
    chapterId,
    mapRecordsToContent,
    outlineBid,
    // scrollToBottom,
    setTrackedContentList,
    shifuBid,
    lessonId,
    effectivePreviewMode,
  ]);

  useEffect(() => {
    if (!chapterId) {
      return;
    }
    if (loadedChapterId === chapterId) {
      return;
    }
    setLoadedChapterId(chapterId);
  }, [chapterId, loadedChapterId]);

  useEffect(() => {
    const unsubscribe = useCourseStore.subscribe(
      state => state.resetedLessonId,
      async curr => {
        if (!curr) {
          return;
        }
        setIsLoading(true);
        if (curr === lessonId) {
          sseRef.current?.close();
          await refreshData();
          // updateResetedChapterId(null);
          // @ts-expect-error resetedLessonId can be null per store design
          updateResetedLessonId(null);
        }
        setIsLoading(false);
      },
    );

    return () => {
      unsubscribe();
    };
  }, [
    loadedChapterId,
    refreshData,
    updateResetedLessonId,
    resetedLessonId,
    lessonId,
  ]);

  useEffect(() => {
    const unsubscribe = useUserStore.subscribe(
      state => state.isLoggedIn,
      isLoggedIn => {
        if (!isLoggedIn || !chapterId) {
          return;
        }
        setLoadedChapterId(chapterId);
        refreshData();
      },
    );

    return () => {
      unsubscribe();
    };
  }, [chapterId, refreshData]);

  useEffect(() => {
    sseRef.current?.close();

    if (!lessonId || resetedLessonId === lessonId) {
      return;
    }
    refreshData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lessonId, resetedLessonId]);

  useEffect(() => {
    const onGoToNavigationNode = (
      event: CustomEvent<{ chapterId: string; lessonId: string }>,
    ) => {
      const { chapterId: targetChapterId, lessonId: targetLessonId } =
        event.detail;
      if (targetChapterId !== loadedChapterId) {
        return;
      }
      setIsTypeFinished(true);
      // setLastInteractionBlock(null);
      lastInteractionBlockRef.current = null;
      scrollToLesson(targetLessonId);
      updateSelectedLesson(targetLessonId);
    };

    events.addEventListener(
      BZ_EVENT_NAMES.GO_TO_NAVIGATION_NODE,
      onGoToNavigationNode as EventListener,
    );

    return () => {
      events.removeEventListener(
        BZ_EVENT_NAMES.GO_TO_NAVIGATION_NODE,
        onGoToNavigationNode as EventListener,
      );
    };
  }, [loadedChapterId, scrollToLesson, updateSelectedLesson]);

  /**
   * updateContentListWithUserOperate rewinds the list to the chosen interaction point.
   */
  const updateContentListWithUserOperate = useCallback(
    (
      params: OnSendContentParams,
    ): { newList: ChatContentItem[]; needChangeItemIndex: number } => {
      const newList = [...contentListRef.current];
      const needChangeItemIndex = newList.findIndex(item =>
        item.content?.includes(params.variableName || ''),
      );
      if (needChangeItemIndex !== -1) {
        newList[needChangeItemIndex] = {
          ...newList[needChangeItemIndex],
          readonly: false,
          defaultButtonText: params.buttonText || '',
          defaultInputText: params.inputText || '',
        };
        newList.length = needChangeItemIndex + 1;
        setTrackedContentList(newList);
      }

      return { newList, needChangeItemIndex };
    },
    [setTrackedContentList],
  );

  /**
   * onRefresh replays a block from the server using the original inputs.
   */
  const onRefresh = useCallback(
    (generatedBlockBid: string) => {
      if (!isTypeFinished) {
        showOutputInProgressToast();
        return;
      }

      const newList = [...contentListRef.current];
      const needChangeItemIndex = newList.findIndex(
        item => item.generated_block_bid === generatedBlockBid,
      );
      if (needChangeItemIndex === -1) {
        showOutputInProgressToast();
        return;
      }

      newList.length = needChangeItemIndex;
      setTrackedContentList(newList);

      setIsTypeFinished(false);
      runRef.current?.({
        input: '',
        input_type: SSE_INPUT_TYPE.NORMAL,
        reload_generated_block_bid: generatedBlockBid,
      });
    },
    [isTypeFinished, setTrackedContentList, showOutputInProgressToast],
  );

  /**
   * onSend processes user interactions and continues streaming responses.
   */
  const onSend = useCallback(
    (content: OnSendContentParams) => {
      if (!isTypeFinished) {
        showOutputInProgressToast();
        return;
      }

      const { variableName, buttonText, inputText } = content;
      if (buttonText === SYS_INTERACTION_TYPE.PAY) {
        trackEvent(EVENT_NAMES.POP_PAY, { from: 'show-btn' });
        onPayModalOpen();
        return;
      }
      if (buttonText === SYS_INTERACTION_TYPE.LOGIN) {
        if (typeof window !== 'undefined') {
          const redirect = encodeURIComponent(window.location.pathname);
          window.location.href = `/login?redirect=${redirect}`;
        }
        return;
      }
      if (buttonText === SYS_INTERACTION_TYPE.NEXT_CHAPTER) {
        const nextLessonId = getNextLessonId(lessonId);
        if (nextLessonId) {
          updateSelectedLesson(nextLessonId, true);
          onGoChapter(nextLessonId);
          scrollToLesson(nextLessonId);
        }
        return;
      }

      const { newList, needChangeItemIndex } =
        updateContentListWithUserOperate(content);

      if (needChangeItemIndex === -1) {
        setTrackedContentList(newList);
      }

      setIsTypeFinished(false);
      // scrollToBottom();
      runRef.current?.({
        input: {
          [variableName as string]: buttonText || inputText,
        },
        input_type: SSE_INPUT_TYPE.NORMAL,
        reload_generated_block_bid:
          needChangeItemIndex !== -1
            ? newList[needChangeItemIndex].generated_block_bid
            : undefined,
      });
    },
    [
      getNextLessonId,
      isTypeFinished,
      lessonId,
      onGoChapter,
      onPayModalOpen,
      scrollToLesson,
      setTrackedContentList,
      showOutputInProgressToast,
      trackEvent,
      updateContentListWithUserOperate,
      updateSelectedLesson,
    ],
  );

  /**
   * onTypeFinished appends the interaction UI once streaming completes.
   */
  const onTypeFinished = useCallback(() => {
    // console.log('🟢 onTypeFinished called', {
    //   hasInteractionBlock: !!lastInteractionBlockRef.current,
    //   contentListLength: contentListRef.current.length,
    //   isTypeFinished,
    // });

    // Only process if:
    // 1. There's a pending interaction block
    // 2. Currently in typing state (not already finished)
    if (!lastInteractionBlockRef.current || !isTypeFinished) {
      // console.log('🟢 onTypeFinishe跳过 - no pending interaction or already finished');
      return;
    }

    if (contentListRef.current.length > 0) {
      // Capture the interaction block value before async operations
      const interactionBlockToAdd = lastInteractionBlockRef.current;

      // Clear the ref immediately to prevent reuse
      lastInteractionBlockRef.current = null;

      setTrackedContentList(prev => {
        const updatedList = [...prev];

        // Find the last CONTENT type item and append AskButton to its content
        // Set isHistory=true to prevent triggering typewriter effect for AskButton
        if (mobileStyle) {
          for (let i = updatedList.length - 1; i >= 0; i--) {
            if (
              updatedList[i].type === ChatContentItemType.CONTENT &&
              !updatedList[i].content?.includes(`<custom-button-after-content>`)
            ) {
              updatedList[i] = {
                ...updatedList[i],
                content:
                  (updatedList[i].content || '') +
                  `<custom-button-after-content><img src="${AskIcon.src}" alt="ask" width="14" height="14" /><span>${t('module.chat.ask')}</span></custom-button-after-content>`,
                isHistory: true, // Prevent AskButton from triggering typewriter
              };
              break;
            }
          }
        }

        // Add interaction blocks - use captured value instead of ref
        const lastItem = updatedList[updatedList.length - 1];
        const gid = lastItem.generated_block_bid;
        updatedList.push(
          {
            parent_block_bid: gid,
            generated_block_bid: '',
            content: '',
            like_status: LIKE_STATUS.NONE,
            type: ChatContentItemType.LIKE_STATUS,
          },
          interactionBlockToAdd,
        );

        return updatedList;
      });

      setIsTypeFinished(true);
      // console.log('🟢 onTypeFinished processed - interaction block added');
    }
  }, [isTypeFinished, mobileStyle, setTrackedContentList, t]);

  /**
   * toggleAskExpanded toggles the expanded state of the ask panel for a specific block
   */
  const toggleAskExpanded = useCallback(
    (parentBlockBid: string) => {
      setTrackedContentList(prev => {
        // Check if ASK block already exists
        const hasAskBlock = prev.some(
          item =>
            item.parent_block_bid === parentBlockBid &&
            item.type === ChatContentItemType.ASK,
        );

        if (hasAskBlock) {
          // Toggle existing ASK block's expanded state
          return prev.map(item =>
            item.parent_block_bid === parentBlockBid &&
            item.type === ChatContentItemType.ASK
              ? { ...item, isAskExpanded: !item.isAskExpanded }
              : item,
          );
        } else {
          // Create new ASK block after LIKE_STATUS block
          return prev.flatMap(item => {
            if (
              item.parent_block_bid === parentBlockBid &&
              item.type === ChatContentItemType.LIKE_STATUS
            ) {
              return [
                item,
                {
                  generated_block_bid: '',
                  parent_block_bid: parentBlockBid,
                  type: BLOCK_TYPE.ASK,
                  content: '',
                  isAskExpanded: true,
                  ask_list: [],
                  readonly: false,
                  customRenderBar: () => null,
                  defaultButtonText: '',
                  defaultInputText: '',
                },
              ];
            }
            return [item];
          });
        }
      });
    },
    [setTrackedContentList],
  );

  // Create a stable null render bar function
  const nullRenderBar = useCallback(() => null, []);

  const items = useMemo(
    () =>
      contentList.map(item => ({
        ...item,
        customRenderBar: item.customRenderBar || nullRenderBar,
      })),
    [contentList, nullRenderBar],
  );

  return {
    items,
    isLoading,
    onSend,
    onRefresh,
    onTypeFinished,
    toggleAskExpanded,
  };
}

export default useChatLogicHook;
