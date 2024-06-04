/*
 * 左侧导航控件容器
 */
import { AppContext } from "@Components/AppContext.js";
import { useContext, useState } from "react";

import NavHeader from "./NavHeader.jsx";
import NavBody from "./NavBody.jsx";
import NavFooter from "./NavFooter.jsx";

import styles from './NavDrawer.module.scss'

/**
 * 导航栏布局类型
 * 1: 展开
 * 0：收缩
 */
export const NAV_LAYOUT_TYPE_FULL = 1;
export const NAV_LAYOUT_TYPE_MINI = 0;

/**
 * 导航栏展示形式
 * 0: 默认，在 dom 流中展示
 * 1：作为抽屉展示
 */
export const NAV_SHOW_TYPE_NORMAL = 0;
export const NAV_SHOW_TYPE_DRAWER = 1;

const NavDrawer = ({ showType = NAV_SHOW_TYPE_NORMAL  }) => {
  const [layoutType, setLayoutType] = useState(NAV_LAYOUT_TYPE_FULL)
  const [width, setWidth] = useState('280px');
  const { frameLayout, isLogin } = useContext(AppContext);

  const onHeaderCloseHandler = () => {
    console.log('onHeaderCloseHandler');
  }

  const onHeaderToggleHandler = ({ isCollapse }) => {
    console.log('onHeaderToggleHandler', isCollapse);
  }

  return (
    <div className={styles.navDrawerWrapper} style={{width}}>
      <div className={styles.navDrawer}>
        <NavHeader
          onClose={onHeaderCloseHandler}
          onToggle={onHeaderToggleHandler}
        />
        <div style={{flex: '1 1 auto'}}>
          <NavBody />
        </div>
        <NavFooter />
      </div>
    </div>
  );
};

export default NavDrawer;
