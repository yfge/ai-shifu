"use client"
import React, { useState, useEffect, useRef } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { Scroll, Edit, Plus, ChevronLeft, ChevronRight } from 'lucide-react';
import { useScenario } from '@/store';
import { Chapter } from '@/types/scenario';

interface SidebarNavProps {
    chapters: Chapter[];
    currentChapter: Chapter | null;
    onChapterClick: (chapter: Chapter) => void;
}

// 简化版Markdown编辑器组件
const MarkdownEditor = ({ content, onChange }: { content: string, onChange: (value: string) => void }) => {
    return (
        <div className="w-full border rounded-md">
            <div className="bg-gray-100 p-2 border-b flex justify-between items-center">
                <div className="flex items-center">
                    <Edit size={16} className="mr-2" />
                    <span className="text-sm font-medium">Markdown 编辑器</span>
                </div>
                <div className="flex space-x-2">
                    <Button variant="ghost" size="sm">预览</Button>
                </div>
            </div>
            <textarea
                value={content}
                onChange={(e) => onChange(e.target.value)}
                className="w-full p-4 min-h-48 focus:outline-none font-mono text-sm"
                placeholder="在此输入Markdown内容..."
            />
        </div>
    );
};

// 侧边栏导航组件
const SidebarNav = ({ chapters, currentChapter, onChapterClick }: SidebarNavProps) => {
    return (
        <Card className="fixed left-4 top-1/2  w-56 max-h-96 overflow-y-auto z-10 shadow-lg translate-y-[-50%] ">
            <CardContent className="p-4">
                <div className="flex items-center mb-4">
                    <Scroll size={18} className="mr-2" />
                    <h3 className="font-semibold">剧本章节</h3>
                </div>
                <Separator className="mb-4" />
                <ul className="space-y-2">
                    {chapters.map((chapter) => (
                        <li key={chapter.chapter_index}>
                            <Button
                                variant={currentChapter?.chapter_index === chapter.chapter_index ? "secondary" : "ghost"}
                                className="w-full justify-start text-left font-normal"
                                onClick={() => onChapterClick(chapter)}
                            >
                                {chapter.chapter_name}
                            </Button>
                        </li>
                    ))}
                </ul>
            </CardContent>
        </Card>
    );
};

const ScriptEditor = ({ id }: { id: string }) => {
    const { chapters, currentChapter, actions } = useScenario();
    const [isSidebarOpen, setIsSidebarOpen] = useState(true);
    const chapterRefs = useRef<{ [key: number]: HTMLDivElement }>({});

    // 处理内容更新
    const handleContentChange = (newContent: string) => {
        if (currentChapter) {
            actions.saveChapter({
                ...currentChapter,
                chapter_description: newContent
            });
        }
    };

    // 添加新章节
    const handleAddChapter = async (afterChapter: Chapter) => {
        const newChapterIndex = afterChapter.chapter_index + 1;
        await actions.createChapter({
            chapter_name: `新章节 ${newChapterIndex}`,
            chapter_description: `# 新章节 ${newChapterIndex}\n\n请在此处输入内容...`,
            scenario_id: id
        });
    };

    // 滚动到章节
    const scrollToChapter = (chapter: Chapter) => {
        if (chapterRefs.current[chapter.chapter_index]) {
            chapterRefs.current[chapter.chapter_index].scrollIntoView({ behavior: 'smooth' });
            actions.setCurrentChapter(chapter);
        }
    };

    useEffect(() => {
        debugger;
        actions.loadChapters(id);
    }, [id]);

    return (
        <div className="min-h-screen bg-gray-50 py-8">
            <div className="container mx-auto">
                <header className="mb-8 px-4 flex justify-between items-center">
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setIsSidebarOpen(!isSidebarOpen)}
                    >
                        {isSidebarOpen ? <ChevronLeft size={16} /> : <ChevronRight size={16} />}
                        {isSidebarOpen ? "隐藏章节" : "显示章节"}
                    </Button>
                </header>

                {isSidebarOpen && (
                    <SidebarNav
                        chapters={chapters}
                        currentChapter={currentChapter}
                        onChapterClick={scrollToChapter}
                    />
                )}

                <div className="flex flex-col gap-8 px-4 ml-0 md:ml-64">
                    {chapters.map((chapter) => (
                        <div key={chapter.chapter_index} onClick={() => actions.setCurrentChapter(chapter)}>
                            <div
                                ref={el => {
                                    if (el) {
                                        chapterRefs.current[chapter.chapter_index] = el;
                                    }
                                }}
                                id={`chapter-${chapter.chapter_index}`}
                                className={`p-6 bg-white rounded-lg shadow-sm ${currentChapter?.chapter_index === chapter.chapter_index ? 'ring-2 ring-blue-500' : ''}`}
                            >
                                <h2 className="text-xl font-semibold mb-4">{chapter.chapter_name}</h2>
                                <MarkdownEditor
                                    content={chapter.chapter_description}
                                    onChange={handleContentChange}
                                />
                            </div>

                            <div className="flex justify-center my-4">
                                <Button
                                    variant="outline"
                                    size="sm"
                                    className="flex items-center gap-1"
                                    onClick={() => handleAddChapter(chapter)}
                                >
                                    <Plus size={16} />
                                    在此处插入新章节
                                </Button>
                            </div>
                        </div>
                    ))}
                    <div className="flex justify-center my-4">
                        <Button
                            variant="outline"
                            size="sm"
                            className="flex items-center gap-1"
                            onClick={() => handleAddChapter({
                                chapter_description: '章节内容a',
                                chapter_index: 0,
                                chapter_name: '新章节a',
                                scenario_id: ''
                            })}
                        >
                            <Plus size={16} />
                            在此处插入新章节
                        </Button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ScriptEditor;
