import { List, Skeleton } from "antd";
import "./ChatList.css";
import { Input, Button } from "antd";
import InfiniteScroll from "react-infinite-scroll-component";
import { createFromIconfontCN, PlusCircleOutlined } from "@ant-design/icons";
import { Dropdown } from "antd";
import { useState, forwardRef, useImperativeHandle } from "react";
import { Empty } from "antd";
import create from "@ant-design/icons/lib/components/IconFont";
import { getLessonTree } from "../../Api/lesson";


import { Menu ,Badge} from 'antd';
import { MailOutlined, AppstoreOutlined, SettingOutlined } from '@ant-design/icons';
import { CheckCircleOutlined, PlayCircleOutlined } from '@ant-design/icons';

const { SubMenu } = Menu;


/**
 * @description 排序选项
 */
const dropdownMenu = [
  { key: "nameAscendingOrder", label: "名称升序" },
  { key: "nameDescendingOrder", label: "名称降序" },
  { key: "timeAscendingOrder", label: "时间升序" },
  { key: "timeDescendingOrder", label: "时间降序" },
];

/**
 * @description 来自iconfont.cn 远程图标
 */
const IconFontSort = createFromIconfontCN({
  scriptUrl: "//at.alicdn.com/t/c/font_4167500_ekpu72ffhmt.js",
});

/**
 * @description 文档列表组件
 * @param {*} onClickListItem - 事件 点击列表中某一行的的方法
 * @returns
 */
const ChatList = forwardRef(
  ({ onClickListItem, onClickCreateNewChat }, ref) => {
    const [selectedSortOrder, setSelectedSortOrder] = useState();
    const [loading, setLoading] = useState();
    const [data, setData] = useState([]);
    const [lessonData,setLessonData] = useState([]);
    const params = {};
    const dataLength = 100;
    const onSearch = (chat_title) => {
      params.chat_title = chat_title;
      queryAllChatsList();
    };

    const onTitleUpdate = (chatId, chatTitle, created) => {
      console.log(chatId, chatTitle, created);
      if (data.length > 0) {
        const newData = data.map((item) => {
          if (item.chat_id === chatId) {
            item.chat_title += chatTitle;
          }
          return item;
        });
        if (data.filter((item) => item.chat_id === chatId) == 0) {
          console.log("没有找到", created);
          newData.unshift({
            chat_id: chatId,
            chat_title: chatTitle,
            created: created,
          });
        }
        setData(newData);
      }
    };

    useImperativeHandle(ref, () => ({
      onTitleUpdate: (chatId, chatTitle, created) => {
        onTitleUpdate(chatId, chatTitle, created);
      },
      queryAllChatsList: () => {
        queryAllChatsList({ chat_title: "" });
      },
    }));
    /**
     * @description 点击下拉菜单中的 排序选项的方法 实现单选 取消选择 的功能
     * @param {*} menuOption
     */
    const onClickMenuItem = (menuOption) => {
      if (menuOption.key === selectedSortOrder[0]) {
        setSelectedSortOrder([]);
        delete params.sortOrder;
      } else {
        setSelectedSortOrder([menuOption.key]);
        params.sortOrder = menuOption.key;
      }
    };

    const onNext = () => {
      setLoading(true);
      setTimeout(() => {
        setLoading(false);
      }, 2000);
      console.log(`下一页`);
    };

    const listElement = () => {
      if (data.length > 0) {
        return (
          <div className="chat_list_body">
            <InfiniteScroll
              dataLength={dataLength}
              next={onNext}
              hasMore={data.length < 50}
              loader={
                <Skeleton
                  loading={loading}
                  paragraph={{
                    rows: 1,
                  }}
                  active
                />
              }
              scrollableTarget="chat_list_container"
            >
              <List
                loading={loading}
                className="chat_list"
                dataSource={data}
                renderItem={(item, index) => (
                  <List.Item>
                    <List.Item.Meta
                      title={
                        <a
                          onClick={() => {
                            onClickListItem(item);
                          }}
                        >
                          {item.chat_title}
                          <br />
                          {item.created}
                        </a>
                      }
                    />
                    <div>{item.time}</div>
                  </List.Item>
                )}
              ></List>
            </InfiniteScroll>
          </div>
        );
      }
      return (
        <div className="chat_list_body__empty">
          <Empty description="暂无数据"></Empty>
        </div>
      );
    };

    const queryAllChatsList = () => {
     

      getLessonTree().then((res) => {
        setLessonData(res.data);
      })
    };

    const onSearchInputChange = ({ target }) => {
      if (target.value.length == 0) {
        queryAllChatsList();
      }
    };

    useState(() => {
      setLoading(true);
      queryAllChatsList();
    }, []);




    return (
      <div id="chat_list_container" className="chat_list_container">
        <div className="documnet_list_header">
          <p>课程列表</p>

        </div>

       <Menu
        mode="inline"
        // openKeys={openKeys}
        // onOpenChange={onOpenChange}
        style={{ width: 256 }}
      >
        {
          lessonData.map((item,index)=>{
            return <SubMenu key={index}  title={item.lesson_name}>
              {
                item.children.map((chapter,index)=>{
                  return <Menu.Item key={chapter.lesson_no}>
                    {chapter.lesson_name} 
                    {chapter.status === "completed" ? (
                      
                    <CheckCircleOutlined style={{ color: 'green', float: 'right' }} />
                  ) : (
                     <PlayCircleOutlined style={{ color: 'green', float: 'right' }} />
                  )}
                    </Menu.Item>
                })
              }
            </SubMenu>
          })
        }
        
      </Menu> 
        {/* <Button
            onClick={onClickCreateNewChat}
            icon={<PlusCircleOutlined />}
            style={{
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
              width: "100%",
              height: 42,
              fontWeight: "bold",
            }}
            type="dashed">
            创建新对话
          </Button> */}
        </div>
      
    );
  }
);

export default ChatList;
