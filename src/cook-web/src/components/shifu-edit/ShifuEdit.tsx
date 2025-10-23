'use client';
import React, { useState, useEffect } from 'react';
import { DndProvider, useDrag, useDrop } from 'react-dnd';
import type { DropTargetMonitor } from 'react-dnd';
import { HTML5Backend } from 'react-dnd-html5-backend';
import { Button } from '@/components/ui/Button';
import {
  Plus,
  GripVertical,
  Trash2,
  SquarePen,
  BugPlay,
  Settings2,
  ListCollapse,
} from 'lucide-react';
import { useShifu } from '@/store';
import { useUserStore } from '@/store';
import OutlineTree from '@/components/outline-tree';
import '@mdxeditor/editor/style.css';
import Header from '../header';
import { BlockDTO, BlockType, ContentDTO } from '@/types/shifu';
import RenderBlockUI from '../render-ui';
import { MarkdownFlowEditor } from 'markdown-flow-ui';
import 'markdown-flow-ui/dist/markdown-flow-ui.css';
import AIDebugDialog from '@/components/ai-debug';

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '../ui/AlertDialog';
import AddBlock from '@/components/add-block';
import Loading from '../loading';
import { useTranslation } from 'react-i18next';
import i18n from '@/i18n';
interface DragItem {
  id: string;
  index: number;
}

interface DraggableBlockProps {
  id: string;
  type: BlockType;
  index: number;
  block: BlockDTO;
  moveBlock: (dragIndex: number, hoverIndex: number) => void;
  onClickDebug?: (id: string) => void;
  onClickRemove?: (id: string) => void;
  onClickChangeType?: (id: string, llm_enabled: boolean) => void;
  children: React.ReactNode;
  disabled?: boolean;
  error?: string | null;
}

const DraggableBlock = ({
  id,
  type,
  index,
  block,
  moveBlock,
  onClickDebug,
  onClickRemove,
  onClickChangeType,
  children,
  disabled = false,
  error,
}: DraggableBlockProps) => {
  const { t } = useTranslation();
  const ref = React.useRef<HTMLDivElement>(null);

  const [llmEnabled, setLlmEnabled] = useState(
    (block.properties as ContentDTO).llm_enabled,
  );

  const [{ handlerId }, drop] = useDrop<
    DragItem,
    void,
    { handlerId: string | symbol | null }
  >({
    accept: 'BLOCK',
    collect(monitor) {
      return {
        handlerId: monitor.getHandlerId(),
      };
    },
    hover(item: DragItem, monitor: DropTargetMonitor) {
      if (!ref.current || disabled) {
        return;
      }

      const dragIndex = item.index;
      const hoverIndex = index;

      if (dragIndex === hoverIndex) {
        return;
      }

      const hoverBoundingRect = ref.current?.getBoundingClientRect();
      const hoverMiddleY =
        (hoverBoundingRect.bottom - hoverBoundingRect.top) / 2;
      const clientOffset = monitor.getClientOffset();
      const hoverClientY = clientOffset!.y - hoverBoundingRect.top;

      if (dragIndex < hoverIndex && hoverClientY < hoverMiddleY) {
        return;
      }
      if (dragIndex > hoverIndex && hoverClientY > hoverMiddleY) {
        return;
      }

      moveBlock(dragIndex, hoverIndex);
      item.index = hoverIndex;
    },
  });

  const [{ isDragging }, drag] = useDrag<
    DragItem,
    void,
    { isDragging: boolean }
  >({
    type: 'BLOCK',
    item: () => {
      return { id, index };
    },
    canDrag: !disabled,
    collect: monitor => ({
      isDragging: monitor.isDragging(),
    }),
  });

  const [showMenu, setShowMenu] = useState(false);

  const handleMouseEnter = () => {
    setShowMenu(true);
  };

  const handleMouseLeave = () => {
    setShowMenu(false);
  };

  const dragRef = React.useRef<HTMLDivElement>(null);
  drop(ref);
  drag(dragRef);

  return (
    <div
      ref={ref}
      style={{ opacity: isDragging ? 0.5 : 1 }}
      data-handler-id={handlerId}
      className='group'
    >
      <div
        ref={dragRef}
        style={{
          border: error ? '1px solid #ff4d4f' : '1px solid #ddd',
          padding: '1rem',
          backgroundColor: '#fff',
          borderRadius: '8px',
          position: 'relative',
        }}
      >
        <div
          onMouseLeave={handleMouseLeave}
          className='group-hover:opacity-100 opacity-0 cursor-grab'
          style={{
            zIndex: 100,
            position: 'absolute',
            top: '0',
            left: '-56px',
          }}
        >
          <div className='p-2 h-8 w-16 flex items-center justify-center border color-[#999] rounded'>
            <SquarePen
              className='text-gray-500'
              onMouseEnter={handleMouseEnter}
            />
            <GripVertical
              className='text-gray-500'
              onMouseEnter={handleMouseEnter}
            />
          </div>

          <div
            className='shadow-md rounded-lg w-48 p-2 transition-all'
            style={{
              position: 'absolute',
              left: '0px',
              zIndex: 51,
              display: `${showMenu ? 'block' : 'none'}`,
              border: '1px solid #f3f4f6',
              backgroundColor: '#fff',
            }}
          >
            <div className='flex flex-col gap-2 text-sm'>
              {type === 'content' && (
                <div className='px-3 py-1.5 text-gray-500 text-lg'>
                  {llmEnabled
                    ? t('module.shifu.aiBlock')
                    : t('module.shifu.regularBlock')}
                </div>
              )}
              {type === 'content' && (
                <div
                  className='flex items-center gap-2 px-3 py-1.5 rounded hover:bg-gray-50 cursor-pointer'
                  onClick={() => {
                    onClickChangeType?.(id, !llmEnabled);
                    setLlmEnabled(!llmEnabled);
                  }}
                >
                  <Settings2 className='h-4 w-4' />
                  {llmEnabled
                    ? t('module.shifu.setAsRegularBlock')
                    : t('module.shifu.setAsAiBlock')}
                </div>
              )}
              {type === 'content' && llmEnabled && (
                <div
                  className='flex items-center gap-2 px-3 py-1.5 rounded hover:bg-gray-50 cursor-pointer'
                  onClick={() => onClickDebug?.(id)}
                >
                  <BugPlay className='h-4 w-4' />
                  {t('module.shifu.debug')}
                </div>
              )}
              <div
                className='flex items-center gap-2 px-3 py-1.5 rounded hover:bg-red-50 text-red-600 cursor-pointer'
                onClick={() => onClickRemove?.(id)}
              >
                <Trash2 className='h-4 w-4' />
                {t('module.shifu.delete')}
              </div>
            </div>
          </div>
        </div>
        {error && (
          <div
            className='mb-2 p-2 bg-red-50 border border-red-200 rounded text-red-700 text-sm'
            role='alert'
            aria-live='polite'
          >
            {error}
          </div>
        )}
        {children}
      </div>
    </div>
  );
};

const ScriptEditor = ({ id }: { id: string }) => {
  const { t } = useTranslation();
  const profile = useUserStore(state => state.userInfo);
  const [expandedBlocks, setExpandedBlocks] = useState<Record<string, boolean>>(
    {},
  );
  const [foldOutlineTree, setFoldOutlineTree] = useState(false);

  useEffect(() => {
    if (profile) {
      i18n.changeLanguage(profile.language);
    }
  }, [profile]);
  const {
    blocks,
    mdflow,
    chapters,
    actions,
    blockContentTypes,
    blockProperties,
    // blockUIProperties,
    // blockUITypes,
    currentNode,
    isLoading,
    currentShifu,
    blockErrors,
  } = useShifu();

  const [debugBlockInfo, setDebugBlockInfo] = useState({
    blockId: '',
    visible: false,
  });

  const [removeBlockInfo, setRemoveBlockInfo] = useState({
    blockId: '',
    visible: false,
  });

  const [newBlockId, setNewBlockId] = useState('');

  const onAddChapter = () => {
    actions.addChapter({
      parent_bid: '',
      bid: 'new_chapter',
      id: 'new_chapter',
      name: ``,
      children: [],
      position: '',
      depth: 0,
    });
    setTimeout(() => {
      document.getElementById('new_chapter')?.scrollIntoView({
        behavior: 'smooth',
      });
    }, 800);
  };

  const onDebugBlock = (id: string) => {
    setDebugBlockInfo({ blockId: id, visible: true });
  };

  const onDebugBlockClose = () => {
    setDebugBlockInfo({ blockId: '', visible: false });
  };

  const onRemove = async (id: string) => {
    setRemoveBlockInfo({ blockId: id, visible: true });
  };

  const handleConfirmDelete = async (id: string | undefined) => {
    if (!id) return;
    try {
      await actions.removeBlock(id, currentShifu?.bid || '');
      setRemoveBlockInfo({ blockId: '', visible: false });
    } catch (error) {
      console.error(error);
    }
  };

  const onAddBlock = async (index: number, type: BlockType, bid: string) => {
    const blockId = await actions.addBlock(index, type, bid);
    if (blockId && ['content', 'input', 'goto', 'options'].includes(type)) {
      setNewBlockId(blockId);
      setExpandedBlocks(prev => ({
        ...prev,
        [blockId]: true,
      }));
    }
  };

  useEffect(() => {
    console.log('newBlockId', newBlockId);
    if (newBlockId && expandedBlocks[newBlockId] === false) {
      console.log('setExpandedBlocks', newBlockId);
      setExpandedBlocks(prev => ({
        ...prev,
        [newBlockId]: true,
      }));
      setNewBlockId('');
    }
  }, [newBlockId, expandedBlocks]);

  useEffect(() => {
    console.log('expandedBlocks', expandedBlocks);
  }, [expandedBlocks]);

  const onChangeBlockType = async (id: string, llm_enabled: boolean) => {
    const p = blockProperties[id].properties as ContentDTO;
    await actions.updateBlockProperties(id, {
      ...blockProperties[id],
      properties: {
        ...p,
        llm_enabled: llm_enabled,
      },
    });

    actions.saveBlocks(currentShifu?.bid || '');
  };

  useEffect(() => {
    actions.loadModels();
    if (id) {
      actions.loadChapters(id);
    }
  }, [id]);

  const onChangeMdflow = (value: string) => {
    actions.setCurrentMdflow(value);
    actions.autoSaveBlocks();
  };

  return (
    <div className='flex flex-col h-screen bg-gray-50'>
      <Header />
      <div className='flex-1 flex overflow-hidden scroll-y'>
        <div className='p-4 bg-white'>
          <div className='flex items-center justify-between gap-3'>
            <div
              onClick={() => setFoldOutlineTree(!foldOutlineTree)}
              className='rounded border bg-white p-1 cursor-pointer text-sm hover:bg-gray-200'
            >
              <ListCollapse className='h-5 w-5' />
            </div>
            {!foldOutlineTree && (
              <Button
                variant='outline'
                className='h-8 bottom-0 left-4 flex-1'
                size='sm'
                onClick={onAddChapter}
              >
                <Plus />
                {t('module.shifu.newChapter')}
              </Button>
            )}
          </div>

          {!foldOutlineTree && (
            <div className='flex-1 h-full overflow-y-auto overflow-x-hidden w-[256px]'>
              <ol className=' text-sm'>
                <OutlineTree
                  items={chapters}
                  onChange={newChapters => {
                    actions.setChapters([...newChapters]);
                  }}
                />
              </ol>
            </div>
          )}
        </div>
        <div className='flex-1 overflow-auto relative text-sm'>
          <div className='p-8 gap-4 flex flex-col max-w-[900px] mx-auto h-full w-full'>
            {
              isLoading ? (
                <div className='h-40 flex items-center justify-center'>
                  <Loading />
                </div>
              ) : currentNode?.depth && currentNode.depth > 0 ? (
                <>
                  <div className='flex items-center'>
                    <h2 className='text-base font-semibold text-foreground'>
                      {t('shifu.creationArea.title')}
                    </h2>
                  </div>
                  <MarkdownFlowEditor
                    locale={profile?.language as 'en-US' | 'zh-CN'}
                    content={mdflow}
                    onChange={onChangeMdflow}
                  />
                </>
              ) : (
                <></>
              )
              // <>
              //   <DndProvider backend={HTML5Backend}>
              //     {blocks.map((block, index) => (
              //       <DraggableBlock
              //         key={block.bid}
              //         id={block.bid}
              //         block={block}
              //         type={block.type as BlockType}
              //         index={index}
              //         moveBlock={(dragIndex: number, hoverIndex: number) => {
              //           const dragBlock = blocks[dragIndex];
              //           const newBlocks = [...blocks];
              //           newBlocks.splice(dragIndex, 1);
              //           newBlocks.splice(hoverIndex, 0, dragBlock);
              //           actions.setBlocks(newBlocks);
              //           actions.autoSaveBlocks(
              //             currentNode!.bid,
              //             newBlocks,
              //             blockContentTypes,
              //             blockProperties,
              //             currentShifu?.bid || '',
              //           );
              //         }}
              //         onClickChangeType={onChangeBlockType}
              //         onClickDebug={onDebugBlock}
              //         onClickRemove={onRemove}
              //         disabled={expandedBlocks[block.bid]}
              //         error={blockErrors[block.bid]}
              //       >
              //         <div
              //           id={block.bid}
              //           className='relative flex flex-col gap-2 '
              //         >
              //           <RenderBlockUI
              //             block={block}
              //             onExpandChange={expanded => {
              //               setExpandedBlocks(prev => ({
              //                 ...prev,
              //                 [block.bid]: expanded,
              //               }));
              //             }}
              //             expanded={expandedBlocks[block.bid]}
              //           />
              //           <div>
              //             <AddBlock
              //               onAdd={(type: BlockType) => {
              //                 onAddBlock(index + 1, type, id);
              //               }}
              //             />
              //           </div>
              //         </div>
              //       </DraggableBlock>
              //     ))}
              //   </DndProvider>
              //   {(currentNode?.depth || 0) > 0 && blocks.length === 0 && (
              //     <div className='flex flex-row items-center justify-start h-6'>
              //       <AddBlock
              //         onAdd={(type: BlockType) => {
              //           onAddBlock(1, type, id);
              //         }}
              //       />
              //     </div>
              //   )}
              // </>
            }
          </div>
        </div>
      </div>
      {debugBlockInfo.visible && (
        <AIDebugDialog
          blockId={debugBlockInfo.blockId}
          open={true}
          onOpenChange={onDebugBlockClose}
        />
      )}

      <AlertDialog
        open={removeBlockInfo.visible}
        onOpenChange={(visible: boolean) => {
          setRemoveBlockInfo({
            ...removeBlockInfo,
            visible,
          });
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {t('module.renderBlock.confirmDelete')}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {t('module.renderBlock.confirmDeleteDescription')}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>
              {t('module.renderBlock.cancel')}
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={() => handleConfirmDelete(removeBlockInfo.blockId)}
            >
              {t('module.renderBlock.confirm')}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};

export default ScriptEditor;
