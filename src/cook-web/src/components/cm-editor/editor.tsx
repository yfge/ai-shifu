'use client'

import { useState, useCallback, useRef, createContext } from 'react'
import CodeMirror from '@uiw/react-codemirror'
// import { markdown } from "@codemirror/lang-markdown"
import {
  autocompletion,
  type CompletionContext,
  type CompletionResult
} from '@codemirror/autocomplete'
import { EditorView } from '@codemirror/view'
import CustomDialog from './components/custom-dialog'
import EditorContext from './editor-context'
import VariableInject from './components/variable-inject'
import ImageInject from './components/image-inject'
import VideoInject from './components/video-inject'
import { SelectedOption, IEditorContext } from './type'

// 定义变量类型
interface EnumItem {
  value: string
  alias: string
}

interface Variable {
  id: string
  name: string
  alias: string
  type: 'system' | 'custom'
  dataType: 'string' | 'enum'
  defaultValue?: string
  enumItems?: EnumItem[]
}

// 简化的 slash 命令处理
function createSlashCommands (
  onSelectOption: (selectedOption: SelectedOption) => void
) {
  return (context: CompletionContext): CompletionResult | null => {
    const word = context.matchBefore(/\/(\w*)$/)
    if (!word) return null

    return {
      from: word.from,
      options: [
        {
          label: '变量',
          apply: () => {
            onSelectOption(SelectedOption.Variable)
            return ''
          }
        },
        {
          label: '图片',
          apply: () => {
            onSelectOption(SelectedOption.Image)
            return
          }
        },
        {
          label: '视频',
          apply: () => {
            onSelectOption(SelectedOption.Video)
            return
          }
        }
      ],
      filter: false
    }
  }
}

type EditorProps = {}

const Editor: React.FC<EditorProps> = () => {
  const [dialogOpen, setDialogOpen] = useState(false)
  const [selectedOption, setSelectedOption] = useState<SelectedOption>(
    SelectedOption.Empty
  )
  const editorViewRef = useRef<EditorView | null>(null)

  const editorContextValue: IEditorContext = {
    selectedOption: SelectedOption.Empty,
    setSelectedOption,
    dialogOpen,
    setDialogOpen
  }

  // 打开对话框的函数
  const onSelectedOption = useCallback((selectedOption: SelectedOption) => {
    setDialogOpen(true)
    setSelectedOption(selectedOption)
  }, [])

  // 插入文本逻辑
  const insertText = useCallback((text: string) => {
    if (!editorViewRef.current) return

    const { state, dispatch } = editorViewRef.current
    const changes = {
      from: state.selection.main.from,
      insert: text
    }

    dispatch({
      changes,
      selection: { anchor: changes.from + text.length }
    })
  }, [])

  const handleSelectVariable = useCallback(
    (variable: Variable) => {
      const textToInsert = `{{${variable.name}}}`
      insertText(textToInsert)
      setDialogOpen(false)
    },
    [insertText]
  )

  // 创建 slash 命令补全
  const slashCommandsExtension = useCallback(() => {
    return autocompletion({
      override: [createSlashCommands(onSelectedOption)]
    })
  }, [onSelectedOption])

  // 保存编辑器引用
  const handleEditorUpdate = useCallback((view: EditorView) => {
    editorViewRef.current = view
  }, [])

  return (
    <>
      <EditorContext.Provider value={editorContextValue}>
        <CodeMirror
          extensions={[
            //markdown(),
            slashCommandsExtension(),
            EditorView.updateListener.of(update => {
              handleEditorUpdate(update.view)
            })
          ]}
          className='border rounded-md'
          placeholder='输入 / 触发命令菜单...'
        />
        <CustomDialog>
          {selectedOption === SelectedOption.Variable && (
            <VariableInject onSelect={handleSelectVariable} />
          )}
          {selectedOption === SelectedOption.Image && <ImageInject />}
          {selectedOption === SelectedOption.Video && <VideoInject />}
        </CustomDialog>
      </EditorContext.Provider>
    </>
  )
}
export default Editor
