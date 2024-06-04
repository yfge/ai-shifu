import { Row, Col } from "antd";
import ChatList from "./ChatList";
import { useState } from "react";
import { UploadEvent } from "../../Api/UploadEvent";
import ChatComponents from "./ChatComponents";
import { GetChatDetail } from "../../Api/chat";
import { useRef } from "react";
import "./ChatPage.css";

const ChatPage = () => {
  UploadEvent("ChatPage", { page: "chatPage" });
  const chatComponents = useRef(null);
  const chatList = useRef(null);
  const onClickListItem = (chatInfo) => {
    UploadEvent("view_chatInfo", { page: "chatPage" });
    GetChatDetail(chatInfo.chat_id).then((res) => {
      chatComponents.current.loadMsg(chatInfo.chat_id, res.data);
    });
  };

  const onTitleUpdate = (chatId, chatTitle, created) => {
    console.log(chatId, chatTitle, created);
    chatList.current.onTitleUpdate(chatId, chatTitle, created);
  };

  const onClickMenuItem = (lessonInfo) => {
    if(lessonInfo && chatComponents.current){
      chatComponents.current.switchLesson(lessonInfo)
    }
  };

  return (
    <div className="chat-page full-height">
      <ChatList 
        onClickListItem={onClickListItem}
        onClickMenuItem={onClickMenuItem}
        ref={chatList}
      ></ChatList>
      <ChatComponents
        className="chat-components"
        ref={chatComponents}
        onTitleUpdate={onTitleUpdate}
      />
    </div>
  );
};

export default ChatPage;
