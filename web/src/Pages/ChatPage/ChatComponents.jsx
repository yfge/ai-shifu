import Chat, { Bubble, useMessages, Empty ,Card,CardMedia,CardTitle,CardText,CardActions} from "@chatui/core";
import { Button } from "antd";
import { Image } from "antd";

import "@chatui/core/dist/index.css";
import "./chatui-theme.css";
import "../../App.css";
import React, { useEffect, forwardRef, useImperativeHandle } from "react";
// import { SendMsg } from "../../Service/SSE";
import {RunScript} from "../../Api/study";
import { UploadEvent } from "../../Api/UploadEvent";
import { ReactMarkdown } from "react-markdown/lib/react-markdown";

import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import { CopyOutlined, NodeExpandOutlined, SendOutlined } from "@ant-design/icons";
import { message } from "antd";
import { enabled, set } from "store";

const generateUUID = () => {
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, function (c) {
    var r = (Math.random() * 16) | 0,
      v = c == "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
};
const quickOperstionList = [
];

const MarkdownBubble = (props) => {
  const onCopy = (content) => {
    console.log(content);
    navigator.clipboard.writeText(content).then((res) => {
    });
  };
  return (
    <Bubble>
      <ReactMarkdown
        children={props.content}
        components={{
          code({ node, inline, className, children, ...props }) {
            const match = /language-(\w+)/.exec(className || "");
            return !inline && match ? (
              <div
                className="markdown-code_block"
                style={{
                  position: "relative",
                }}
              >
                <Button
                  className="copy_btn"
                  type="dashed"
                  ghost
                  size="small"
                  icon={<CopyOutlined></CopyOutlined>}
                  onClick={() => onCopy(children)}
                ></Button>
                <SyntaxHighlighter
                  {...props}
                  children={String(children).replace(/\n$/, "")}
                  style={vscDarkPlus}
                  language={match[1]}
                  showLineNumbers={true}
                  wrapLines={false}
                  onCopy={() => {
                    onCopy(children);
                  }}
                  renderInline={true}
                ></SyntaxHighlighter>
              </div>
            ) : (
              <code {...props} className={className}>
                {children}
              </code>
            );
          },
          img(props) {
            return <Image {...props} width={320}></Image>;
          },
        }}
      ></ReactMarkdown>
    </Bubble>
  );
};

const ChatComponents = forwardRef(({ onTitleUpdate, className }, ref) => {
  const { messages, appendMsg, setTyping, updateMsg, resetList } = useMessages(
    []
  );
  const [chatId, setChatId] = React.useState("");
  const [scriptId, setScriptId] = React.useState("");
  const [inputPlaceholder, setInputPlaceholder] = React.useState("请输入");
  const [inputDisabled,setInputDisabled]=React.useState(false);
  const [lessonId,setLessonId]=React.useState("");

  function handleSend(type, val) {

    let sendScriptId = scriptId;
    if (type === "text" && val.trim()) {
      appendMsg({
        _id: generateUUID(),
        type: "text",
        content: { type: "text", text: val },
        position: "right",
      });
      UploadEvent("ChatInput", {
        text_length: val.length,
        page: "chat",
      });
    }else if (type === "button"){
      sendScriptId = undefined;
    }
      setTyping(true);
      let lastMsg = null;


      console.log("lesson_id",lessonId);

      RunScript(chatId, lessonId,val,val, sendScriptId,(response) => {
        try {
          console.log(response);
          setChatId(response.chat_id);
          let id = generateUUID();
          if (lastMsg !== null && lastMsg.content.type === "calling") {
            lastMsg.content.isProcessed = true;
            updateMsg(lastMsg._id, lastMsg);
          }
          if (response.type === "calling") {
            lastMsg = {
              content: {
                function_name: response.function_name,
                type: response.type,
                isProcessed: false,
              },
              _id: id,
            };
            appendMsg(lastMsg);
            UploadEvent("CallingRunning", {
              page: "chat",
              function_name: response.function_name,
            });
          } else if (response.type === "text") {
            if (lastMsg !== null && lastMsg.content.type === "text") {
              lastMsg.content.text = lastMsg.content.text + response.content;
              updateMsg(lastMsg._id, lastMsg);
            } else {
              lastMsg = {
                _id: id,
                type: response.type,
                content: {
                  type: response.type,
                  text: response.content.replace(/<br\/>/g, "\n"),
                },
                position: "left",
                user: { avatar:  require("../../Assets/chat/sunner_icon.jpg") },
              };
              appendMsg(lastMsg);
            }
          }else if (response.type === "text_end"){
            lastMsg = null;
          }else if (response.type === "input"){
            setInputPlaceholder(response.content);
            setScriptId(response.id);
            setInputDisabled(false);

          } else if (response.type === "buttons"){
            lastMsg = {
              _id: id,
              type: "card",
              content: response.content,
              position: "right" 
            };
            appendMsg(lastMsg);
            setInputDisabled(true);
          }else if (response.type === "title") {
            onTitleUpdate(response.chat_id, response.text, response.created);
          }else if (response.type === "study_complete"){
            // setLessonId(response.lesson_id);

          }
        } catch (e) {
          // console.log("error", e);
        }
      });
    
  }

  function onButtonClick(){
    handleSend("button","点击了按钮");

  }
  function renderMessageContent(msg) {
    const { content } = msg;
    if (content === undefined) {
      return null;
    }
    if (content.type === "calling") {
      return (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            padding: "10px",
            borderRadius: "5px",
            fontWeight: "bold",
            minWidth: "25%",
            backgroundColor: "#f7f8fa",
          }}
        >
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <img
                style={{ display: content.isProcessed ? "block" : "none" }}
                src={require("../../Assets/success_chat.png")}
                alt=""
              />
              <img
                className="chat_loading"
                style={{ display: content.isProcessed ? "none" : "block" }}
                src={require("../../Assets/loading_chat.png")}
                alt=""
              />
              {content.isProcessed
                ? "操作执行完成"
                : `正在执行操作:“${content.function_name}”`}
            </div>
          </div>
        </div>
      );
    } else if (content.type === "text") {
      return <MarkdownBubble content={content.text} />;
    } else if (content.type === "init") {
    }else if (msg.type === "card") {
      console.log("card:"+content);
      return (
        <Bubble>
        <Card size="xl">
      <CardTitle>接下来</CardTitle>
      <CardActions>
        <Button onClick={onButtonClick} >{content}</Button>
      </CardActions>
    </Card>
    </Bubble>
      )
        }
    return null;
  }

  function loadMsg(chatId, messages) {
    resetList();
    setChatId(chatId);
    messages.forEach((item) => {
      if (item.role === "user") {
        appendMsg({
          _id: generateUUID(),
          type: "content",
          content: { type: "content", text: item.content },
          position: "right",
        });
      } else {
        if (item.function_call) {
          appendMsg({
            content: {
              function_name: item.function_call,
              type: "calling",
              isProcessed: true,
            },
            _id: generateUUID(),
          });
        } else {
          appendMsg({
            _id: generateUUID(),
            type: "content",
            content: { type: "content", text: item.content },
            position: "left",
          });
        }
      }
    });
  }
  
  const switchLesson = (lessonInfo) => {
    console.log("switch Lesson",lessonInfo);
    setLessonId(lessonInfo.lesson_id);
    

  }

  useImperativeHandle(ref, () => ({
    loadMsg,
    switchLesson
  }));

  function renderBeforeMessageList() {
    // message 的长度等于 0 的时候 返回 Empty 组件
    if (messages.length === 0) {
      return (
        <div
          className="full-height chat-ui_container"
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <Empty
            className="chatui_empty"
            children={
                <div className="empty_header">
                  <div className="title">
                    <img
                      className="logo"
                      src={require("../../Assets/chat/img8.png")}
                      alt=""
                    />
                    <div className="system-name"></div>
                  </div>
                  <div className="slogan">AI私教</div>
                </div>

            }
          ></Empty>
        </div>
      );
    }
  }
  return (
    <Chat
      navbar={{ title: "和AI学Python" }}
      messages={messages}
      renderMessageContent={renderMessageContent}
      onSend={handleSend}
      loadMsg={loadMsg}
      renderBeforeMessageList={renderBeforeMessageList}
      recorder={{ canRecord: true }}
      placeholder={inputPlaceholder}
      inputOptions={{disabled:inputDisabled}}
    />
  );
});

export default ChatComponents;
