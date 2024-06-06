import PopupModal from '@Components/PopupModal';

import styles from './FilingModal.module.scss';

export const FillingModal = ({ open, onClose, style }) => {
  return (
    <PopupModal open={open} onClose={onClose} wrapStyle={{ ...style}}>
      <div className={styles.filingModal}>
        <div>北京xxxx有限公司</div>
        <div>北京朝阳区望京xx大厦xx层xx02</div>
        <div>京ICP备2024060606</div>
        <div>京公安网备gaxxxxxxxxxx</div>
        <div className={styles.btnGroup}>
          <div>提交反馈</div>
          <div>|</div>
          <div>服务协议</div>
          <div>|</div>
          <div>隐私政策</div>
        </div>
      </div>
    </PopupModal>
  );
}

export default FillingModal;
