"use client"
import { SortableTree, SimpleTreeItemWrapper, TreeItemComponentProps, TreeItems } from '../dnd-kit-sortable-tree';
import React from 'react';
import { Outline } from '@/types/scenario';
import { cn } from '@/lib/utils';
import { Plus, Trash } from 'lucide-react';
import { InlineInput } from '../inline-input';
import { useScenario } from '@/store/useScenario';
interface ICataTreeProps {
    currentNode?: Outline;
    items: TreeItems<Outline>;
    onChange?: (data: TreeItems<Outline>) => void;
    onAddNodeClick?: (node: Outline) => void;
}

export const CataTree = React.memo((props: ICataTreeProps) => {
    const { items, onChange, } = props;
    const onItemsChanged = (data: TreeItems<Outline>) => {

        onChange?.(data);
    }

    const onAddNodeClick = (node: Outline) => {
        props.onAddNodeClick?.(node);
    }

    return (
        <SortableTree
            items={items}
            indentationWidth={20}
            onItemsChanged={onItemsChanged}
            TreeItemComponent={(props) => {
                return (
                    <MinimalTreeItemComponent
                        {...props}
                        onAddNodeClick={onAddNodeClick}
                    />
                )
            }}
            dropAnimation={null}
        />
    );
});

CataTree.displayName = 'CataTree';




export type TreeItemProps = {
    currentNode?: Outline;
    onChange?: (node: Outline, value: string) => void;
}
const MinimalTreeItemComponent = React.forwardRef<
    HTMLDivElement,
    TreeItemComponentProps<Outline> & TreeItemProps
>((props, ref) => {
    const { focusId, actions, cataData } = useScenario();
    const onNodeChange = (value: string) => {
        actions.updateOuline(props.item.id, {
            id: props.item.id,
            name: value,
            children: [],
            no: '',
            depth: props.item.depth,
        })

        actions.createChapter({
            parent_id: cataData[props.item.id!]?.parent_id,
            id: props.item.id,
            name: value,
            children: [],
            no: '',
            depth: props.item.depth,
        })
        actions.setFocusId("");
    }
    const onAddNodeClick = (node: Outline) => {
        actions.addSubOutline(node, "");
    }
    const removeNode = () => {
        console.log(props.item)
        actions.removeOutline(props.item);
    }
    return (
        <SimpleTreeItemWrapper {...props} ref={ref}>
            <div className={cn(
                'flex items-center flex-1 px-0 py-1 justify-between w-full',
                (props.item?.children?.length || 0) > 0 ? 'pl-0' : 'pl-4'
            )}>
                <span className='w-40 whitespace-nowrap overflow-hidden text-ellipsis' >
                    <InlineInput
                        isEdit={focusId === props.item.id}
                        value={cataData[props.item.id!]?.name || ""}
                        onChange={onNodeChange}
                        onFocus={() => {
                            actions.setFocusId(props.item.id || "")
                        }}
                    />
                </span>
                {
                    props.item.depth > 0 && (
                        <div className='flex items-center space-x-1'>
                            <Plus className='cursor-pointer h-5 w-5 text-gray-500' />
                            <Trash className='cursor-pointer h-4 w-4 text-gray-500' onClick={removeNode} />
                        </div>
                    )
                }
                {
                    props.item.depth <= 0 && (
                        <div onClick={(e) => {
                            e.stopPropagation();
                            onAddNodeClick?.(props.item);
                        }}>
                            <Plus className='cursor-pointer h-5 w-5 text-gray-500' />
                        </div>
                    )
                }

            </div>
        </SimpleTreeItemWrapper >
    )
});

MinimalTreeItemComponent.displayName = 'MinimalTreeItemComponent';


export default CataTree;