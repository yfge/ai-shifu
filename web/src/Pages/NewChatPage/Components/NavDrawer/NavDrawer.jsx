/*
 * 左侧导航控件容器
 */
import { AppContext } from '@Components/AppContext.js';
import { useContext, useState } from 'react';

import NavHeader from './NavHeader.jsx';
import NavBody from './NavBody.jsx';
import NavFooter from './NavFooter.jsx';
import FillingModal from './FilingModal.jsx';
import ThemeWindow from './ThemeWindow.jsx';
import SettingWindow from './SettingWindow.jsx';

import styles from './NavDrawer.module.scss';

import {
  FRAME_LAYOUT_PAD,
  FRAME_LAYOUT_PAD_INTENSIVE,
  FRAME_LAYOUT_MOBILE,
} from '@constants/uiContants';

/**
 * 导航栏展示形式
 * 0: 默认，在 dom 流中展示
 * 1：作为抽屉展示
 */
export const NAV_SHOW_TYPE_NORMAL = 0;
export const NAV_SHOW_TYPE_DRAWER = 1;

const calcNavWidth = (frameLayout) => {
  if (frameLayout === FRAME_LAYOUT_MOBILE) {
    return '100%';
  }
  if (frameLayout === FRAME_LAYOUT_PAD_INTENSIVE) {
    return '280px';
  }
  if (frameLayout === FRAME_LAYOUT_PAD) {
    return '25%';
  }
  return '280px';
}

const COLLAPSE_WIDTH = '60px';

const NavDrawer = ({ showType = NAV_SHOW_TYPE_NORMAL }) => {
  const { frameLayout } = useContext(AppContext);
  const [isCollapse, setIsCollapse] = useState(false);
  const [isFillingModalOpen, setIsFillingModalOpen] = useState(false);

  const onHeaderCloseHandler = () => {
    console.log('onHeaderCloseHandler');
  }

  const onHeaderToggleHandler = ({ isCollapse }) => {
    setIsCollapse(isCollapse);
  }

  const onFilingModalClose = () => {
    console.log('onFilingModalClose');
    setIsFillingModalOpen(false);  
  }

  const popupWindowStyle = {
    left: '50%', transform: 'translate(-50%)', width: '250px', top: 'auto', bottom: 80 
  }

  return (
    <div className={styles.navDrawerWrapper} style={{width: isCollapse ? COLLAPSE_WIDTH : calcNavWidth(frameLayout) }}>
      <div className={styles.navDrawer}>
        <NavHeader
          onClose={onHeaderCloseHandler}
          onToggle={onHeaderToggleHandler}
          isCollapse={isCollapse}
        />
        <div style={{flex: '1 1 auto'}}>
          { !isCollapse && <NavBody /> }
        </div>
        <NavFooter
          isCollapse={isCollapse}
          onFilingClick={() => {
            setIsFillingModalOpen(true)
          }}
        />
        <FillingModal open={false} style={popupWindowStyle} />
        <ThemeWindow open={false} style={popupWindowStyle} />
        <SettingWindow open={true} style={popupWindowStyle} />
      </div>
    </div>
  );
};

export default NavDrawer;
