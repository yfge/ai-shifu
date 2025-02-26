"use client"
import React, { useState, useEffect, useRef } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { Scroll, Edit, Plus, ChevronDown, ChevronUp, ChevronLeft, ChevronRight } from 'lucide-react';

// 模拟初始剧本数据
const initialScriptSections = [
    { id: 1, title: "第一幕：引子", content: "# 第一幕：引子\n\n这是剧本的开始，主角登场..." },
    { id: 2, title: "第二幕：冲突", content: "# 第二幕：冲突\n\n主角面临第一个挑战..." },
    { id: 3, title: "第三幕：高潮", content: "# 第三幕：高潮\n\n故事迎来最激烈的冲突..." },
    { id: 4, title: "第四幕：结局", content: "# 第四幕：结局\n\n故事走向结局..." }
];

// 简化版Markdown编辑器组件
const MarkdownEditor = ({ content, onChange, sectionId }) => {
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
                onChange={(e) => onChange(sectionId, e.target.value)}
                className="w-full p-4 min-h-48 focus:outline-none font-mono text-sm"
                placeholder="在此输入Markdown内容..."
            />
        </div>
    );
};

// 侧边栏导航组件
const SidebarNav = ({ sections, activeSection, onSectionClick }) => {
    return (
        <Card className="fixed left-4 top-1/2  w-56 max-h-96 overflow-y-auto z-10 shadow-lg translate-y-[-50%] ">
            <CardContent className="p-4">
                <div className="flex items-center mb-4">
                    <Scroll size={18} className="mr-2" />
                    <h3 className="font-semibold">剧本章节</h3>
                </div>
                <Separator className="mb-4" />
                <ul className="space-y-2">
                    {sections.map((section) => (
                        <li key={section.id}>
                            <Button
                                variant={activeSection === section.id ? "secondary" : "ghost"}
                                className="w-full justify-start text-left font-normal"
                                onClick={() => onSectionClick(section.id)}
                            >
                                {section.title}
                            </Button>
                        </li>
                    ))}
                </ul>
            </CardContent>
        </Card>
    );
};

const ScriptEditor = ({ id }: { id: string }) => {
    const [sections, setSections] = useState(initialScriptSections);
    const [activeSection, setActiveSection] = useState<string>("1");
    const [isSidebarOpen, setIsSidebarOpen] = useState(true);
    const sectionRefs = useRef<{ [key: string]: HTMLDivElement }>({});

    // 处理内容更新
    const handleContentChange = (sectionId: string, newContent: string) => {
        setSections(sections.map(section =>
            section.id === sectionId ? { ...section, content: newContent } : section
        ));
    };

    // 添加新章节
    const handleAddSection = (afterId) => {
        const newId = Math.max(...sections.map(s => s.id)) + 1;
        const index = sections.findIndex(s => s.id === afterId);
        const newSection = {
            id: newId,
            title: `新章节 ${newId}`,
            content: `# 新章节 ${newId}\n\n请在此处输入内容...`
        };

        const newSections = [
            ...sections.slice(0, index + 1),
            newSection,
            ...sections.slice(index + 1)
        ];

        setSections(newSections);
        setActiveSection(newId);
    };

    // 滚动到章节
    const scrollToSection = (sectionId: string) => {
        if (sectionRefs.current[sectionId]) {
            sectionRefs.current[sectionId].scrollIntoView({ behavior: 'smooth' });
            setActiveSection(sectionId);
        }
    };

    // 保存引用以便后续滚动
    useEffect(() => {
        sectionRefs.current = {};
    }, []);

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
                        sections={sections}
                        activeSection={activeSection}
                        onSectionClick={scrollToSection}
                    />
                )}

                <div className="flex flex-col gap-8 px-4 ml-0 md:ml-64">
                    {sections.map((section, index) => (
                        <div key={section.id} onClick={() => {
                            console.log('===')
                            setActiveSection(section.id);
                        }} >
                            <div
                                ref={el => sectionRefs.current[section.id] = el}
                                id={`section-${section.id}`}
                                className={`p-6 bg-white rounded-lg shadow-sm ${activeSection === section.id ? 'ring-2 ring-blue-500' : ''}`}
                            >
                                <h2 className="text-xl font-semibold mb-4">{section.title}</h2>
                                <MarkdownEditor
                                    content={section.content}
                                    onChange={handleContentChange}
                                    sectionId={section.id}
                                />
                            </div>

                            <div className="flex justify-center my-4">
                                <Button
                                    variant="outline"
                                    size="sm"
                                    className="flex items-center gap-1"
                                    onClick={() => handleAddSection(section.id)}
                                >
                                    <Plus size={16} />
                                    在此处插入新章节
                                </Button>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
};

export default ScriptEditor;
