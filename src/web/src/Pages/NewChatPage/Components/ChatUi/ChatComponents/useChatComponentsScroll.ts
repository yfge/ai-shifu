import { message } from "antd";
import { useCallback, useRef, useState, useEffect } from "react"
import { smoothScroll } from 'Utils/smoothScroll';

const SCROLL_BOTTOM_THROTTLE = 50;

// take scoll logic in the separte file
export const useChatComponentsScroll = ({
  chatRef,
  containerStyle,
  messages,
  deleteMsg,
  appendMsg,
}) => {
  const [autoScroll, setAutoScroll] = useState(true);
  const lastScrollPositionRef = useRef(0);
  const needUpdateScrollRef = useRef(false);
  const fixedScrollPositionRef = useRef(0);
  const [scrollPosition, setScrollPosition] = useState(0);
  const [lastMessageHeight, setLastMessageHeight] = useState(0);



  const startAutoScroll = useCallback(() => {
    setAutoScroll(true);
    console.log('startAutoScroll');
    if (messages.length && messages[messages.length - 1].position === 'pop') {
      deleteMsg(messages[messages.length - 1]._id);
    }
  }, [deleteMsg, messages]);

  const stopAutoScroll = useCallback(() => {
    setAutoScroll(false);
    if (messages.length && messages[messages.length - 1].position === 'pop') {
      return;
    }
    appendMsg({ type: 'loading', position: 'pop' });
  }, [appendMsg, messages]);


  const onMessageListScroll = useCallback((e) => {
    const scrollWrapper = e.target;
    const inner = scrollWrapper.children[0];
    const currentScrollTop = Math.max(0, scrollWrapper.scrollTop);

    if (!scrollWrapper || !inner) {
      return;
    }

    if (
      currentScrollTop >= 0 &&
      currentScrollTop + scrollWrapper.clientHeight <
      inner.clientHeight - SCROLL_BOTTOM_THROTTLE
    ) {
      // stopAutoScroll();
    } else {
      // startAutoScroll();
    }
  }, [startAutoScroll, stopAutoScroll, fixedScrollPositionRef]);


  useEffect(() => {
    console.log('fixedScrollPositionRef', fixedScrollPositionRef.current);
    scrollTo(fixedScrollPositionRef.current, true);
  }, [fixedScrollPositionRef.current]);

  const scrollTo = useCallback((height, stopScroll = false) => {
    console.log('scrollTo', height);
    if (stopScroll) {
      stopAutoScroll();
    }

    const wrapper = chatRef.current?.querySelector(
      `.${containerStyle} .PullToRefresh`
    );

    if (!wrapper) {
      return;
    }
    smoothScroll({ el: wrapper, to: height });
  }, [chatRef, containerStyle, stopAutoScroll]);

  const scrollToLesson = useCallback((lessonId) => {
    if (!chatRef.current) {
      return;
    }

    const lessonNode = chatRef.current.querySelector(
      `[data-id=lesson-${lessonId}]`
    );
    if (!lessonNode) {
      return;
    }

    scrollTo(lessonNode.offsetTop, true);
  }, [chatRef, scrollTo]);

  const scrollToBottom = useCallback(() => {
    const inner = chatRef.current?.querySelector(
      `.${containerStyle} .PullToRefresh-inner`
    );

    if (!inner) {
      return;
    }

    scrollTo(inner.clientHeight);
  }, [chatRef, containerStyle, scrollTo]);

  // 重置函数

  const [isLastMessageAtTop, setIsLastMessageAtTop] = useState(false);

  useEffect(() => {
    console.log('fixedScrollPositionRef', fixedScrollPositionRef.current);
  }, [fixedScrollPositionRef.current]);
  useEffect(() => {
    console.log('autoScroll', autoScroll);
  }, [autoScroll]);

  const scrollLastMessageToTop = useCallback(() => {
    if (autoScroll) {
      console.log('stopAutoScroll in scrollLastMessageToTop');
      stopAutoScroll();
    }
    setIsLastMessageAtTop(true);
    needUpdateScrollRef.current = true;
    const wrapper = chatRef.current?.querySelector(
      `.${containerStyle} .PullToRefresh`
    );
    const inner = chatRef.current?.querySelector(
      `.${containerStyle} .PullToRefresh-inner`
    );

    if (!wrapper || !inner) {
      return;
    }

    const messageElements = inner.querySelector('.MessageList').children;
    if (messageElements.length === 0) {
      console.log('messageElements', messageElements);
      return;
    }

  const lastMessage = messageElements[messageElements.length - 1];
  const secondLastMessage = messageElements[messageElements.length - 2];

  // 添加调试信息
  console.log('lastMessage height:', lastMessage.offsetHeight);
  console.log('secondLastMessage height:', secondLastMessage.offsetHeight);
  console.log('lastMessage offsetTop:', lastMessage.offsetTop);
  console.log('secondLastMessage offsetTop:', secondLastMessage.offsetTop);
  console.log('实际间距:', lastMessage.offsetTop - secondLastMessage.offsetTop - secondLastMessage.offsetHeight);



    // const lastMessage = messageElements[messageElements.length - 1];
    const wrapperRect = inner.getBoundingClientRect();
    const lastMessageRect = lastMessage.getBoundingClientRect();
    const offsetTop = lastMessage.offsetTop;
    // 记录当前消息高度
    lastMessageHeightRef.current = lastMessageRect.height;

    console.log('messageHeight', lastMessageRect.height);
    // 添加底部 padding 创建滚动空间
    const extraSpace = wrapper.clientHeight - lastMessageRect.height;

    console.log('extraSpace', extraSpace);
    inner.style.paddingBottom = `${extraSpace}px`;

    scrollTo(offsetTop, true);
  }, [chatRef, containerStyle, scrollTo]);



  return {
    autoScroll,
    onMessageListScroll,
    scrollTo,
    scrollToLesson,
    scrollToBottom,
    scrollLastMessageToTop,
  }
}
