/* eslint-disable @typescript-eslint/no-unused-vars */
import React from 'react'
import {
    headingsPlugin,
    listsPlugin,
    quotePlugin,
    tablePlugin,
    toolbarPlugin,
    SandpackConfig,
    UndoRedo,
    BoldItalicUnderlineToggles,
    ListsToggle,
    BlockTypeSelect
} from '@mdxeditor/editor';
import '@mdxeditor/editor/style.css'
import MDXEditor from '@/components/md-editor/ForwardRefEditor';
import { cn } from '@/lib/utils';

const defaultSnippetContent = `
export default function App() {
  return (
    <div className="App">
      <h1>Hello CodeSandbox</h1>
      <h2>Start editing to see some magic happen!</h2>
    </div>
  );
}
`.trim()

export const virtuosoSampleSandpackConfig: SandpackConfig = {
    defaultPreset: 'react',
    presets: [
        {
            label: 'React',
            name: 'react',
            meta: 'live react',
            sandpackTemplate: 'react',
            sandpackTheme: 'light',
            snippetFileName: '/App.js',
            snippetLanguage: 'jsx',
            initialSnippetContent: defaultSnippetContent
        },
        {
            label: 'React',
            name: 'react',
            meta: 'live',
            sandpackTemplate: 'react',
            sandpackTheme: 'light',
            snippetFileName: '/App.js',
            snippetLanguage: 'jsx',
            initialSnippetContent: defaultSnippetContent
        },
        {
            label: 'Virtuoso',
            name: 'virtuoso',
            meta: 'live virtuoso',
            sandpackTemplate: 'react-ts',
            sandpackTheme: 'light',
            snippetFileName: '/App.tsx',
            initialSnippetContent: defaultSnippetContent,
            dependencies: {
                'react-virtuoso': 'latest',
                '@ngneat/falso': 'latest'
            },
        }
    ]
}

export async function expressImageUploadHandler(image: File) {
    const formData = new FormData()
    formData.append('image', image)
    const response = await fetch('/uploads/new', { method: 'POST', body: formData })
    const json = (await response.json()) as { url: string }
    return json.url
}


export const ALL_PLUGINS = [
    toolbarPlugin({
        toolbarClassName: "md-toolbar",
        toolbarContents: () => {
            return (
                <>
                    <UndoRedo />
                    <BoldItalicUnderlineToggles />
                    <ListsToggle options={['bullet', 'number']} />
                    <BlockTypeSelect />
                </>
            )
        }
    }),
    listsPlugin(),
    quotePlugin(),
    headingsPlugin({ allowedHeadingLevels: [1, 2, 3] }),
    tablePlugin(),

]

export const MDEditor = ({ className = '', value, onChange }: { className: string, value: string, onChange: (value: string) => void }) => {
    return (
        <MDXEditor

            className={cn("h-auto overflow-auto markdown bg-[#F5F5F4]", className)}
            markdown={value}
            onChange={(value) => {
                onChange?.(value)
            }}
            plugins={ALL_PLUGINS}
        />
    )
}

export default MDEditor
